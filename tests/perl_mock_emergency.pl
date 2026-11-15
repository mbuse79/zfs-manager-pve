use strict;use warnings;
BEGIN {
 package PVE::RESTHandler; our %ROUTES;
 sub register_method {my($cls,$r)=@_;$ROUTES{$r->{name}}=$r;}
 $INC{'PVE/RESTHandler.pm'}=1;
 package PVE::JSONSchema; sub get_standard_option{return {type=>'string'};}
 sub import {no strict 'refs';*{caller().'::get_standard_option'}=\&get_standard_option;}
 $INC{'PVE/JSONSchema.pm'}=1;
 package PVE::RPCEnvironment; our $USER='root@pam';our $ALLOWED=1;
 sub get{return bless {},__PACKAGE__;}sub get_user{return $USER;}
 sub check{die 'denied' unless $ALLOWED;return 1;}
 $INC{'PVE/RPCEnvironment.pm'}=1;
}
require 'PVE/API2/ZFSSnapshotViewer.pm';
my %e=%PVE::RESTHandler::ROUTES;
for my $name(qw(emergency_status emergency_preview emergency_cleanup emergency_config)){
 die "Missing route $name" unless $e{$name};
}
my $writes=0;my $validations=0;
{
 no warnings 'redefine';
 local *PVE::API2::ZFSSnapshotViewer::_emergency_preview=sub {
   return {pool=>'rpool',dataset=>'rpool',snapshot=>'a'x64,token=>'a'x64,
    digest=>'a'x64,delete_count=>2,targets=>['rpool/data@zfs-auto-snap_hourly-123']};};
 local *PVE::API2::ZFSSnapshotViewer::_verify_preview=sub {$validations++;};
 local *PVE::API2::ZFSSnapshotViewer::_run_emergency_write=sub {$writes++;return {deleted_count=>2};};
 my $base={node=>'pve4',pool=>'rpool',count=>15,token=>'signed',critical_ack=>1,confirm=>'EMERGENCY-DELETE'};
 my $call=$e{emergency_cleanup}{code};
 my $ok=eval {$call->({%$base,confirm=>'NO'});1};
 die 'missing confirmation bypass' if $ok || $writes;
 $ok=eval {$call->({%$base,critical_ack=>0});1};
 die 'critical acknowledgement bypass' if $ok || $writes;
 $PVE::RPCEnvironment::USER='nonadmin@pve';
 $ok=eval {$call->($base);1};
 die 'nonadmin bypass' if $ok || $writes;
 $PVE::RPCEnvironment::USER='root@pam';
 $ok=eval {$call->($base);1};
 die "valid emergency failed: $@" unless $ok && $writes==1 && $validations==1;
}
print "PASS: v34 root-only emergency routes, two confirmations, signed preview verification\n";
