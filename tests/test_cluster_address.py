"""A standalone PVE::Cluster helper must refresh its initially empty cache."""
import os
from pathlib import Path

import pytest
import zfsm_cluster as cluster


@pytest.mark.parametrize('node,expected', [('node-a','10.23.0.11'),('node-b','fd23::12'),('missing',None)])
def test_real_perl_helper_refreshes_cluster_cache_and_refuses_dns_fallback(tmp_path,monkeypatch,node,expected):
    pve=tmp_path/'PVE'; pve.mkdir()
    (pve/'Cluster.pm').write_text('''package PVE::Cluster;
our $members = {};
sub cfs_update { die "strict refresh required" unless $_[0] == 1;
 $members = {'node-a'=>{ip=>'10.23.0.11'},'node-b'=>{ip=>'fd23::12'}}; }
sub get_members { return $members; }
1;
''')
    (pve/'SSHInfo.pm').write_text('''package PVE::SSHInfo;
use PVE::Cluster;
sub get_ssh_info { my ($node)=@_; my $m=PVE::Cluster::get_members();
 return {name=>$node,ip=>$m->{$node}{ip}//'192.0.2.99'}; }
sub ssh_info_to_command { my ($i,@opts)=@_; return ['/usr/bin/ssh',
 '-o','BatchMode=yes','-o','HostKeyAlias='.$i->{name},
 '-o','UserKnownHostsFile=/etc/pve/nodes/'.$i->{name}.'/ssh_known_hosts',
 @opts,'root@'.$i->{ip}]; }
1;
''')
    # Only this isolated subprocess loads fixture modules; no SSH is executed.
    monkeypatch.setenv('PERL5LIB',str(tmp_path))
    if expected is None:
        with pytest.raises(cluster.ClusterError,match='DNS fallback refused'):
            cluster.ssh_command(node)
    else:
        command=cluster.ssh_command(node)
        assert command[-1]=='root@'+expected
        assert 'HostKeyAlias='+node in command
        assert 'UserKnownHostsFile=/etc/pve/nodes/'+node+'/ssh_known_hosts' in command
        assert '-oStrictHostKeyChecking=yes' in command
