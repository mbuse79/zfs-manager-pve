from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]


def historical_api_without_v133_topology():
    """Strictly preserve the 1.0.0-32 API excluding the new read-only route."""
    s=(ROOT/'src/PVE/API2/ZFSSnapshotViewer.pm').read_bytes()
    for label in (b'LOCAL STABLE UPDATES', b'DATASET AUTOSNAP STATUS'):
        first=s.index(b'# BEGIN ZFSM '+label+b'\n')
        end_marker=b'# END ZFSM '+label+b'\n\n'
        last=s.index(end_marker,first)+len(end_marker)
        s=s[:first]+s[last:]
    # Guest snapshot controls are additive. Continue comparing every original
    # handler byte-for-byte, including the underlying guest-access resolver.
    start_guest=s.index(b'# BEGIN ZFSM GUEST SNAPSHOT CONTROLS\n')
    end_guest=s.index(b'# END ZFSM GUEST SNAPSHOT CONTROLS\n',start_guest)+len(b'# END ZFSM GUEST SNAPSHOT CONTROLS\n\n')
    s=s[:start_guest]+s[end_guest:]
    s=s.replace(b'return _guest_autosnap_rows();},',b'return _guest_access_rows();},',1)
    # The separate cluster deployment routes must leave all snapshot handlers
    # byte-identical. Their root-only authorization is tested independently.
    start_cluster=s.index(b'# BEGIN ZFSM OPTIONAL CLUSTER DEPLOYMENT\n')
    end_cluster=s.index(b'# END ZFSM OPTIONAL CLUSTER DEPLOYMENT\n',start_cluster)+len(b'# END ZFSM OPTIONAL CLUSTER DEPLOYMENT\n')
    s=s[:start_cluster]+s[end_cluster:]
    # v34 RC6 adds a read-only external-service inventory; strip it for historical comparison.
    start6=s.index(b'# Read-only inventory: detects but NEVER manages external replication jobs.')
    end6=s.index(b'# Retention configuration is read from the existing distro cron entries.',start6)
    s=s[:start6]+s[end6:]
    # v34 intentionally adds three guarded emergency API routes. Verify that
    # all prior backend logic remains unchanged after stripping both additions.
    start34=s.index(b'# v1.0.0-34: pool capacity alerts and signed emergency preview.')
    end34=s.index(b'# v1.0.0-33: Dynamic, strictly read-only pool to physical member mapping.',start34)
    s=s[:start34]+s[end34:]
    start=s.index(b'# v1.0.0-33: Dynamic, strictly read-only pool to physical member mapping.')
    end=s.index(b'# Read pool health, last scrub and read/write/checksum errors via zpool status.', start)
    return s[:start]+s[end:]


def test_exact_unchanged_v132_backend_outside_new_readonly_route():
    assert historical_api_without_v133_topology() == (ROOT/'tests/fixtures/ZFSSnapshotViewer_v129.pm').read_bytes()
    api=(ROOT/'src/PVE/API2/ZFSSnapshotViewer.pm').read_text()
    assert "path=>'pool-topology'" in api
    assert "_run_capture('/usr/bin/python3','/usr/lib/pve-zfs-manager/pool_discovery.py','--json')" in api
    assert "method=>'GET'" in api
