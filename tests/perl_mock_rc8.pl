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
    our $USER='root@pam'; our $ALLOWED=1;
    sub get {return bless {},__PACKAGE__;}
    sub get_user {return $USER;}
    sub check {die 'permission denied' unless $ALLOWED;return 1;}
    $INC{'PVE/RPCEnvironment.pm'}=1;
}
require 'PVE/API2/ZFSSnapshotViewer.pm';
my $mod='PVE::API2::ZFSSnapshotViewer';
my $create=$PVE::RESTHandler::ROUTES{dataset_snapshot_create};
my $delete=$PVE::RESTHandler::ROUTES{guest_snapshot_delete};
my $rollback=$PVE::RESTHandler::ROUTES{guest_rollback};
my $delete_preview=$PVE::RESTHandler::ROUTES{guest_snapshot_delete_preview};
my $rollback_preview=$PVE::RESTHandler::ROUTES{guest_rollback_preview};
for my $ep ($create,$delete,$rollback,$delete_preview,$rollback_preview) {die 'missing guarded endpoint' unless $ep;}
for my $ep ($delete,$rollback) {
    die 'missing admin permission' unless $ep->{permissions}{check}[2][0] eq 'Sys.Modify';
    die 'missing second checkbox API gate' unless $ep->{parameters}{properties}{critical_ack};
}
my $writes=0;
{
    no warnings 'redefine';
    local *PVE::API2::ZFSSnapshotViewer::_guest_lock = sub {return 1};
    local *PVE::API2::ZFSSnapshotViewer::_delete_guest_plan = sub {
        return {dataset=>'rpool/data/subvol-100-disk-0',snapshot=>'snap-old',
            delete_list=>['snap-old','snap-new'], delete_count=>2,
            newer=>['snap-new'],newer_count=>1, delete_last=>'snap-new',high_risk=>1,token=>'stub'};
    };
    local *PVE::API2::ZFSSnapshotViewer::_rollback_preview = sub {
        return {dataset=>'rpool/data/subvol-100-disk-0',snapshot=>'snap-old',
            newer=>['snap-new'],newer_count=>1,high_risk=>1,token=>'stub'};
    };
    local *PVE::API2::ZFSSnapshotViewer::_verify_preview = sub {return 1};
    local *PVE::API2::ZFSSnapshotViewer::_check_clone_dependencies = sub {return 1};
    local *PVE::API2::ZFSSnapshotViewer::_check_snapshot_holds = sub {return 1};
    local *PVE::API2::ZFSSnapshotViewer::_dry_run_destroy_range = sub {return ('bounded','dry-run')};
    local *PVE::API2::ZFSSnapshotViewer::_assert_no_bookmarks = sub {return 1};
    local *PVE::API2::ZFSSnapshotViewer::_run_zfs_write = sub {$writes++;return 1};
    my $base={node=>'pvetest2',dataset=>'rpool/data/subvol-100-disk-0',snapshot=>'snap-old',
        token=>'1234567890.'.('a'x64)};
    my $dk={%$base,confirm=>'DELETE-RANGE:snap-old'};
    my $ok=eval{$delete->{code}->($dk);1};
    die 'CRITICAL delete bypass without second acknowledgement' if $ok || $writes;
    $ok=eval{$delete->{code}->({%$dk,critical_ack=>0});1};
    die 'CRITICAL delete bypass with unchecked checkbox' if $ok || $writes;
    $ok=eval{$delete->{code}->({%$dk,critical_ack=>1});1};
    die "valid critical delete denied: $@" unless $ok && $writes==1;
    $writes=0;
    my $rb={%$base,confirm=>'ROLLBACK:snap-old'};
    $ok=eval{$rollback->{code}->($rb);1};
    die 'rollback bypass without extra checkbox' if $ok || $writes;
    $ok=eval{$rollback->{code}->({%$rb,critical_ack=>1});1};
    die "valid rollback denied: $@" unless $ok && $writes==2;
    $writes=0;
    $PVE::RPCEnvironment::USER='operator@pve';
    $ok=eval{$delete->{code}->({%$dk,critical_ack=>1});1};
    die 'non-admin delete bypass' if $ok || $writes;
    $ok=eval{$rollback->{code}->({%$rb,critical_ack=>1});1};
    die 'non-admin rollback bypass' if $ok || $writes;
    $PVE::RPCEnvironment::USER='root@pam!token';
    $ok=eval{$delete->{code}->({%$dk,critical_ack=>1});1};
    die 'API token delete bypass' if $ok || $writes;
    $PVE::RPCEnvironment::USER='root@pam';
    $PVE::RPCEnvironment::ALLOWED=0;
    $ok=eval{$rollback->{code}->({%$rb,critical_ack=>1});1};
    die 'Sys.Modify denied user bypass' if $ok || $writes;
}
print "PASS: Critical delete/rollback second confirmation required server-side; unauthorised users and tokens rejected\n";
