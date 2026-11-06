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
my %e=%PVE::RESTHandler::ROUTES;
for my $key(qw(guest_snapshot_delete guest_rollback guest_snapshot_delete_preview guest_rollback_preview
               host_snapshot_delete host_rollback host_snapshot_delete_preview host_rollback_preview)) {
    die "Endpoint fehlt: $key" unless $e{$key};
    die "Admin-Privileg fehlt: $key" unless $e{$key}{permissions}{check}[2][0] eq 'Sys.Modify';
}
for my $key(qw(host_snapshot_delete host_rollback)) {
    die "Zweite HOST-Checkbox in API fehlt" unless exists $e{$key}{parameters}{properties}{critical_ack};
}
my $writes=0;
{
    no warnings 'redefine';
    local *PVE::API2::ZFSSnapshotViewer::_guest_lock = sub {return 1};
    local *PVE::API2::ZFSSnapshotViewer::_delete_guest_plan = sub {
        return {dataset=>'rpool/data/subvol-100-disk-0',snapshot=>'snap-old',
            delete_list=>['snap-old','snap-new'],delete_count=>2,
            newer=>['snap-new'],newer_count=>1,delete_last=>'snap-new',high_risk=>0,
            token=>'stub',bounded_range=>'bounded'};
    };
    local *PVE::API2::ZFSSnapshotViewer::_rollback_preview = sub {
        return {dataset=>'rpool/data/subvol-100-disk-0',snapshot=>'snap-old',
            newer=>['snap-new'],newer_count=>1,high_risk=>0,token=>'stub',
            disks=>[{dataset=>'rpool/data/subvol-100-disk-0',newer=>['snap-new'],newer_count=>1,bounded_range=>'bounded'}]};
    };
    local *PVE::API2::ZFSSnapshotViewer::_host_plan = sub {
        my ($ds,$snap,$mode)=@_;
        return {dataset=>$ds,snapshot=>$snap,token=>'stub',high_risk=>1,
            newer=>['new'],newer_count=>1,delete_list=>['old','new'],delete_count=>2,
            delete_last=>'new',bounded_range=>'bounded',
            allowed_to_execute=>($ds eq 'rpool/ROOT/pve-1' ? 0 : 1)};
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
    my $ok=eval{$e{guest_snapshot_delete}{code}->($dk);1};
    die "Gast-Löschen mit nur einer Checkbox gesperrt: $@" unless $ok && $writes==1;
    $writes=0;
    $ok=eval{$e{guest_rollback}{code}->({%$base,confirm=>'ROLLBACK:snap-old'});1};
    die "Gast-Rollback mit nur einer Checkbox gesperrt: $@" unless $ok && $writes==2;
    $writes=0;
    my $hd={%$base,dataset=>'rpool/ROOT/pve-1',confirm=>'HOST-DELETE:snap-old'};
    $ok=eval{$e{host_snapshot_delete}{code}->($hd);1};
    die 'Host-Loeschung ohne zweite Checkbox erlaubt' if $ok || $writes;
    $ok=eval{$e{host_snapshot_delete}{code}->({%$hd,critical_ack=>1});1};
    die "Host-Löschung trotz Doppelbestätigung gesperrt: $@" unless $ok && $writes==1;
    $writes=0;
    my $hr={%$hd,confirm=>'HOST-ROLLBACK:snap-old',critical_ack=>1};
    $ok=eval{$e{host_rollback}{code}->($hr);1};
    die 'Aktives Boot-Dataset live zurückgesetzt!' if $ok || $writes;
    $hr->{dataset}='pool/standalone';
    $ok=eval{$e{host_rollback}{code}->($hr);1};
    die "Unmounted Host-Rollback gesperrt: $@" unless $ok && $writes==2;
    $writes=0;
    $PVE::RPCEnvironment::USER='operator@pve';
    $ok=eval{$e{guest_snapshot_delete}{code}->($dk);1};
    die 'Nicht-Admin darf Gast löschen!' if $ok || $writes;
    $ok=eval{$e{host_snapshot_delete}{code}->({%$hd,critical_ack=>1});1};
    die 'Nicht-Admin darf Host löschen!' if $ok || $writes;
    $PVE::RPCEnvironment::USER='root@pam!token';
    $ok=eval{$e{host_snapshot_delete}{code}->({%$hd,critical_ack=>1});1};
    die 'API token darf Host löschen!' if $ok || $writes;
    $PVE::RPCEnvironment::USER='root@pam';$PVE::RPCEnvironment::ALLOWED=0;
    $ok=eval{$e{guest_rollback}{code}->({%$base,confirm=>'ROLLBACK:snap-old'});1};
    die 'Gast-Rollback trotz verweigertem Sys.Modify!' if $ok || $writes;
}
print "PASS: Guests one checkbox; hosts two; active-root rollback blocked; RBAC and API tokens enforced\n";
