"""Exercise the real Perl worker spawn under Proxmox's taint mode."""
import json
import os
from pathlib import Path
import subprocess

ROOT=Path(__file__).resolve().parents[1]


def test_cluster_worker_and_polling_with_tainted_api_values():
    env={**os.environ,'ZFSM_TEST_USER':'root@pam','ZFSM_TEST_NODE':'fixture',
         'ZFSM_TEST_LANG':'de','ZFSM_TEST_NODES':'node-a,node-b',
         'ZFSM_TEST_PLAN':'a'*32,'ZFSM_TEST_SECRET':'b'*64,
         'PATH':'/tmp/untrusted:/usr/bin:/bin'}
    p=subprocess.run(['/usr/bin/perl','-T','-I',str(ROOT/'src'),str(ROOT/'tests/perl_taint_cluster.pl')],
                     env=env,capture_output=True,text=True)
    assert p.returncode==0,p.stdout+p.stderr
    rows=[json.loads(s) for s in p.stdout.splitlines() if s.startswith('{')]
    assert len(rows)==2
    assert rows[0]['args'][:3]==['--lang','de','preview']
    assert rows[0]['args'][-2:]==['--nodes','node-a,node-b']
    assert rows[1]['args'][:3]==['--lang','de','install']
    assert rows[1]['args'][-3:]==['--plan','a'*32,'--confirmed']
    assert 'PASS: real system/open calls under perl -T' in p.stdout
