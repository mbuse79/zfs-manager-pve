import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def test_guest_controls_safety_and_taint():
    env = {**os.environ, "ZFSM_TEST_DATASET": "tank/data/vm-101-disk-0"}
    cp = subprocess.run(
        ["perl", "-T", "-I" + str(ROOT / "src"), str(ROOT / "tests/perl_mock_guest_controls.pl")],
        text=True, capture_output=True, env=env, timeout=30,
    )
    assert cp.returncode == 0, cp.stdout + cp.stderr
    assert "PASS:" in cp.stdout
