use strict; use warnings;
BEGIN {
 package PVE::RESTHandler; our %ROUTES;
 sub register_method {my($class,$def)=@_;$ROUTES{$def->{name}}=$def;}
 $INC{'PVE/RESTHandler.pm'}=1;
 package PVE::JSONSchema; sub get_standard_option {return {type=>'string'};}
 sub import {no strict 'refs';*{caller().'::get_standard_option'}=\&get_standard_option;}
 $INC{'PVE/JSONSchema.pm'}=1;
 package PVE::RPCEnvironment; our $USER='root@pam'; our $ALLOWED=1;
 sub get {return bless {},__PACKAGE__;} sub get_user{return $USER;}
 sub check {die 'permission denied' unless $ALLOWED;return 1;}
 $INC{'PVE/RPCEnvironment.pm'}=1;
}
require 'PVE/API2/ZFSSnapshotViewer.pm';
use JSON::PP qw(encode_json);
use Scalar::Util qw(tainted);
my %routes=%PVE::RESTHandler::ROUTES;
my @ds=($ENV{ZFSM_TEST_DATASET},'tank/data/vm-101-disk-1');
my ($kind,$id,$running,$protected,$hold,$clone,$bookmark,$failure)=('vm',101,0,0,0,0,0,0);
my $fingerprint='a'x64;
my @writes;
my %snaps=($ds[0]=>[{name=>'manual',created=>1,txg=>1},{name=>'daily',created=>2,txg=>2}],
           $ds[1]=>[{name=>'hourly',created=>3,txg=>3}]);
my $propstate="com.sun:auto-snapshot\ttrue\tlocal\n";
my $extra=0;
my ($inventory_base,$inventory_interval,$wrong_owner)=('true','-',0);
sub call {my ($name,$p)=@_;return $routes{$name}{code}->({node=>'fixture-node',guest=>$kind,vmid=>$id,%{$p||{}}});}
sub blocked {my ($code,$pattern)=@_;@writes=();eval {$code->();1} and die 'Expected rejection';
    die "Wrong rejection: $@" unless $@ =~ $pattern;die 'Write before rejection' if @writes;}
{
 no warnings 'redefine';
 local *PVE::API2::ZFSSnapshotViewer::_guest_lock=sub {1};
 local *PVE::API2::ZFSSnapshotViewer::_preview_secret=sub {'b'x64};
 local *PVE::API2::ZFSSnapshotViewer::_guest_access_rows=sub {
     return [map {{dataset=>$_,guest=>$kind,vmid=>$id}} (@ds,($extra?'tank/data/new-disk':()))];
 };
 local *PVE::API2::ZFSSnapshotViewer::_validate_test_guest=sub {
     my ($ds,$stop)=@_;die "Guest must stop\n" if $stop && $running;
     return {dataset=>$ds,guest=>$kind,vmid=>($wrong_owner ? $id+1 : $id),fingerprint=>$fingerprint,
        protected=>$protected,can_create=>!$protected,can_delete=>!$protected};
 };
 local *PVE::API2::ZFSSnapshotViewer::_list_guest_snaps=sub {$snaps{$_[0]}||[]};
 local *PVE::API2::ZFSSnapshotViewer::_assert_no_bookmarks=sub {die "bookmark\n" if $bookmark};
 local *PVE::API2::ZFSSnapshotViewer::_check_snapshot_holds=sub {die "hold\n" if $hold};
 local *PVE::API2::ZFSSnapshotViewer::_check_clone_dependencies=sub {die "clone\n" if $clone};
 local *PVE::API2::ZFSSnapshotViewer::_run_capture=sub {
     my @a=@_;
     die 'tainted process argument' if grep {tainted($_)} @a;
     if ($a[1] eq 'set') {
         die 'tainted set argument' if grep {tainted($_)} @a;
         push @writes,\@a;return '';
     }
     if ($a[1] eq 'get' && $a[4] eq 'name,property,value') {
         my @lines;
         for my $ds (@ds) {
             for my $prop (PVE::API2::ZFSSnapshotViewer::_autosnap_properties()) {
                 push @lines,join("\t",$ds,$prop,$prop eq 'com.sun:auto-snapshot' ? $inventory_base : $inventory_interval);
             }
         }
         return join("\n",@lines)."\n";
     }
     return $propstate if $a[1] eq 'get';
     die 'Unexpected command' unless $a[1] eq 'destroy' && $a[2] eq '-n';
     return 'dry run';
 };
 local *PVE::API2::ZFSSnapshotViewer::_run_zfs_write=sub {
     die 'tainted write argument' if grep {tainted($_)} @_;
     die "injected failure\n" if $failure && @writes==1;
     push @writes,[@_];
 };
 for my $case (['false','true',1],['true','false',1],['true','-',0],['False','-',1]) {
     ($inventory_base,$inventory_interval,my $expected)=@$case;
     @writes=();my $rows=$routes{guest_access}{code}->({node=>'fixture-node'});
     die 'Wrong effective AutoSnap status' if grep {$_->{autosnap_excluded} != $expected} @$rows;
     die 'Inventory wrote' if @writes;
 }
 $wrong_owner=1;blocked(sub {call('guest-delete-all-preview')},qr/Gastzuordnung/);$wrong_owner=0;
 for my $type ('vm','lxc') {
     $kind=$type;
     @writes=();my $plan=call('guest-delete-all-preview');
     die 'Preview wrote or omitted partial snapshot groups' unless !@writes && $plan->{delete_count}==3;
     my $params={token=>$plan->{token},confirm=>"GUEST-DELETE-ALL:$kind:$id",critical_ack=>1};
     call('guest-delete-all',$params);
     die 'Wrong delete targets' unless encode_json(\@writes) eq encode_json([
         ['destroy',"$ds[0]\@manual"],['destroy',"$ds[0]\@daily"],['destroy',"$ds[1]\@hourly"]]);
     blocked(sub {call('guest-delete-all',{%$params,critical_ack=>0})},qr/Warnung/);
     blocked(sub {call('guest-delete-all',{%$params,confirm=>'wrong'})},qr/Bestaetigung/);
     $running=1;blocked(sub {call('guest-delete-all',$params)},qr/stop/);$running=0;
     for my $flag (\$hold,\$clone,\$bookmark,\$protected) {
         $$flag=1;blocked(sub {call('guest-delete-all',$params)},qr/hold|clone|bookmark|Geschuetzter/);$$flag=0;
     }
     $extra=1;blocked(sub {call('guest-delete-all',$params)},qr/geaendert/);$extra=0;
     push @{$snaps{$ds[1]}},{name=>'new',created=>4,txg=>4};
     blocked(sub {call('guest-delete-all',$params)},qr/geaendert/);pop @{$snaps{$ds[1]}};
     $fingerprint='c'x64;blocked(sub {call('guest-delete-all',$params)},qr/geaendert/);$fingerprint='a'x64;
     $failure=1;@writes=();eval {call('guest-delete-all',$params)};
     die 'No partial failure report or continued writes' unless $@ =~ /abgeschlossen:.*manual.*fehlgeschlagen\/unklar:.*daily/ && @writes==1;
     $failure=0;
     for my $excluded (0,1) {
         @writes=();$running=1;my $preview=call('guest-autosnap-preview',{excluded=>$excluded});
         die 'AutoSnap preview wrote' if @writes;
         my $p={token=>$preview->{token},confirm=>"GUEST-AUTOSNAP:$kind:$id",critical_ack=>1,excluded=>$excluded};
         call('guest-autosnap',$p);
         die 'Missing disk or label properties' unless @writes==2 && @{$writes[0]}==10;
         die 'Wrong AutoSnap value' unless $writes[0][2] eq 'com.sun:auto-snapshot='.($excluded?'false':'true')
             && $writes[0][8] eq 'com.sun:auto-snapshot:yearly='.($excluded?'false':'true');
         blocked(sub {call('guest-autosnap',{%$p,excluded=>1-$excluded})},qr/geaendert/);
         $propstate.="changed\n";blocked(sub {call('guest-autosnap',$p)},qr/geaendert/);$propstate=~s/changed\n$//;
         $extra=1;blocked(sub {call('guest-autosnap',$p)},qr/geaendert/);$extra=0;
         $running=0;
     }
 }
 for my $user ('operator@pve','root@pam!token') {
     $PVE::RPCEnvironment::USER=$user;
     for my $route (qw(guest-delete-all-preview guest-delete-all guest-autosnap-preview guest-autosnap)) {
         blocked(sub {call($route,{excluded=>1})},qr/Administrator|API-Token/);
     }
 }
 $PVE::RPCEnvironment::USER='root@pam';
 $PVE::RPCEnvironment::ALLOWED=0;
 blocked(sub {call('guest-delete-all-preview')},qr/permission/);
 $PVE::RPCEnvironment::ALLOWED=1;
 %snaps=();blocked(sub {call('guest-delete-all-preview')},qr/Keine Snapshots/);
 # Data from an external source must be recaptured before the property exec.
 my $tainted=$ENV{ZFSM_TEST_DATASET};
 die 'Missing tainted input' unless tainted($tainted);
 @writes=();PVE::API2::ZFSSnapshotViewer::_set_guest_autosnap($tainted,1);
 die 'Taint-safe property write not attempted' unless @writes==1;
 blocked(sub {PVE::API2::ZFSSnapshotViewer::_set_guest_autosnap('tank/data;touch /tmp/no',1)},qr/Dataset/);
}
print "PASS: guest-wide exact deletion and AutoSnap; VM/LXC, partial groups, preview HMAC/state, permissions, protections, failures and taint\n";
