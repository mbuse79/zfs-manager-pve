use strict;
use warnings;
BEGIN {
    package PVE::RESTHandler;
    our %ROUTES;
    sub register_method {my ($c,$def)=@_;$ROUTES{$def->{name}}=$def;}
    $INC{'PVE/RESTHandler.pm'}=1;
    package PVE::JSONSchema;
    sub get_standard_option {return {type=>'string'};}
    sub import {no strict 'refs';*{caller().'::get_standard_option'}=\&get_standard_option;}
    $INC{'PVE/JSONSchema.pm'}=1;
    package PVE::RPCEnvironment;
    our $USER='root@pam';
    sub get {return bless {},__PACKAGE__;}
    sub get_user {return $USER;}
    sub check {return 1;}
    $INC{'PVE/RPCEnvironment.pm'}=1;
}
require 'PVE/API2/ZFSSnapshotViewer.pm';
my %routes=%PVE::RESTHandler::ROUTES;
my $writes=0;
{
    no warnings 'redefine';
    local *PVE::API2::ZFSSnapshotViewer::_cluster_task=sub {$writes++;return {job=>'a'x32,upid=>'fixture'};};
    local *PVE::API2::ZFSSnapshotViewer::_admin_identity=sub {return $PVE::RPCEnvironment::USER;};
    local *PVE::API2::ZFSSnapshotViewer::_cluster_json=sub {return {nodes=>[]};};
    for my $key(qw(cluster_status cluster_job cluster_preview cluster_install)) {
        my $r=$routes{$key};
        die 'Route not protected' unless $r->{protected} && $r->{proxyto} eq 'node';
        die 'Missing Sys.Modify' unless $r->{permissions}{check}[2][0] eq 'Sys.Modify';
        for my $user('operator@pve','root@pam!token') {
            $PVE::RPCEnvironment::USER=$user;
            my $ok=eval{$r->{code}->({node=>'fixture',job=>'a'x32,plan=>'a'x32,nodes=>'node-a',confirm=>1});1};
            die 'Non-root or token allowed' if $ok || $writes;
        }
    }
    $PVE::RPCEnvironment::USER='root@pam';
    for my $p({node=>'fixture',nodes=>'node-a;id'}, {node=>'fixture',nodes=>'-oProxyCommand=id'}) {
        my $ok=eval{$routes{cluster_preview}{code}->($p);1};
        die 'Unsafe node accepted' if $ok || $writes;
    }
    for my $p({node=>'fixture',plan=>'a'x32,confirm=>0}, {node=>'fixture',plan=>'../outside',confirm=>1}) {
        my $ok=eval{$routes{cluster_install}{code}->($p);1};
        die 'Unconfirmed or unsafe plan accepted' if $ok || $writes;
    }
    $routes{cluster_install}{code}->({node=>'fixture',plan=>'a'x32,confirm=>1});
    die 'Confirmed root operation blocked' unless $writes==1;
}
{
    require File::Temp;
    my ($fh,$name)=File::Temp::tempfile(UNLINK=>1);
    print $fh "import json, sys\nprint(json.dumps({'log': 'x' * int(sys.argv[1])}))\n";
    close($fh);
    local $PVE::API2::ZFSSnapshotViewer::CLUSTER_TOOL=$name;
    my $report=PVE::API2::ZFSSnapshotViewer::_cluster_json('200000');
    die 'Large multi-node report truncated' unless length($report->{log})==200000;
    my $ok=eval{PVE::API2::ZFSSnapshotViewer::_cluster_json('2200000');1};
    die 'Unbounded cluster report accepted' if $ok || $@ !~ /Cluster report too large/;
}
print "PASS: cluster deployment is root-only, token-blocked, confirmed and scoped\n";
