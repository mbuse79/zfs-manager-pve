"""The public quick entry must verify its bootstrap before running it."""
import io
from pathlib import Path
import subprocess

import pytest

ROOT=Path(__file__).resolve().parents[1]


@pytest.mark.parametrize('case',['valid','tampered','http-redirect'])
def test_pinned_quick_entry(case,monkeypatch):
    code=(ROOT/'quick-install.sh').read_text().split("<<'PYQUICK'\n",1)[1].rsplit('\nPYQUICK',1)[0]
    ns={'__name__':'test'};exec(compile(code,'quick-install.sh','exec'),ns)
    class Response(io.BytesIO):
        url='https://fixture.example.invalid/bootstrap' if case!='http-redirect' else 'http://fixture.example.invalid/bootstrap'
    payload=(ROOT/'bootstrap-1.1.sh').read_bytes() if case!='tampered' else b'tampered'
    monkeypatch.setattr(ns['os'],'geteuid',lambda:0)
    monkeypatch.setattr(ns['urllib'].request,'urlopen',lambda *a,**k:Response(payload))
    calls=[]
    def run(args,**kwargs):
        calls.append(args)
        return subprocess.CompletedProcess(args,0,'pve-manager/9.2.26/fixture','')
    monkeypatch.setattr(ns['subprocess'],'run',run)
    if case=='valid':
        assert ns['main'](['--check-only','--lang','en'])==0
        assert calls[-1][0]=='bash'
        assert calls[-1][2:4]==[ns['ZIP_URL'],ns['ZIP_SHA']]
        assert calls[-1][-3:]==['--lang','en','--check-only']
    else:
        with pytest.raises(ValueError):ns['main'](['--check-only'])
        assert len(calls)==1  # Only the read-only pveversion fixture ran.
