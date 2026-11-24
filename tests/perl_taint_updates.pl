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
local $PVE::API2::ZFSSnapshotViewer::UPDATE_TOOL=$trusted_fixture;
my ($runner_fh,$runner_path)=File::Temp::tempfile(DIR=>'/tmp',UNLINK=>1);
print $runner_fh "#!/usr/bin/python3\nimport os,sys\nargs=sys.argv[1:]\nassert args[0]=='--unit' and args[1].startswith('pve-zfsm-update-')\nassert all(x in args for x in ['--collect','--wait','--pipe','--property=UMask=0077'])\nidx=args.index('/usr/bin/python3')\nos.execv(args[idx],args[idx:])\n";
close($runner_fh);chmod(0755,$runner_path);
my ($trusted_runner)=$runner_path =~ /\A(\/tmp\/[A-Za-z0-9_-]+)\z/;
local $PVE::API2::ZFSSnapshotViewer::UPDATE_RUNNER=$trusted_runner;
{
    no warnings 'redefine';
    local *PVE::API2::ZFSSnapshotViewer::_preview_secret=sub {return $ENV{ZFSM_TEST_SECRET};};
    my $r=\%PVE::RESTHandler::ROUTES;
    my $p={node=>$ENV{ZFSM_TEST_NODE}};
    $r->{update_check}{code}->($p);
    $r->{update_prepare}{code}->($p);
    $r->{update_install}{code}->({%$p,plan=>$ENV{ZFSM_TEST_PLAN},confirm=>1});
    my $job=$r->{update_job}{code}->({%$p,job=>$ENV{ZFSM_TEST_PLAN}});
    die 'Unsafe polling job' unless $job->{args}[2] eq $ENV{ZFSM_TEST_PLAN};
    my $status=$r->{update_status}{code}->($p);
    die 'Status did not use read-only CLI' unless $status->{args}[0] eq 'status';
    my $forks=$PVE::RPCEnvironment::FORKS;
    for my $bad ('a;id','--help','a'x31) {
        my $ok=eval {$r->{update_install}{code}->({%$p,plan=>$bad,confirm=>1});1};
        die 'Bad plan accepted' if $ok;
        $ok=eval {$r->{update_job}{code}->({%$p,job=>$bad});1};
        die 'Bad polling ID accepted' if $ok;
    }
    my $ok=eval {$r->{update_install}{code}->({%$p,plan=>$ENV{ZFSM_TEST_PLAN},confirm=>0});1};
    die 'Missing confirmation accepted' if $ok;
    for my $user ('root@pam!token','operator@pve') {
        local $ENV{ZFSM_TEST_USER}=$user;
        for my $name (qw(update_check update_prepare update_install update_job)) {
            my $ok=eval {$r->{$name}{code}->({%$p,plan=>$ENV{ZFSM_TEST_PLAN},job=>$ENV{ZFSM_TEST_PLAN},confirm=>1});1};
            die 'Non-root/token update accepted' if $ok;
        }
    }
    die 'Rejected request started worker' unless $PVE::RPCEnvironment::FORKS==$forks;
}
for my $case ([['-',('-')x6],0,0], [['false',('true')x6],1,0], [['true',('false')x6],1,0], [['-', 'false',('-')x5],0,1]) {
    my ($values,$excluded,$partial)=@$case;
    my $row=PVE::API2::ZFSSnapshotViewer::_parse_dataset_autosnap(join("\t",'tank/dataset',@$values)."\n");
    die 'Wrong dataset AutoSnap status' unless $row->{autosnap_excluded}==$excluded && $row->{autosnap_partial}==$partial;
}
for my $bad ("tank/dataset\tfalse",join("\t",'tank/dataset;id',('-')x7)) {
    my $ok=eval {PVE::API2::ZFSSnapshotViewer::_parse_dataset_autosnap($bad);1};
    die 'Invalid dataset status accepted' if $ok;
}
die 'Dataset status is not read-only' unless $PVE::RESTHandler::ROUTES{dataset_autosnap_status}{method} eq 'GET';
print "PASS: updater real system/open under perl -T; root-only, tokens, confirmation, safe polling\n";
