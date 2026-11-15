#!/usr/bin/env python3
"""Send ZFS Manager alerts via Proxmox VE's existing notification matchers.

Never creates/changes notification targets or reads secrets. Admin configures
and validates delivery in Datacenter -> Notifications.
"""
from __future__ import annotations
import json
from pathlib import Path
import re
import subprocess

CONFIG = Path('/etc/pve/notifications.cfg')
TARGET = re.compile(r'^\s*(sendmail|smtp|gotify|webhook):\s+[^\s]+\s*$', re.I)
ALLOWED_LEVELS = ('info','notice','warning','error')
PERL = r'''
use strict;
use warnings;
use JSON::PP qw(decode_json);
use PVE::Notify;
local $/;
my $raw = <STDIN>;
my $event = decode_json($raw);
my $level = $event->{level};
die "invalid severity" unless $level =~ /\A(?:info|notice|warning|error)\z/;
my $common = PVE::Notify::common_template_data();
my $data = {%$common, title => $event->{title}, message => $event->{message}};
my $fields = { type => 'zfs-manager-capacity', origin => 'zfs-manager' };
PVE::Notify::notify($level, 'simple', $data, $fields);
'''

class NotifyError(RuntimeError):
    pass


def inspect_targets(path=CONFIG):
    """Read public target declarations only, never private Proxmox secrets."""
    try:
        raw=path.read_text(encoding='utf-8')
    except (FileNotFoundError,PermissionError,OSError):
        return {'backend':'proxmox','targets':0,'configured':False,
                'note':'Keine Proxmox-Benachrichtigungsziele: Datacenter -> Notifications einrichten'}
    if len(raw)>2_000_000:
        raise NotifyError('Notifications-Konfiguration zu gross')
    n=sum(bool(TARGET.match(line)) for line in raw.splitlines())
    return {'backend':'proxmox','targets':n,'configured':n>0,
            'note':('Proxmox-Ziele vorhanden; Zustellung mit notify-test pruefen' if n else
                    'Keine Proxmox-Benachrichtigungsziele: Datacenter -> Notifications einrichten')}


def send(level,title,message,*,runner=subprocess.run):
    """Exit 0 means accepted by Proxmox; no guarantee of recipient delivery."""
    if level not in ALLOWED_LEVELS or not isinstance(title,str) or not isinstance(message,str):
        raise NotifyError('Ungueltige Benachrichtigung')
    if not (1 <= len(title) <= 150 and 1 <= len(message) <= 1500):
        raise NotifyError('Benachrichtigung zu lang oder leer')
    payload=json.dumps({'level':level,'title':title,'message':message},ensure_ascii=False)
    try:
        result=runner(['/usr/bin/perl','-MJSON::PP','-MPVE::Notify','-e',PERL],
                      input=payload,text=True,capture_output=True,timeout=25,check=False)
    except (OSError,subprocess.TimeoutExpired) as exc:
        raise NotifyError('Proxmox-Benachrichtigung konnte nicht gestartet werden') from exc
    if result.returncode:
        # Never expose Perl's full stderr, which could contain sensitive data.
        raise NotifyError('Proxmox-Benachrichtigungsversand fehlgeschlagen (Exit '+str(result.returncode)+')')
    return True
