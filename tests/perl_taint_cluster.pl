use strict;
use warnings;
use Scalar::Util qw(tainted);
BEGIN {
    package PVE::RESTHandler;
    our %ROUTES;
    sub register_method { my ($class,$r)=@_; $ROUTES{$r->{name}}=$r; }
    $INC{'PVE/RESTHandler.pm'}=1;
    package PVE::JSONSchema;
    sub get_standard_option { return {type=>'string'}; }
    sub import { no strict 'refs'; *{caller().'::get_standard_option'}=\&get_standard_option; }
    $INC{'PVE/JSONSchema.pm'}=1;
    package PVE::RPCEnvironment;
    sub get { return bless {},__PACKAGE__; }
    sub get_user { return $ENV{ZFSM_TEST_USER}; }
    sub check { return 1; }
    our $FORKS=0;
    sub fork_worker { my ($self,$type,$node,$user,$code)=@_; $FORKS++; $code->(); return 'fixture-upid'; }
    $INC{'PVE/RPCEnvironment.pm'}=1;
}
require 'PVE/API2/ZFSSnapshotViewer.pm';
if ($ENV{ZFSM_TEST_CLEAN_PATH}) { $ENV{PATH}='/usr/bin:/bin'; }
die 'Test must run under -T with tainted inputs' unless ${^TAINT} && tainted($ENV{ZFSM_TEST_NODES}) && tainted($ENV{ZFSM_TEST_PLAN});
require File::Temp;
my ($fh,$path)=File::Temp::tempfile(DIR=>'/tmp',UNLINK=>1);
print $fh "import json, sys\nprint(json.dumps({'args': sys.argv[1:]}))\n";
close($fh);
my ($trusted_fixture)=$path =~ /\A(\/tmp\/[A-Za-z0-9_-]+)\z/;
die 'Unexpected fixture path' unless defined($trusted_fixture);
local $PVE::API2::ZFSSnapshotViewer::CLUSTER_TOOL=$trusted_fixture;
{
    no warnings 'redefine';
    local *PVE::API2::ZFSSnapshotViewer::_preview_secret=sub {return $ENV{ZFSM_TEST_SECRET};};
    my $r=\%PVE::RESTHandler::ROUTES;
    my $p={node=>$ENV{ZFSM_TEST_NODE},lang=>$ENV{ZFSM_TEST_LANG}};
    $r->{cluster_preview}{code}->({%$p,nodes=>$ENV{ZFSM_TEST_NODES}});
    $r->{cluster_install}{code}->({%$p,plan=>$ENV{ZFSM_TEST_PLAN},confirm=>1});
    my $report=$r->{cluster_job}{code}->({%$p,job=>$ENV{ZFSM_TEST_PLAN}});
    die 'Tainted polling ID not passed safely' unless $report->{args}[2] eq $ENV{ZFSM_TEST_PLAN};
    $r->{cluster_status}{code}->($p);
    my $forks=$PVE::RPCEnvironment::FORKS;
    for my $bad('node-a;id','--help','node-a,$(id)') {
        my $ok=eval{$r->{cluster_preview}{code}->({%$p,nodes=>$bad});1};
        die 'Invalid target accepted' if $ok;
    }
    for my $bad('de;id','--help','DE') {
        my $ok=eval{$r->{cluster_preview}{code}->({%$p,lang=>$bad,nodes=>$ENV{ZFSM_TEST_NODES}});1};
        die 'Invalid language accepted' if $ok;
    }
    die 'Invalid input started worker' unless $PVE::RPCEnvironment::FORKS==$forks;
}
print "PASS: real system/open calls under perl -T; preview, install, polling, status and invalid inputs\n";
