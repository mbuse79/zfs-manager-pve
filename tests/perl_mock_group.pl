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
my %e=%PVE::RESTHandler::ROUTES;
for my $ep(qw(guest_group_create group_delete_preview group_delete group_rollback_preview group_rollback)) {
 die "Missing: $ep" unless $e{$ep};
}
my @executed;
{
 no warnings 'redefine';
 local *PVE::API2::ZFSSnapshotViewer::_guest_lock=sub{return 1};
 local *PVE::API2::ZFSSnapshotViewer::_validate_test_guest=sub {
  my($ds,$stopped,$rollback,$create)=@_;
  return {dataset=>$ds,guest=>'vm',vmid=>990,fingerprint=>('f'x64),
   protected=>0,can_create=>1,can_delete=>1};
 };
 local *PVE::API2::ZFSSnapshotViewer::_run_zfs_write=sub {push @executed, [@_];};
 my $selection='["rpool/data/vm-990-disk-0","rpool/data/vm-990-disk-1"]';
 my $res=$e{guest_group_create}{code}->({node=>'pvetest2',selection=>$selection,confirm=>'CREATE-GROUP'});
 die 'Missing two selected disks' unless $res->{disk_count}==2 && @executed==1 &&
  @{$executed[0]}==3 && $executed[0][0] eq 'snapshot';
 @executed=();
 my $bad='["rpool/data/vm-990-disk-0","rpool/data/vm-990-disk-0"]';
 my $ok=eval{$e{guest_group_create}{code}->({node=>'pvetest2',selection=>$bad,confirm=>'CREATE-GROUP'});1};
 die 'duplicate disks permitted' if $ok || @executed;
 $ok=eval{$e{guest_group_create}{code}->({node=>'pvetest2',selection=>$selection,confirm=>'WRONG'});1};
 die 'missing confirmation permitted' if $ok || @executed;
 $PVE::RPCEnvironment::USER='operator@pve';
 $ok=eval{$e{guest_group_create}{code}->({node=>'pvetest2',selection=>$selection,confirm=>'CREATE-GROUP'});1};
 die 'operator permitted' if $ok || @executed;
}

{
 no warnings 'redefine';
 local *PVE::API2::ZFSSnapshotViewer::_guest_lock=sub{return 1};
 local *PVE::API2::ZFSSnapshotViewer::_validate_test_guest=sub {
  my($ds)=@_; return {dataset=>$ds,guest=>'vm',vmid=>990,fingerprint=>('f'x64),
    protected=>0,can_create=>1,can_delete=>1};
 };
 local *PVE::API2::ZFSSnapshotViewer::_guest_plan=sub {
   my($ds,$snap)=@_; return {dataset=>$ds,snapshot=>$snap,token=>'internal',
     newer=>['new'],newer_count=>1};
 };
 local *PVE::API2::ZFSSnapshotViewer::_delete_guest_plan=sub {
   my($ds,$snap)=@_;return {dataset=>$ds,snapshot=>$snap,token=>'internal',
     newer=>['new'],newer_count=>1,bounded_range=>"$ds\@old%new",delete_count=>2};
 };
 local *PVE::API2::ZFSSnapshotViewer::_assert_no_bookmarks=sub {return 1};
 local *PVE::API2::ZFSSnapshotViewer::_check_clone_dependencies=sub {return 1};
 local *PVE::API2::ZFSSnapshotViewer::_check_snapshot_holds=sub {return 1};
 local *PVE::API2::ZFSSnapshotViewer::_dry_run_destroy_range=sub {
   my($ds)=@_;return ("$ds\@new",'dry run');
 };
 local *PVE::API2::ZFSSnapshotViewer::_verify_preview=sub{return 1};
 local *PVE::API2::ZFSSnapshotViewer::_sign_preview=sub {my($p)=@_;$p->{token}='test';return $p};
 local *PVE::API2::ZFSSnapshotViewer::_run_zfs_write=sub {push @executed, [@_];};
 $PVE::RPCEnvironment::USER='root@pam';
 my $sel='["rpool/data/vm-990-disk-0","rpool/data/vm-990-disk-1"]';
 my $pv=$e{group_delete_preview}{code}->({node=>'pvetest2',selection=>$sel,snapshot=>'old'});
 die 'group delete preview mismatch' unless $pv->{disk_count}==2;
 @executed=();
 my $r=$e{group_delete}{code}->({node=>'pvetest2',selection=>$sel,snapshot=>'old',
   confirm=>'GROUP-DELETE:old',token=>'test'});
 die 'group delete did not target both disks' unless $r->{disk_count}==2 && @executed==2 &&
  $executed[0][0] eq 'destroy' && $executed[1][0] eq 'destroy';
 @executed=();
 $pv=$e{group_rollback_preview}{code}->({node=>'pvetest2',selection=>$sel,snapshot=>'old'});
 die 'group rollback preview mismatch' unless $pv->{disk_count}==2;
 $r=$e{group_rollback}{code}->({node=>'pvetest2',selection=>$sel,snapshot=>'old',
  confirm=>'GROUP-ROLLBACK:old',token=>'test'});
 die 'group rollback did not target both disks' unless $r->{disk_count}==2 &&
  @executed==4 && $executed[0][0] eq 'destroy' && $executed[1][0] eq 'rollback' &&
  $executed[2][0] eq 'destroy' && $executed[3][0] eq 'rollback';
}

print "PASS: grouped snapshot creates two disks in one ZFS call; duplicate, confirmation, RBAC checks; group delete/rollback previews and execution\n";
