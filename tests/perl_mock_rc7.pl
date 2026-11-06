use strict;
use warnings;
BEGIN {
    package PVE::RESTHandler;
    our %ROUTES;
    sub register_method { my ($class,$def)=@_;$ROUTES{$def->{name}}=$def; }
    $INC{'PVE/RESTHandler.pm'}=1;
    package PVE::JSONSchema;
    sub get_standard_option {return {type=>'string'};}
    sub import {no strict 'refs';*{caller().'::get_standard_option'}=\&get_standard_option;}
    $INC{'PVE/JSONSchema.pm'}=1;
    package PVE::RPCEnvironment;
    our $USER='root@pam';our $ALLOWED=1;
    sub get {return bless {},__PACKAGE__;}
    sub get_user {return $USER;}
    sub check {die "RBAC denied\n" unless $ALLOWED;return 1;}
    $INC{'PVE/RPCEnvironment.pm'}=1;
}
require 'PVE/API2/ZFSSnapshotViewer.pm';
my $endpoint=$PVE::RESTHandler::ROUTES{dataset_snapshot_create};
die 'host endpoint fehlt' unless $endpoint;
die 'host route nicht POST' unless $endpoint->{method} eq 'POST';
my $ops=0;
{
  no warnings 'redefine';
  local *PVE::API2::ZFSSnapshotViewer::_guest_lock = sub {return 1};
  local *PVE::API2::ZFSSnapshotViewer::_run_capture = sub {
    my @args=@_;
    die 'unerwartetes Kommando' unless join(' ',@args[0..3]) eq '/usr/sbin/zfs list -H -d';
    return "rpool/ROOT/pve-1\tfilesystem\n";
  };
  local *PVE::API2::ZFSSnapshotViewer::_run_zfs_write = sub {
    my ($subcommand,$dataset)=@_;
    die 'unerwarteter ZFS Befehl' unless $subcommand eq 'snapshot' && $dataset =~ /^rpool\/ROOT\/pve-1\@zfsmgr-/;
    $ops++;
  };
  my $p={node=>'pve',dataset=>'rpool/ROOT/pve-1',confirm=>'CREATE-DATASET:rpool/ROOT/pve-1'};
  my $ok=$endpoint->{code}->($p);
  die 'host snapshot nicht erzeugt' unless $ops==1 && $ok->{dataset} eq 'rpool/ROOT/pve-1';
  my $fail=eval {$endpoint->{code}->({%$p,confirm=>'INVALID'});1};
  die 'unsichere Bestaetigung akzeptiert' if $fail;
  $fail=eval {$endpoint->{code}->({%$p,dataset=>'rpool/data/vm-100-disk-0',confirm=>'CREATE-DATASET:rpool/data/vm-100-disk-0'});1};
  die 'Gast-Policy-Umgehung akzeptiert' if $fail;
  $PVE::RPCEnvironment::USER='guest@pve';
  $fail=eval {$endpoint->{code}->($p);1};
  die 'unberechtigter Host-Snapshot akzeptiert' if $fail;
  $PVE::RPCEnvironment::USER='root@pam!token';
  $fail=eval {$endpoint->{code}->($p);1};
  die 'API-Token akzeptiert' if $fail;
  $PVE::RPCEnvironment::USER='root@pam';
  $PVE::RPCEnvironment::ALLOWED=0;
  $fail=eval {$endpoint->{code}->($p);1};
  die 'Sys.Modify-Sperre umgangen' if $fail;
}
print "PASS: Host-Snapshot, exakte Bestaetigung, Guest-Sperre, Admin- und Token-Pruefung\n";
