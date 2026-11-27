"""Capacity alarms must not mask installation success or real integration failures."""
import importlib.util
from pathlib import Path
import subprocess
import pytest
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('health_installer',ROOT/'install_driver.py')
driver=importlib.util.module_from_spec(spec);spec.loader.exec_module(driver)

@pytest.mark.parametrize('health',[0,2])
def test_capacity_alarm_keeps_success(monkeypatch,health,capsys):
    calls=[]
    def run(args,**kw):
        calls.append(args)
        if health and args==['zfsm','check','--lang','de']:raise subprocess.CalledProcessError(health,args)
        return subprocess.CompletedProcess(args,0)
    monkeypatch.setattr(driver.subprocess,'run',run)
    driver.post_install_checks('de')
    assert calls[1]==['zfsm','check','--integration-only','--lang','de']
    assert calls[-1]==['zfsm','services','--lang','de']
    assert ('critical pool alert' in capsys.readouterr().out)==(health==2)

def test_integration_failure_stops_before_health(monkeypatch):
    calls=[]
    def run(args,**kw):
        calls.append(args)
        if '--integration-only' in args:raise subprocess.CalledProcessError(2,args)
        return subprocess.CompletedProcess(args,0)
    monkeypatch.setattr(driver.subprocess,'run',run)
    with pytest.raises(subprocess.CalledProcessError):driver.post_install_checks('en')
    assert len(calls)==2

def test_health_error_not_ignored(monkeypatch):
    def run(args,**kw):
        if args==['zfsm','check','--lang','de']:raise subprocess.CalledProcessError(1,args)
        return subprocess.CompletedProcess(args,0)
    monkeypatch.setattr(driver.subprocess,'run',run)
    with pytest.raises(subprocess.CalledProcessError):driver.post_install_checks('de')

@pytest.mark.parametrize('integration_only',[False,True])
def test_cli_capacity_and_integration_are_separate(monkeypatch,integration_only):
    import zfsm_cli,zfsm_emergency
    monkeypatch.setattr(zfsm_cli,'run',lambda args:0)
    monkeypatch.setattr(zfsm_emergency,'pools',lambda:[{'name':'fixture','percent':91,'severity':'critical'}])
    args=['check','--lang','de']+(['--integration-only'] if integration_only else [])
    assert zfsm_cli.main(args)==(0 if integration_only else 2)
