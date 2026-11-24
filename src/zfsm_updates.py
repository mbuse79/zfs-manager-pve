#!/usr/bin/env python3
"""Stable-release checks and explicitly confirmed local updates; never auto-install."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys
import tempfile
import time
import urllib.parse
import urllib.request

from zfsm_cluster import Store
import zfsm_cluster_remote as bundle

REPO = 'mbuse79/zfs-manager-pve'
API = 'https://api.github.com/repos/' + REPO + '/releases/latest'
STATE = Path('/var/lib/pve-zfs-manager/updates')
CACHE = '0' * 32
HOSTS = {'api.github.com', 'github.com', 'release-assets.githubusercontent.com', 'objects.githubusercontent.com'}


class UpdateError(RuntimeError):
    pass


def safe_url(url):
    p = urllib.parse.urlsplit(url)
    if p.scheme != 'https' or p.hostname not in HOSTS or p.username or p.password or p.port not in (None, 443):
        raise UpdateError('Untrusted update URL / Nicht vertrauenswuerdige Updateadresse')
    return url


class Redirects(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return super().redirect_request(req, fp, code, msg, headers, safe_url(newurl))


def download(url, limit):
    req = urllib.request.Request(safe_url(url), headers={
        'User-Agent': 'BuMaVory-ZFSM-Updater', 'Accept': 'application/vnd.github+json'})
    with urllib.request.build_opener(Redirects()).open(req, timeout=45) as response:
        safe_url(response.url)
        chunks, total = [], 0
        while True:
            chunk = response.read(min(1024 * 1024, limit + 1 - total))
            if not chunk:
                return b''.join(chunks)
            chunks.append(chunk)
            total += len(chunk)
            if total > limit:
                raise UpdateError('Update download too large / Updatedownload zu gross')


def run(args, timeout=30):
    cp = subprocess.run(args, capture_output=True, text=True, timeout=timeout,
                        env={**os.environ, 'LC_ALL': 'C.UTF-8'})
    if len(cp.stdout) + len(cp.stderr) > 2_000_000:
        raise UpdateError('Excessive installer output / Installerausgabe zu gross')
    if cp.returncode:
        raise UpdateError((cp.stdout + cp.stderr)[-16000:] or 'Command failed: ' + args[0])
    return cp.stdout.strip()


def installed():
    value = run(['dpkg-query', '-W', '-f=${Status}\t${Version}', 'pve-zfs-manager'])
    if not value.startswith('install ok installed\t'):
        raise UpdateError('ZFSM package not configured / ZFSM-Paket nicht fertig konfiguriert')
    version = value.split('\t', 1)[1]
    if not re.fullmatch(r'[0-9][A-Za-z0-9.+:~\-]{0,100}', version):
        raise UpdateError('Invalid installed version')
    return version


def newer(candidate, current):
    if any(not isinstance(v, str) or not re.fullmatch(r'[0-9][A-Za-z0-9.+:~\-]{0,100}', v) for v in (candidate, current)):
        raise UpdateError('Invalid Debian version')
    cp = subprocess.run(['dpkg', '--compare-versions', candidate, 'gt', current],
                        capture_output=True, text=True, timeout=10)
    if cp.returncode not in (0, 1):
        raise UpdateError('Debian version comparison failed')
    return cp.returncode == 0


def release_info(raw):
    data = json.loads(raw)
    if not isinstance(data, dict) or data.get('draft') is not False or data.get('prerelease') is not False:
        raise UpdateError('Only published stable releases are supported / Nur stabile veroeffentlichte Releases')
    tag = data.get('tag_name', '')
    if not isinstance(tag, str) or len(tag)>80 or not re.fullmatch(r'v?[0-9]+(?:\.[0-9]+){1,3}(?:\+[A-Za-z0-9.]+)?', tag):
        raise UpdateError('Invalid stable release tag')
    version = tag.removeprefix('v')
    zipname = 'BuMaVory-ZFS-Manager-' + version + '.zip'
    assets = data.get('assets')
    if not isinstance(assets, list):
        raise UpdateError('Missing release assets')
    selected = {}
    for name, limit in [(zipname, bundle.MAX_ZIP), ('SHA256SUMS', 128000)]:
        matches = [a for a in assets if isinstance(a, dict) and a.get('name') == name]
        if len(matches) != 1:
            raise UpdateError('Missing/ambiguous release asset: ' + name)
        asset = matches[0]
        expected = 'https://github.com/' + REPO + '/releases/download/' + urllib.parse.quote(tag, safe='') + '/' + urllib.parse.quote(name, safe='')
        if asset.get('browser_download_url') != expected or not isinstance(asset.get('size'), int) or not 0 < asset['size'] <= limit:
            raise UpdateError('Invalid release asset URL/size')
        digest = asset.get('digest')
        if digest is not None and not re.fullmatch(r'sha256:[a-f0-9]{64}', str(digest)):
            raise UpdateError('Invalid GitHub asset digest')
        selected[name] = {'url': expected, 'size': asset['size'], 'digest': digest}
    return {'version': version, 'tag': tag, 'zip_name': zipname, 'assets': selected,
            'release_url': 'https://github.com/' + REPO + '/releases/tag/' + urllib.parse.quote(tag, safe='')}


def checksum_manifest(raw, name):
    entries = {}
    for line in raw.decode('ascii').splitlines():
        match = re.fullmatch(r'([a-f0-9]{64})  ([A-Za-z0-9_.+~\-]{1,200})', line)
        if not match or match[2] in entries or match[2] in ('.', '..'):
            raise UpdateError('Invalid/duplicate release checksum')
        entries[match[2]] = match[1]
    if name not in entries:
        raise UpdateError('ZIP checksum missing')
    return entries[name]


def checked_asset(info, name, fetch):
    asset = info['assets'][name]
    raw = fetch(asset['url'], bundle.MAX_ZIP if name == info['zip_name'] else 128000)
    if len(raw) != asset['size']:
        raise UpdateError('Release asset size changed')
    digest = hashlib.sha256(raw).hexdigest()
    if asset['digest'] and asset['digest'] != 'sha256:' + digest:
        raise UpdateError('GitHub asset digest mismatch')
    return raw


def job_id(value):
    if not isinstance(value, str) or not re.fullmatch('[a-f0-9]{32}', value) or value == CACHE:
        raise UpdateError('Invalid update job ID')
    return value


class Updater:
    def __init__(self, store=None, fetch=download, current=installed):
        self.store = store if store is not None else Store(STATE)
        self.fetch, self.current = fetch, current

    def status(self):
        try:
            cached = self.store.read(CACHE)
        except FileNotFoundError:
            cached = {'checked_at': None, 'latest_version': None, 'error': None}
        current = self.current()
        latest = cached.get('latest_version')
        return {**cached, 'installed_version': current,
                'available': bool(not cached.get('error') and latest and newer(latest, current)),
                'channel': 'stable', 'automatic_installation': False}

    def check(self):
        with self.store.lock():
            try:
                info = release_info(self.fetch(API, 2_000_000))
                result = {'checked_at': int(time.time()), 'latest_version': info['version'],
                          'release_url': info['release_url'], 'error': None}
            except Exception as exc:
                result = {'checked_at': int(time.time()), 'latest_version': None, 'error': str(exc)[-2000:]}
            self.store.write(CACHE, result)
        return self.status()

    def job(self, ident):
        value = self.store.read(job_id(ident))
        # Return public progress only; ZIP digests and plan evidence stay root-owned.
        return {k: value[k] for k in ('job', 'kind', 'status', 'phase', 'version', 'installed_version',
                                      'expires_at', 'error', 'log', 'ready') if k in value}

    def host_state(self):
        current = self.current()
        pve = run(['pveversion'])
        if not re.match(r'^pve-manager/9\.\d+\.\d+/', pve):
            raise UpdateError('PVE 9 required')
        if run(['dpkg', '--audit']):
            raise UpdateError('Pending package configuration; inspect host first / Unfertige Paketkonfiguration')
        return {'installed_version': current, 'pve': pve}

    def verify_package(self, raw, digest, target, version):
        bundle.unpack(raw, digest, target)
        deb = target / ('pve-zfs-manager_' + version + '_all.deb')
        for field, value in [('Package', 'pve-zfs-manager'), ('Version', version), ('Architecture', 'all')]:
            if run(['dpkg-deb', '-f', str(deb), field]) != value:
                raise UpdateError('Wrong update package metadata: ' + field)

    def prepare(self, ident):
        ident = job_id(ident)
        with self.store.lock():
            state = self.host_state()
            info = release_info(self.fetch(API, 2_000_000))
            if not newer(info['version'], state['installed_version']):
                raise UpdateError('No newer stable version / Keine neuere stabile Version')
            report = {'job': ident, 'kind': 'prepare', 'status': 'running', 'phase': 'download',
                      'version': info['version'], **state}
            self.store.write(ident, report)
            sums = checked_asset(info, 'SHA256SUMS', self.fetch)
            digest = checksum_manifest(sums, info['zip_name'])
            raw = checked_asset(info, info['zip_name'], self.fetch)
            if hashlib.sha256(raw).hexdigest() != digest:
                raise UpdateError('Release ZIP checksum mismatch')
            report['phase'] = 'precheck'
            self.store.write(ident, report)
            with tempfile.TemporaryDirectory(prefix='zfsm-update-precheck-') as td:
                target = Path(td)
                self.verify_package(raw, digest, target, info['version'])
                log = run(['bash', str(target/'install-local.sh'), '--check-only', '--lang', 'en'], timeout=600)
            if self.host_state() != state:
                raise UpdateError('Host changed during update precheck; repeat preview')
            # Publish a newly created private archive only after complete verification.
            archive = self.store.root / ('bundle-' + ident + '.zip')
            fd = os.open(archive, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
            with os.fdopen(fd, 'wb') as f:
                f.write(raw)
                f.flush()
                os.fsync(f.fileno())
            report.update(status='prepared', phase='ready', ready=True, expires_at=int(time.time())+300,
                          digest=digest, log=log[-16000:])
            self.store.write(ident, report)
            return self.job(ident)

    def read_archive(self, plan):
        archive = self.store.root / ('bundle-' + job_id(plan) + '.zip')
        fd = os.open(archive, os.O_RDONLY | os.O_NOFOLLOW)
        with os.fdopen(fd, 'rb') as f:
            meta = os.fstat(f.fileno())
            if not stat.S_ISREG(meta.st_mode) or meta.st_uid != 0 or stat.S_IMODE(meta.st_mode) != 0o600 or meta.st_size > bundle.MAX_ZIP:
                raise UpdateError('Unsafe staged update archive')
            return f.read(bundle.MAX_ZIP+1)

    def install(self, ident, plan, confirmed):
        ident, plan = job_id(ident), job_id(plan)
        if not confirmed or ident == plan:
            raise UpdateError('Explicit confirmation required')
        with self.store.lock():
            preview = self.store.read(plan)
            if preview.get('status') != 'prepared' or not preview.get('ready') or preview.get('expires_at', 0) <= time.time():
                raise UpdateError('Update preview expired or already used / Vorschau abgelaufen oder verwendet')
            if self.host_state() != {k: preview[k] for k in ('installed_version', 'pve')}:
                raise UpdateError('Host changed; repeat update preview')
            if not newer(preview['version'], self.current()):
                raise UpdateError('Downgrade or reinstall refused')
            archive = self.store.root / ('bundle-' + plan + '.zip')
            raw = self.read_archive(plan)
            report = {'job': ident, 'kind': 'install', 'status': 'running', 'phase': 'install',
                      'version': preview['version'], 'installed_version': preview['installed_version']}
            self.store.write(ident, report)
            with tempfile.TemporaryDirectory(prefix='zfsm-update-apply-') as td:
                target = Path(td)
                self.verify_package(raw, preview['digest'], target, preview['version'])
                # Single-use before the first possible package write. The verified
                # installer independently repeats structural and exact APT guards.
                preview.update(status='used', ready=False)
                self.store.write(plan, preview)
                log = run(['bash', str(target/'install-local.sh'), '--lang', 'en'], timeout=900)
            if self.current() != preview['version']:
                raise UpdateError('Installed version uncertain; inspect task log before retry')
            report.update(status='installed', phase='complete', log=log[-16000:])
            self.store.write(ident, report)
            try:
                archive.unlink()
            except OSError:
                pass  # Completed installation must not become a failure due to cache cleanup.
            return self.job(ident)

    def execute(self, operation, ident, plan=None, confirmed=False):
        ident = job_id(ident)
        if operation not in ('check', 'prepare', 'install'):
            raise UpdateError('Invalid update operation')
        self.store.write(ident, {'job': ident, 'kind': operation, 'status': 'running',
                                 'phase': 'check' if operation=='check' else 'download' if operation=='prepare' else 'precheck'})
        try:
            if operation == 'check':
                result = self.check()
                report = {'job': ident, 'kind': 'check', 'status': 'failed' if result.get('error') else 'complete',
                          'error': result.get('error')}
                self.store.write(ident, report)
                return report
            if operation == 'prepare':
                return self.prepare(ident)
            if operation == 'install':
                return self.install(ident, plan, confirmed)
            raise UpdateError('Invalid update operation')
        except Exception as exc:
            report = {'job': ident, 'kind': operation, 'status': 'failed', 'error': str(exc)[-16000:]}
            self.store.write(ident, report)
            raise


def main(argv=None, lang='en'):
    parser = argparse.ArgumentParser(description='Stable ZFSM updates / Stabile ZFSM-Updates')
    parser.add_argument('command', nargs='?', default='status', choices=['status', 'check', 'prepare', 'install', 'job'])
    parser.add_argument('--job')
    parser.add_argument('--plan')
    parser.add_argument('--confirmed', action='store_true')
    parser.add_argument('--json', action='store_true')
    parser.add_argument('--lang', choices=['de', 'en'], default=lang)
    args = parser.parse_args(argv)
    if os.geteuid() != 0:
        parser.error('root required / Root-Rechte erforderlich')
    updater = Updater()
    try:
        if args.command == 'status':
            result = updater.status()
        elif args.command == 'job':
            result = updater.job(args.job)
        elif args.job:
            result = updater.execute(args.command, args.job, args.plan, args.confirmed)
        elif args.command == 'check':
            result = updater.check()
        else:
            raise UpdateError('Use --job ID; installation also needs --plan ID --confirmed')
        if args.json:
            print(json.dumps(result, ensure_ascii=False))
        elif args.command in ('status', 'check'):
            de=args.lang=='de'
            print(('Installierte Version: ' if de else 'Installed version: ')+str(result['installed_version']))
            print(('Neueste stabile Version: ' if de else 'Latest stable version: ')+str(result.get('latest_version') or ('Unbekannt' if de else 'Unknown')))
            checked=result.get('checked_at')
            print(('Letzte Pruefung: ' if de else 'Last check: ')+(time.strftime('%Y-%m-%d %H:%M:%S %Z',time.localtime(checked)) if checked else ('Noch nicht geprueft' if de else 'Never checked')))
            print(('Update verfuegbar' if de else 'Update available') if result['available'] else ('Kein neueres stabiles Update' if de else 'No newer stable update'))
            if result.get('error'):print(('Prueffehler: ' if de else 'Check failed: ')+result['error'])
        else:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        return 1 if args.command == 'check' and result.get('error') else 0
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
