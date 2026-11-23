import json
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def test_real_update_worker_execution_under_perl_taint_and_rbac():
    env = {**os.environ, 'ZFSM_TEST_USER': 'root@pam', 'ZFSM_TEST_NODE': 'fixture',
           'ZFSM_TEST_NODES': 'node-a', 'ZFSM_TEST_PLAN': 'a'*32, 'ZFSM_TEST_SECRET': 'b'*64,
           'PATH': '/tmp/untrusted:/usr/bin:/bin'}
    cp = subprocess.run(['/usr/bin/perl', '-T', '-I'+str(ROOT/'src'), str(ROOT/'tests/perl_taint_updates.pl')],
                        env=env, capture_output=True, text=True, timeout=30)
    assert cp.returncode == 0, cp.stdout+cp.stderr
    rows = [json.loads(line) for line in cp.stdout.splitlines() if line.startswith('{')]
    assert [row['args'][0] for row in rows] == ['check', 'prepare', 'install']
    assert rows[-1]['args'][-4:] == ['--plan', 'a'*32, '--confirmed', '--json']
    assert 'PASS:' in cp.stdout
