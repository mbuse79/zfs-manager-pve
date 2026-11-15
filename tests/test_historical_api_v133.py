from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]


def historical_api_without_v133_topology():
    """Strictly preserve the 1.0.0-32 API excluding the new read-only route."""
    s=(ROOT/'src/PVE/API2/ZFSSnapshotViewer.pm').read_bytes()
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
