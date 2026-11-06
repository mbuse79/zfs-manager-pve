package PVE::API2::ZFSSnapshotViewer;

use strict;
use warnings;
use base qw(PVE::RESTHandler);
use PVE::JSONSchema qw(get_standard_option);

# Base inventory endpoints are read-only; write actions are separately authorized and scoped.
# Authenticated, node-scoped Proxmox API; no additional listener or port.
# Parse each row independent of Perl's dynamic regex capture variables.
# Another regex check would reset $1/$2, so copy the captures immediately.
# v0.11: writing retention and destructive snapshots requires the actual
# authenticated PVE administrator, not merely the broadly delegable Sys.Modify.
# Conservative TEST policy: root@pam only, API tokens are intentionally refused.
# Other Administrator-role identities need a separately audited role check.
use PVE::RPCEnvironment;
use JSON::PP qw(decode_json);
use Digest::SHA qw(hmac_sha256_hex sha256_hex);
use Fcntl qw(O_RDONLY O_NOFOLLOW);
our $ADMINS_FILE = '/etc/pve-zfs-manager/admins.conf';
our $PREVIEW_SECRET = '/etc/pve-zfs-manager/preview.key';
our $GUEST_POLICY = '/usr/local/libexec/pve-zfs-manager/guest_policy.py';

sub _admin_identity {
    my ($node) = @_;
    die "Knoten fehlt\n" unless defined($node) && $node =~ /\A[a-zA-Z0-9][a-zA-Z0-9.-]{0,127}\z/;
    my $rpcenv = PVE::RPCEnvironment::get();
    die "Sitzung nicht authentifiziert\n" unless defined $rpcenv;
    my $user = $rpcenv->get_user();
    die "API-Token sind fuer kritische Aktionen gesperrt\n"
        unless defined($user) && $user =~ /\A[a-zA-Z0-9_.@-]{3,128}\z/ && $user !~ /!/;
    $rpcenv->check($user, "/nodes/$node", ['Sys.Modify']);
    if ($user ne 'root@pam') {
        # Administrator ACL AND explicit root-controlled allowlist required.
        $rpcenv->check($user, '/', ['Permissions.Modify']);
        my @st = lstat($ADMINS_FILE);
        die "Administratorfreigabeliste fehlt oder ist unsicher\n"
            unless @st && -f _ && !-l $ADMINS_FILE && $st[4] == 0
              && ($st[2] & 0777) == 0600 && $st[7] < 8192;
        sysopen(my $fh, $ADMINS_FILE, O_RDONLY|O_NOFOLLOW) or die "Administratorliste nicht lesbar\n";
        my @users = <$fh>;
        close($fh);
        die "Keine ausdrueckliche Administratorfreigabe fuer $user\n"
            unless grep { my $v = $_; chomp($v); $v eq $user } @users;
    }
    return $user;
}
sub _require_zfsmgr_admin { my ($node) = @_; _admin_identity($node); return 1; }

sub _preview_secret {
    my @st = lstat($PREVIEW_SECRET);
    die "Vorschau-Schluessel fehlt oder ist unsicher\n"
        unless @st && -f _ && !-l $PREVIEW_SECRET && $st[4] == 0
            && ($st[2] & 0777) == 0600 && $st[7] >= 64 && $st[7] <= 256;
    sysopen(my $fh, $PREVIEW_SECRET, O_RDONLY|O_NOFOLLOW) or die "Vorschau-Schluessel nicht lesbar\n";
    my $key = <$fh>;
    close($fh);
    die "Vorschau-Schluessel ungueltig\n" unless defined($key) && $key =~ /\A[a-f0-9]{64}\s*\z/;
    $key =~ s/\s+\z//;
    return $key;
}
sub _preview_hmac {
    my ($mode,$plan,$expires) = @_;
    my $user = PVE::RPCEnvironment::get()->get_user();
    return hmac_sha256_hex(join('|','ZFSMGR-V1',$mode,$user,$plan->{dataset},
        $plan->{snapshot},$plan->{token},$expires),_preview_secret());
}
sub _sign_preview {
    my ($plan,$mode) = @_;
    my $expires = time + 300;
    $plan->{token} = $expires . '.' . _preview_hmac($mode,$plan,$expires);
    $plan->{expires_seconds} = 300;
    return $plan;
}
sub _verify_preview {
    my ($plan,$mode,$supplied) = @_;
    die "Ungueltiges Vorschau-Token\n"
        unless defined($supplied) && $supplied =~ /\A(\d{10})\.([a-f0-9]{64})\z/;
    my ($expires,$mac) = ($1,$2);
    die "Vorschau abgelaufen; neue Vorschau erforderlich\n"
        if $expires <= time || $expires > time+300;
    die "Vorschau abgelaufen oder geaendert; neue Vorschau erforderlich\n"
        unless $mac eq _preview_hmac($mode,$plan,$expires);
}

sub _parse_snapshot_row {
    my ($line) = @_;
    chomp($line);
    my @columns = split(/\t/, $line, -1);
    die "Unerwartetes ZFS-Datenformat\n" if @columns != 4;
    my ($name, $creation, $used, $refer) = @columns;
    my ($dataset, $snapshot) = $name =~ /\A([^\t\n\r@]+)@([^\t\n\r@]+)\z/;
    die "Unerwartetes ZFS-Datenformat\n"
        if !defined($dataset) || !defined($snapshot)
        || $creation !~ /\A\d+\z/ || $used !~ /\A\d+\z/ || $refer !~ /\A\d+\z/;
    return {
        name => $name,
        dataset => $dataset,
        snapshot => $snapshot,
        creation => 0 + $creation,
        used => 0 + $used,
        referenced => 0 + $refer,
    };
}

__PACKAGE__->register_method({
    name => 'snapshots',
    path => 'snapshots',
    method => 'GET',
    proxyto => 'node',
    protected => 1,
    permissions => {
        check => ['perm', '/nodes/{node}', ['Sys.Audit']],
    },
    description => 'Read-only listing of ZFS snapshots on this node.',
    parameters => {
        additionalProperties => 0,
        properties => { node => get_standard_option('pve-node') },
    },
    returns => {
        type => 'array',
        items => { type => 'object', additionalProperties => 1 },
    },
    code => sub {
        my ($param) = @_;
        my @rows;
        my $err;
        my $fh;
        my $ok = eval {
            local $SIG{ALRM} = sub { die "ZFS-Snapshot-Liste: Zeitlimit ueberschritten\n" };
            alarm(20);
            open($fh, '-|', '/usr/sbin/zfs', 'list', '-H', '-p', '-t', 'snapshot',
                '-o', 'name,creation,used,refer', '-s', 'creation')
                or die "zfs list konnte nicht gestartet werden: $!\n";
            while (my $line = <$fh>) {
                die "ZFS-Snapshot-Liste zu gross (maximal 10000 Eintraege)\n" if @rows >= 10_000;
                die "Unerwartet lange ZFS-Ausgabe\n" if length($line) > 4096;
                push @rows, _parse_snapshot_row($line);
            }
            close($fh) or die "zfs list ist fehlgeschlagen\n";
            alarm(0);
            1;
        };
        $err = $@ if !$ok;
        alarm(0);
        if ($err) {
            close($fh) if defined($fh) && defined(fileno($fh));
            die $err;
        }
        return \@rows;
    },
});

# Read-only dataset inventory includes filesystems and zvols without snapshots.
sub _parse_dataset_row {
    my ($line) = @_;
    chomp($line);
    my @columns = split(/\t/, $line, -1);
    die "Unerwartetes ZFS-Dataset-Format\n" if @columns != 5;
    my ($name, $type, $used, $available, $mountpoint) = @columns;
    die "Unerwartetes ZFS-Dataset-Format\n"
        if $name !~ /\A[^\t\n\r\@]+\z/
        || $type !~ /\A(?:filesystem|volume)\z/
        || $used !~ /\A\d+\z/
        || $available !~ /\A(?:\d+|-)\z/;
    return {
        name => $name,
        type => $type,
        used => 0 + $used,
        available => ($available eq '-' ? undef : 0 + $available),
        mountpoint => ($mountpoint eq '-' ? undef : $mountpoint),
    };
}

__PACKAGE__->register_method({
    name => 'datasets',
    path => 'datasets',
    method => 'GET',
    proxyto => 'node',
    protected => 1,
    permissions => {
        check => ['perm', '/nodes/{node}', ['Sys.Audit']],
    },
    description => 'Read-only inventory of ZFS filesystems and volumes on this node.',
    parameters => {
        additionalProperties => 0,
        properties => { node => get_standard_option('pve-node') },
    },
    returns => {
        type => 'array',
        items => { type => 'object', additionalProperties => 1 },
    },
    code => sub {
        my ($param) = @_;
        my @rows;
        my $fh;
        my $ok = eval {
            local $SIG{ALRM} = sub { die "ZFS-Dataset-Liste: Zeitlimit ueberschritten\n" };
            alarm(20);
            open($fh, '-|', '/usr/sbin/zfs', 'list', '-H', '-p',
                '-t', 'filesystem,volume', '-o', 'name,type,used,avail,mountpoint')
                or die "zfs list konnte nicht gestartet werden: $!\n";
            while (my $line = <$fh>) {
                die "ZFS-Dataset-Liste zu gross (maximal 10000 Eintraege)\n" if @rows >= 10_000;
                die "Unerwartet lange ZFS-Ausgabe\n" if length($line) > 4096;
                push @rows, _parse_dataset_row($line);
            }
            close($fh) or die "zfs list ist fehlgeschlagen\n";
            alarm(0);
            1;
        };
        my $err = $@ if !$ok;
        alarm(0);
        if ($err) {
            close($fh) if defined($fh) && defined(fileno($fh));
            die $err;
        }
        return \@rows;
    },
});

# Retention configuration is read from the existing distro cron entries.
# Cron retention read endpoint; separate Sys.Modify endpoint edits only a validated --keep value.
our %RETENTION_CRON_FILES = (
    frequent => '/etc/cron.d/zfs-auto-snapshot',
    hourly => '/etc/cron.hourly/zfs-auto-snapshot',
    daily => '/etc/cron.daily/zfs-auto-snapshot',
    weekly => '/etc/cron.weekly/zfs-auto-snapshot',
    monthly => '/etc/cron.monthly/zfs-auto-snapshot',
    yearly => '/etc/cron.d/pve-zfs-manager-yearly',
);

sub _read_retention_file {
    my ($label, $file) = @_;
    die "Nicht unterstuetztes Zeitplanformat\n"
        unless defined($label) && $label =~ /\A(?:frequent|hourly|daily|weekly|monthly|yearly)\z/;
    die "Zeitplandatei fehlt oder ist ein Symlink: $file\n" if !-f $file || -l $file;
    open my $fh, '<', $file or die "Zeitplandatei konnte nicht gelesen werden: $!\n";
    my @lines = <$fh>;
    close($fh) or die "Lesefehler in Zeitplandatei\n";
    die "Zeitplandatei zu gross\n" if @lines > 200;
    my @found;
    for my $line (@lines) {
        die "Zeitplan-Zeile zu lang\n" if length($line) > 2048;
        # Our own marker makes the one intended cron command inert without --keep=0.
        my $disabled = ($line =~ s/\A# PVE-ZFS-MANAGER-DISABLED //);
        next if !$disabled && $line =~ /\A\s*(?:#|\z)/;
        next unless $line =~ /\bzfs-auto-snapshot\b/;
        my ($joblabel) = $line =~ /--label=([a-z]+)\b/;
        next unless defined $joblabel && $joblabel eq $label;
        my ($keep) = $line =~ /--keep=(\d+)\b/;
        die "Unerwartete Aufbewahrungsregel in $file\n" unless defined($keep) && $keep >= 0 && $keep <= 9999;
        push @found, $disabled ? 0 : 0 + $keep;
    }
    die "Aufbewahrungsregel fehlt oder ist mehrdeutig: $file\n" unless @found == 1;
    return { label => $label, keep => $found[0], file => $file };
}

__PACKAGE__->register_method({
    name => 'retention',
    path => 'retention',
    method => 'GET',
    proxyto => 'node',
    protected => 1,
    permissions => {
        check => ['perm', '/nodes/{node}', ['Sys.Audit']],
    },
    description => 'Read current zfs-auto-snapshot retention from existing cron jobs (read-only).',
    parameters => {
        additionalProperties => 0,
        properties => { node => get_standard_option('pve-node') },
    },
    returns => {
        type => 'array',
        items => { type => 'object', additionalProperties => 1 },
    },
    code => sub {
        my ($param) = @_;
        my @labels = qw(frequent hourly daily weekly monthly yearly);
        my @result;
        for my $label (@labels) {
            push @result, _read_retention_file($label, $RETENTION_CRON_FILES{$label});
        }
        return \@result;
    },
});


# Mutations are deliberately isolated to a single, fixed cron file per request.
# Proxmox authenticates the caller, enforces CSRF on POST and checks Sys.Modify.
use Fcntl qw(:DEFAULT :flock O_NOFOLLOW);
use File::Temp qw(tempfile tempdir);
use File::Path qw(make_path);
use File::Basename qw(dirname);
our $RETENTION_BACKUP_DIR = '/root/pve-zfs-manager-retention-backups';
our $RETENTION_LOCK_FILE = '/run/lock/pve-zfs-manager-retention.lock';

sub _safe_cron_text {
    my ($file) = @_;
    my @st = lstat($file);
    die "Zeitplandatei nicht regulaer oder fehlt\n" unless @st && -f _ && !-l _;
    die "Zeitplandatei hat ungueltige Besitzer/Links/Groesse\n"
        unless $st[4] == 0 && $st[3] == 1 && $st[7] <= 32768;
    sysopen(my $fh, $file, O_RDONLY | O_NOFOLLOW) or die "Zeitplandatei nicht lesbar: $!\n";
    binmode($fh);
    local $/;
    my $contents = <$fh>;
    close($fh) or die "Zeitplandatei Lesefehler\n";
    die "Zeitplandatei enthaelt nicht unterstuetzte Zeichen\n"
        if !defined($contents) || $contents =~ /\x00/ || length($contents) > 32768;
    return ($contents, $st[2] & 07777, $st[4], $st[5]);
}

sub _write_private {
    my ($file, $contents) = @_;
    sysopen(my $out, $file, O_WRONLY | O_CREAT | O_EXCL | O_NOFOLLOW, 0600)
        or die "Sicherungsdatei konnte nicht angelegt werden: $!\n";
    binmode($out);
    print {$out} $contents or die "Sicherungsdatei konnte nicht geschrieben werden\n";
    close($out) or die "Sicherungsdatei Schreibfehler\n";
}

sub _update_retention {
    my ($label, $keep, $expected, $confirmation) = @_;
    die "Ungueltiger Snapshot-Typ\n" unless defined($label) && exists $RETENTION_CRON_FILES{$label};
    die "Ungueltiger Aufbewahrungswert (0..999)\n" unless defined($keep) && $keep =~ /\A\d+\z/ && $keep >= 0 && $keep <= 999;
    die "Ungueltiger Vergleichswert\n" unless defined($expected) && $expected =~ /\A\d+\z/ && $expected <= 9999;
    die "Bestaetigung fehlt\n" unless defined($confirmation) &&
        $confirmation eq "RETENTION:$label:$expected:$keep";

    sysopen(my $lock, $RETENTION_LOCK_FILE, O_RDWR | O_CREAT | O_NOFOLLOW, 0600)
        or die "ZFS-Manager Sperrdatei nicht verfuegbar: $!\n";
    flock($lock, LOCK_EX) or die "ZFS-Manager Sperre fehlgeschlagen\n";
    my $file = $RETENTION_CRON_FILES{$label};
    my ($raw, $mode, $uid, $gid) = _safe_cron_text($file);
    my $current = _read_retention_file($label, $file)->{keep};
    die "Aufbewahrung wurde zwischenzeitlich geaendert, bitte aktualisieren\n" if $current != $expected;
    return {label => $label, keep => 0 + $keep, previous_keep => $current, unchanged => 1}
        if $current == $keep;

    my @lines = $raw =~ /[^\n]*\n|[^\n]+\z/g;
    my $matches = 0;
    for my $line (@lines) {
        my $candidate = $line;
        my $disabled = ($candidate =~ s/\A# PVE-ZFS-MANAGER-DISABLED //);
        next if !$disabled && $candidate =~ /\A\s*(?:#|\z)/;
        next unless $candidate =~ /\bzfs-auto-snapshot\b/;
        my ($found) = $candidate =~ /--label=([a-z]+)\b/;
        next unless defined($found) && $found eq $label;
        $matches++;
        my @keep_args = $candidate =~ /(?<!\S)--keep=\d+(?=\s|$)/g;
        die "Zeitplan hat mehrere oder keine --keep-Argumente\n" unless @keep_args == 1;
        # When disabling, retain the previous nonzero --keep in the comment so
        # activation can restore it without losing the rest of the cron command.
        if ($keep != 0) {
            my $replaced = ($candidate =~ s/(?<!\S)--keep=\d+(?=\s|$)/--keep=$keep/);
            die "Zeitplan hat kein eindeutiges --keep-Argument\n" unless $replaced == 1;
        }
        $line = $keep == 0 ? '# PVE-ZFS-MANAGER-DISABLED ' . $candidate : $candidate;
    }
    die "Zeitplan ist mehrdeutig\n" unless $matches == 1;
    my $next = join('', @lines);
    die "Unbeabsichtigte leere Zeitplandatei\n" unless length($next) && $next ne $raw;

    if (!-d $RETENTION_BACKUP_DIR) {
        make_path($RETENTION_BACKUP_DIR, {mode => 0700});
    }
    die "Unsicheres Sicherungsverzeichnis\n" if -l $RETENTION_BACKUP_DIR || !-d $RETENTION_BACKUP_DIR;
    my @backst = stat($RETENTION_BACKUP_DIR);
    die "Sicherungsverzeichnis ist nicht root-privat\n"
        unless @backst && $backst[4] == 0 && ($backst[2] & 0777) == 0700;

    my $backupfolder = tempdir('retention-XXXXXXXX', DIR => $RETENTION_BACKUP_DIR, CLEANUP => 0);
    _write_private("$backupfolder/$label.cron", $raw);
    my $directory = dirname($file);
    die "Unsicheres Cron-Verzeichnis\n" if -l $directory || !-d $directory;
    my ($tmpfh, $temp) = tempfile('.pve-zfs-keep-XXXXXXXX', DIR => $directory, UNLINK => 0);
    my $renamed = 0;
    eval {
        binmode($tmpfh);
        print {$tmpfh} $next or die "Neue Zeitplandatei nicht schreibbar\n";
        chmod($mode, $temp) == 1 or die "Dateirechte konnten nicht gesetzt werden\n";
        chown($uid, $gid, $temp) == 1 or die "Dateibesitzer konnten nicht gesetzt werden\n";
        close($tmpfh) or die "Neue Zeitplandatei nicht geschlossen\n";
        my ($before) = _safe_cron_text($file);
        die "Zeitplan wurde parallel geaendert\n" unless $before eq $raw;
        rename($temp, $file) or die "Zeitplandatei konnte nicht atomar ersetzt werden: $!\n";
        $renamed = 1;
        my $check = _read_retention_file($label, $file)->{keep};
        die "Neue Aufbewahrung nicht verifizierbar\n" unless $check == $keep;
        1;
    } or do {
        my $error = $@ || 'Unbekannter Schreibfehler';
        unlink($temp) if !$renamed && -e $temp;
        # The original is safely backed up. No blind overwrite after rename.
        die "Aufbewahrung nicht abgeschlossen: $error; Sicherung in $backupfolder\n";
    };
    return {label => $label, keep => 0 + $keep, previous_keep => $current,
            unchanged => 0, backup => "$backupfolder/$label.cron"};
}

__PACKAGE__->register_method({
    name => 'retention_update',
    path => 'retention-update',
    method => 'POST',
    proxyto => 'node',
    protected => 1,
    permissions => {
        check => ['perm', '/nodes/{node}', ['Sys.Modify']],
    },
    description => 'Update one known zfs-auto-snapshot keep count after explicit confirmation.',
    parameters => {
        additionalProperties => 0,
        properties => {
            node => get_standard_option('pve-node'),
            label => {type => 'string', enum => ['frequent','hourly','daily','weekly','monthly','yearly']},
            keep => {type => 'integer', minimum => 0, maximum => 999},
            expected_keep => {type => 'integer', minimum => 0, maximum => 9999},
            confirm => {type => 'string', maxLength => 90},
        },
    },
    returns => {type => 'object', additionalProperties => 1},
    code => sub {
        my ($param) = @_;
        _require_zfsmgr_admin($param->{node});
        return _update_retention($param->{label}, $param->{keep},
                                 $param->{expected_keep}, $param->{confirm});
    },
});

# v0.5.0 TEST-only guest snapshot operations.
# The existing host snapshot listing and retention are unchanged.
use Digest::SHA qw(sha256_hex);
use POSIX qw(WNOHANG);

sub _run_capture {
    my (@argv) = @_;
    my ($fh, $output);
    my $ok = eval {
        local $SIG{ALRM} = sub { die "Zeitlimit bei Gastpruefung\n" };
        alarm(15);
        open($fh, '-|', @argv) or die "Prozessstart fehlgeschlagen\n";
        local $/;
        $output = <$fh>;
        $output = '' if !defined($output); # empty stdout is valid for no bookmarks or a no-op dry-run
        die "Prozessausgabe zu lang\n" if length($output) > 100_000;
        close($fh) or die "Gastpruefung fehlgeschlagen\n";
        alarm(0);
        1;
    };
    my $err = $@ if !$ok;
    alarm(0);
    if ($err) {
        close($fh) if defined($fh) && defined(fileno($fh));
        die $err;
    }
    return $output;
}

# This policy is independent of volume-name guesses: it resolves ownership
# from the Proxmox storage.cfg and current VM/LXC configuration. Unknown,
# template/locked, shared, detached or ambiguous volumes fail closed.
sub _guest_access_rows {
    my $raw = _run_capture('/usr/bin/python3', $GUEST_POLICY, 'list');
    my $rows = eval { decode_json($raw) };
    die "Gastzuordnung nicht lesbar\n" unless ref($rows) eq 'ARRAY';
    return $rows;
}
sub _validate_test_guest {
    my ($dataset, $must_stop, $rollback, $create) = @_;
    die "Ungueltiges Dataset\n" unless defined($dataset)
        && $dataset =~ /\A[A-Za-z0-9_.:~-]+(?:\/[A-Za-z0-9_.:~-]+)*\z/;
    my @args = ('/usr/bin/python3', $GUEST_POLICY,'resolve','--dataset',$dataset);
    push @args, '--stop' if $must_stop;
    push @args, '--rollback' if $rollback;
    push @args, '--create' if $create;
    my $json = _run_capture(@args);
    my $entry = eval { decode_json($json) };
    die "Keine eindeutige Proxmox-Gastzuordnung\n"
        unless ref($entry) eq 'HASH' && ($entry->{dataset}//'') eq $dataset
            && ($entry->{fingerprint}//'') =~ /\A[a-f0-9]{64}\z/;
    my $actual = _run_capture('/usr/sbin/zfs','get','-H','-o','value','type',$dataset);
    my $type = $entry->{guest} eq 'vm' ? 'volume' : 'filesystem';
    die "ZFS-Datentraegertyp stimmt nicht mit Gastzuordnung ueberein\n"
        unless $actual =~ /\A\Q$type\E\s*\z/;
    return $entry;
}

__PACKAGE__->register_method({
    name=>'guest_access', path=>'guest-access',method=>'GET',protected=>1,proxyto=>'node',
    permissions=>{check=>['perm','/nodes/{node}',['Sys.Audit']]},
    description=>'Read-only mapping of explicitly configured Proxmox guest ZFS disks.',
    parameters=>{additionalProperties=>0,properties=>{node=>get_standard_option('pve-node')}},
    returns=>{type=>'array',items=>{type=>'object',additionalProperties=>1}},
    code=>sub {my ($p)=@_; return _guest_access_rows();},
});
__PACKAGE__->register_method({
    name=>'admin_status',path=>'admin-status',method=>'GET',protected=>1,proxyto=>'node',
    permissions=>{check=>['perm','/nodes/{node}',['Sys.Audit']]},
    description=>'Read-only capability: does not grant privileges.',
    parameters=>{additionalProperties=>0,properties=>{node=>get_standard_option('pve-node')}},
    returns=>{type=>'object',additionalProperties=>1},
    code=>sub {my ($p)=@_;
        my $allowed = eval { _require_zfsmgr_admin($p->{node}); 1 } ? 1 : 0;
        return { admin => $allowed };
    },
});

sub _list_guest_snaps {
    my ($dataset) = @_;
    my $raw = _run_capture('/usr/sbin/zfs', 'list', '-H', '-p', '-t', 'snapshot',
        '-o', 'name,creation,createtxg', '-s', 'createtxg', '-d', '1', $dataset);
    my @result;
    for my $line (split /\n/, $raw) {
        next if $line eq '';
        my ($name, $created, $txg) = split /\t/, $line;
        die "Unerwarteter Snapshot-Name\n" unless defined $name && $name =~ /^\Q$dataset\E\@([A-Za-z0-9_.:-]{1,128})$/;
        my $snap = $1;
        die "Unerwartetes Snapshot-Datum\n" unless defined($created) && $created =~ /\A\d{1,20}\z/ && defined($txg) && $txg =~ /\A\d{1,20}\z/;
        push @result, { name => $snap, created => 0 + $created, txg => 0 + $txg };
        die "Zu viele Snapshots\n" if @result > 500;
    }
    return \@result;
}

sub _guest_plan {
    my ($dataset, $snapshot) = @_;
    die "Ungueltiger Snapshot-Name\n" unless defined($snapshot) && $snapshot =~ /\A[A-Za-z0-9_.:-]{1,128}\z/;
    my $guest = _validate_test_guest($dataset, 1, 0);
    my $list = _list_guest_snaps($dataset);
    my $pos;
    for my $i (0..$#$list) { if ($list->[$i]{name} eq $snapshot) { $pos = $i; last; } }
    die "Snapshot nicht gefunden\n" unless defined $pos;
    my @newer = map { $_->{name} } @{$list}[$pos+1..$#$list];
    my $signature = sha256_hex(join('\n', $dataset, $snapshot,
        map { $_->{name} . ':' . $_->{created} . ':' . $_->{txg} } @$list));
    $signature = sha256_hex(join('|', $signature, $guest->{fingerprint}));
    return { dataset => $dataset, snapshot => $snapshot,
        newer => \@newer, newer_count => scalar(@newer), token => $signature,
        guest => $guest->{guest}, vmid => $guest->{vmid}, stopped => 1 };
}

__PACKAGE__->register_method({
    name => 'guest_rollback_preview', path => 'guest-rollback-preview', method => 'GET',
    proxyto => 'node', protected => 1,
    permissions => { check => ['perm', '/nodes/{node}', ['Sys.Modify']] },
    description => 'Preview rollback of stopped uniquely mapped guest only; does not change ZFS.',
    parameters => { additionalProperties => 0, properties => {
        node => get_standard_option('pve-node'),
        dataset => {type=>'string', maxLength=>200},
        snapshot => {type=>'string', maxLength=>128},
    } },
    returns => { type=>'object', additionalProperties=>1 },
    code => sub {
        my ($param) = @_;
        _require_zfsmgr_admin($param->{node});
        return _sign_preview(_rollback_preview($param->{dataset},$param->{snapshot}), 'ROLLBACK');
    },
});

# Destructive execution is disabled by default until an explicit, short-lived
# root-only host approval exists after independently verified guest backup.

# All test writes serialised with the retention writer; fixed binary commands,
# no shell, no user-selected arbitrary path.
sub _guest_lock {
    sysopen(my $lock, '/run/lock/pve-zfs-manager-guest.lock', O_RDWR|O_CREAT|O_NOFOLLOW, 0600)
        or die "Guest-Sperre nicht verfuegbar\n";
    flock($lock, LOCK_EX) or die "Guest-Sperre fehlgeschlagen\n";
    return $lock;
}
sub _run_zfs_write {
    my (@argv) = @_;
    # Child process inherits no shell, and the endpoint hardcodes subcommands.
    my $pid = fork();
    die "Prozess kann nicht gestartet werden\n" unless defined $pid;
    if ($pid == 0) {
        exec('/usr/sbin/zfs', @argv) or POSIX::_exit(127);
    }
    my $deadline = time + 20;
    my $status;
    while (1) {
        my $w = waitpid($pid, WNOHANG);
        if ($w == $pid) { $status = $?; last; }
        die "Warteprozess fehlgeschlagen\n" if $w < 0;
        if (time > $deadline) {
            kill 'TERM', $pid;
            waitpid($pid, 0);
            die "ZFS-Aktion hat das Zeitlimit ueberschritten; Zustand bitte pruefen\n";
        }
        select undef, undef, undef, 0.1;
    }
    die "ZFS-Aktion fehlgeschlagen (exit=$status)\n" if $status != 0;
}

sub _create_test_guest_snapshot {
    my ($dataset, $confirm) = @_;
    die "Bestaetigung fehlt\n" unless defined($confirm) && $confirm eq 'CREATE-TEST-SNAPSHOT';
    my $lock = _guest_lock();
    # Online ZFS snapshot: guest may remain running. This is crash-consistent,
    # not automatically application-consistent (DB flush/quiesce not implied).
    _validate_test_guest($dataset, 0, 0, 1);
    my $snap = 'zfsmgr-' . POSIX::strftime('%Y%m%d-%H%M%S',localtime()) . '-' . $$;
    _run_zfs_write('snapshot', "$dataset\@$snap");
    return { dataset => $dataset, snapshot => $snap };
}

# Preview a destructive range operation: selected snapshot plus every newer one.
# Only the selected dataset is affected. This is NOT a rollback of data.
sub _delete_guest_plan {
    my ($dataset, $snapshot) = @_;
    my $plan = _guest_plan($dataset, $snapshot); # validates stopped guest
    my @deleted = ($snapshot, @{$plan->{newer}});
    $plan->{delete_list} = \@deleted;
    $plan->{delete_count} = scalar(@deleted);
    $plan->{delete_last} = $deleted[-1];
    $plan->{token} = sha256_hex(join('\n', 'DELETE-RANGE-v1', $plan->{token}, @deleted));
    _check_clone_dependencies($dataset, \@deleted);
    _check_snapshot_holds($dataset, \@deleted);
    my ($range, $dry_run) = _dry_run_destroy_range($dataset, $snapshot, $plan->{delete_last});
    $plan->{dry_run} = $dry_run;
    $plan->{bounded_range} = $range;
    return $plan;
}

__PACKAGE__->register_method({
    name=>'guest_snapshot_delete_preview', path=>'guest-snapshot-delete-preview', method=>'GET',
    protected=>1, proxyto=>'node',
    permissions=>{check=>['perm','/nodes/{node}',['Sys.Modify']]},
    description=>'Read-only preview of deleting selected AND ALL newer snapshots of stopped uniquely mapped guest.',
    parameters=>{additionalProperties=>0,properties=>{
        node=>get_standard_option('pve-node'),
        dataset=>{type=>'string',maxLength=>200},
        snapshot=>{type=>'string',maxLength=>128},
    }},
    returns=>{type=>'object',additionalProperties=>1},
    code=>sub {my ($p)=@_;_require_zfsmgr_admin($p->{node});return _sign_preview(_delete_guest_plan($p->{dataset},$p->{snapshot}), 'DELETE')},
});

sub _check_clone_dependencies {
    my ($dataset, $snapshots) = @_;
    for my $name (@$snapshots) {
        my $clones = _run_capture('/usr/sbin/zfs','get','-H','-o','value','clones',"$dataset\@$name");
        die "Snapshot besitzt abhaengige Klone\n" unless $clones =~ /\A-\s*\z/;
    }
}

# Per-action, user-bound 5-minute signed preview replaces the global gate.
sub _check_snapshot_holds {
    my ($dataset, $names) = @_;
    for my $name (@$names) {
        my $refs = _run_capture('/usr/sbin/zfs','get','-H','-o','value','userrefs',"$dataset\@$name");
        die "Snapshot besitzt Holds und ist gesperrt\n" unless $refs =~ /\A0\s*\z/;
    }
}
sub _assert_no_bookmarks {
    my ($dataset) = @_;
    my $b = _run_capture('/usr/sbin/zfs','list','-H','-t','bookmark','-o','name','-d','1',$dataset);
    die "ZFS-Bookmarks erkannt: Rollback nur nach gesonderter Pruefung\n" if $b =~ /\S/;
}
sub _dry_run_destroy_range {
    my ($dataset, $first, $last) = @_;
    die "Leere Loeschgrenze\n" unless defined $first && defined $last;
    my $range = "$dataset\@$first";
    $range .= "%$last" if $first ne $last;
    # ZFS -n is a native no-op preview. No snapshots are modified.
    my $result = _run_capture('/usr/sbin/zfs','destroy','-n','-v',$range);
    return ($range, $result);
}

sub _rollback_preview {
    my ($dataset, $snapshot) = @_;
    my $plan = _guest_plan($dataset, $snapshot);
    _validate_test_guest($dataset, 1, 1); # no partial multi-disk guest rollback
    _assert_no_bookmarks($dataset);
    _check_clone_dependencies($dataset, [$snapshot, @{$plan->{newer}}]);
    _check_snapshot_holds($dataset, [$snapshot, @{$plan->{newer}}]);
    if ($plan->{newer_count}) {
        my ($range, $dry_run) = _dry_run_destroy_range($dataset, $plan->{newer}[0], $plan->{newer}[-1]);
        $plan->{dry_run} = $dry_run;
        $plan->{bounded_range} = $range;
    } else {
        $plan->{dry_run} = '';
        $plan->{bounded_range} = '';
    }
    return $plan;
}

sub _delete_test_guest_snapshot {
    my ($dataset,$snapshot,$token,$confirm) = @_;
    die "Bestaetigung fehlt\n" unless defined($confirm) && $confirm eq "DELETE-RANGE:$snapshot";
    die "Vorschau-Token fehlt\n" unless defined $token && $token =~ /\A\d{10}\.[a-f0-9]{64}\z/;
    my $lock = _guest_lock();
    my $plan = _delete_guest_plan($dataset,$snapshot);
    _verify_preview($plan, 'DELETE', $token);
    _check_clone_dependencies($dataset, $plan->{delete_list});
    _check_snapshot_holds($dataset, $plan->{delete_list});
    my $last = $plan->{delete_last};
    # Explicit bounded inclusive range. NEVER use @snapshot% (open ended),
    # -r/-R (descendants/clones), or -d (deferred deletion).
    my $range = "$dataset\@$snapshot";
    $range .= "%$last" if $last ne $snapshot;
    _dry_run_destroy_range($dataset, $snapshot, $last);
    _run_zfs_write('destroy', $range);
    return { dataset=>$dataset, snapshot=>$snapshot,
             deleted_count=>$plan->{delete_count}, deleted=>$plan->{delete_list} };
}

sub _rollback_test_guest {
    my ($dataset,$snapshot,$token,$confirm) = @_;
    die "Snapshotname ungueltig\n" unless defined $snapshot && $snapshot =~ /\A[A-Za-z0-9_.:-]{1,128}\z/;
    die "Bestaetigung fehlt\n" unless defined($confirm) && $confirm eq "ROLLBACK:$snapshot";
    die "Vorschau-Token fehlt\n" unless defined $token && $token =~ /\A\d{10}\.[a-f0-9]{64}\z/;
    my $lock = _guest_lock();
    my $plan = _rollback_preview($dataset,$snapshot);
    _verify_preview($plan, 'ROLLBACK', $token);
    # A bounded removal followed by plain rollback avoids -r destroying any
    # snapshots created AFTER preview/revalidation. This is NOT atomic:
    # snapshot deletion may succeed even if the later rollback fails.
    _assert_no_bookmarks($dataset);
    _check_clone_dependencies($dataset, [$snapshot, @{$plan->{newer}}]);
    _check_snapshot_holds($dataset, [$snapshot, @{$plan->{newer}}]);
    if ($plan->{newer_count}) {
        my $first = $plan->{newer}[0];
        my $last = $plan->{newer}[-1];
        my ($range, $dryrun) = _dry_run_destroy_range($dataset, $first, $last);
        _run_zfs_write('destroy', $range);
    }
    _run_zfs_write('rollback',"$dataset\@$snapshot");
    return { dataset=>$dataset, snapshot=>$snapshot,
        removed_newer_count=>$plan->{newer_count}, rollback=>1 };
}

# Snapshot creation for independently managed ZFS datasets, including host
# roots. Deliberately separate from the guest endpoint: guest-like volume
# names must NEVER bypass guest-policy validation by using this endpoint.
# Delete and rollback remain separate and are NOT enabled for these datasets.
sub _create_standalone_dataset_snapshot {
    my ($dataset, $confirm) = @_;
    die "Ungueltiges Dataset\n" unless defined($dataset) && length($dataset) <= 200
        && $dataset =~ /\A[A-Za-z0-9_.:~-]+(?:\/[A-Za-z0-9_.:~-]+)*\z/;
    die "Explizite Dataset-Bestaetigung fehlt\n"
        unless defined($confirm) && $confirm eq 'CREATE-DATASET:' . $dataset;
    die "Gast-Datentraeger erfordern Gast-Snapshot-Schnittstelle\n"
        if $dataset =~ m{/(?:vm|subvol)-[0-9]+-disk-[0-9]+(?:-[A-Za-z0-9_.-]+)?\z};
    my $lock = _guest_lock();
    # This proves the target exists as a regular ZFS filesystem or zvol.
    # -d 0 restricts the command output to the requested dataset only.
    my $raw = _run_capture('/usr/sbin/zfs', 'list', '-H', '-d', '0',
        '-t', 'filesystem,volume', '-o', 'name,type', $dataset);
    my @rows = grep { length($_) } split /\n/, $raw;
    die "ZFS-Dataset nicht eindeutig vorhanden\n" unless @rows == 1;
    my ($actual_name,$type) = split /\t/, $rows[0], -1;
    die "Dataset-Typ oder Name nicht freigegeben\n"
        unless defined($actual_name) && $actual_name eq $dataset
        && defined($type) && ($type eq 'filesystem' || $type eq 'volume');
    my $snap = 'zfsmgr-' . POSIX::strftime('%Y%m%d-%H%M%S',localtime()) . '-' . $$;
    _run_zfs_write('snapshot', "$dataset\@$snap");
    return { dataset => $dataset, snapshot => $snap, scope => 'standalone' };
}

__PACKAGE__->register_method({
    name=>'dataset_snapshot_create', path=>'dataset-snapshot-create', method=>'POST',
    protected=>1, proxyto=>'node',
    permissions=>{check=>['perm','/nodes/{node}',['Sys.Modify']]},
    description=>'Create a ZFS snapshot of a named non-guest filesystem or volume; no delete/rollback rights.',
    parameters=>{additionalProperties=>0,properties=>{
        node=>get_standard_option('pve-node'),
        dataset=>{type=>'string',maxLength=>200},
        confirm=>{type=>'string',maxLength=>240},
    }},
    returns=>{type=>'object',additionalProperties=>1},
    code=>sub {
        my ($p)=@_;
        _require_zfsmgr_admin($p->{node});
        return _create_standalone_dataset_snapshot($p->{dataset},$p->{confirm});
    },
});

__PACKAGE__->register_method({
    name=>'guest_snapshot_create', path=>'guest-snapshot-create', method=>'POST',
    protected=>1, proxyto=>'node',
    permissions=>{check=>['perm','/nodes/{node}',['Sys.Modify']]},
    description=>'Create crash-consistent ZFS snapshot for verified Proxmox guest volume.',
    parameters=>{additionalProperties=>0,properties=>{
        node=>get_standard_option('pve-node'),
        dataset=>{type=>'string',maxLength=>200},
        confirm=>{type=>'string',maxLength=>50},
    }},
    returns=>{type=>'object',additionalProperties=>1},
    code=>sub {my ($p)=@_;_require_zfsmgr_admin($p->{node});return _create_test_guest_snapshot($p->{dataset},$p->{confirm})},
});

__PACKAGE__->register_method({
    name=>'guest_snapshot_delete', path=>'guest-snapshot-delete', method=>'POST',
    protected=>1, proxyto=>'node',
    permissions=>{check=>['perm','/nodes/{node}',['Sys.Modify']]},
    description=>'Delete selected and every newer snapshot from stopped uniquely mapped guest, with fresh preview token.',
    parameters=>{additionalProperties=>0,properties=>{
        node=>get_standard_option('pve-node'),
        dataset=>{type=>'string',maxLength=>200},
        snapshot=>{type=>'string',maxLength=>128},
        token=>{type=>'string',maxLength=>80},
        confirm=>{type=>'string',maxLength=>160},
    }},
    returns=>{type=>'object',additionalProperties=>1},
    code=>sub {my ($p)=@_;_require_zfsmgr_admin($p->{node});return _delete_test_guest_snapshot($p->{dataset},$p->{snapshot},$p->{token},$p->{confirm})},
});

__PACKAGE__->register_method({
    name=>'guest_rollback', path=>'guest-rollback', method=>'POST',
    protected=>1, proxyto=>'node',
    permissions=>{check=>['perm','/nodes/{node}',['Sys.Modify']]},
    description=>'Rollback stopped uniquely mapped guest, pruning newer snapshots after preview.',
    parameters=>{additionalProperties=>0,properties=>{
        node=>get_standard_option('pve-node'),
        dataset=>{type=>'string',maxLength=>200},
        snapshot=>{type=>'string',maxLength=>128},
        token=>{type=>'string',maxLength=>80},
        confirm=>{type=>'string',maxLength=>160},
    }},
    returns=>{type=>'object',additionalProperties=>1},
    code=>sub {my ($p)=@_;_require_zfsmgr_admin($p->{node});return _rollback_test_guest($p->{dataset},$p->{snapshot},$p->{token},$p->{confirm})},
});

# Read pool health, last scrub and read/write/checksum errors via zpool status.
__PACKAGE__->register_method({
    name=>'pool_scan',path=>'pool-scan',method=>'GET',proxyto=>'node',protected=>1,
    permissions=>{check=>['perm','/nodes/{node}',['Sys.Audit']]},
    description=>'Read ZFS pool scan/scrub status, no write operations.',
    parameters=>{additionalProperties=>0,properties=>{node=>get_standard_option('pve-node')}},
    returns=>{type=>'array',items=>{type=>'object',additionalProperties=>1}},
    code=>sub {
        my ($p)=@_;
        my $list=_run_capture('/usr/sbin/zpool','list','-H','-o','name');
        my @rows;
        for my $pool (split /\n/,$list) {
            next unless length($pool);
            die "Poolname hat ungueltiges Format\n" unless $pool =~ /\A[A-Za-z0-9_.:-]{1,128}\z/;
            die "Zu viele Pools\n" if @rows>=100;
            my $details=_run_capture('/usr/sbin/zpool','status', $pool);
            my ($state)=$details =~ /^\s*state:\s*(.+)$/m;
            my ($scan)=$details =~ /^\s*scan:\s*(.+)$/m;
            my ($errors)=$details =~ /^\s*errors:\s*(.+)$/m;
            push @rows,{name=>$pool, state=>$state//'Unbekannt',scan=>$scan//'Keine Angabe',
                errors=>$errors//'Keine Angabe'};
        }
        return \@rows;
    },
});

# Elevated, strictly read-only host/other-dataset preview. It is NOT a
# permission to destroy or roll back an active host or boot filesystem.
sub _protected_snapshot_review {
    my ($dataset, $snapshot) = @_;
    die "Ungueltiges Dataset\n" unless defined($dataset) && $dataset =~ /\A[A-Za-z0-9_.:~-]+(?:\/[A-Za-z0-9_.:~-]+)*\z/;
    die "Ungueltiger Snapshot-Name\n" unless defined($snapshot) && $snapshot =~ /\A[A-Za-z0-9_.:-]{1,128}\z/;
    my $raw = _run_capture('/usr/sbin/zfs','list','-H','-p','-t','snapshot',
        '-o','name,creation,createtxg','-s','createtxg','-d','1',$dataset);
    my @history;
    for my $line (split /\n/, $raw) {
        next unless length($line);
        my ($full,$created,$txg) = split /\t/, $line;
        die "Unerwartete Snapshotliste\n" unless defined($full);
        my ($snapname) = $full =~ /\A\Q$dataset\E\@([A-Za-z0-9_.:-]{1,128})\z/;
        die "Unerwartete Snapshotliste\n" unless defined($snapname) &&
            defined($created) && $created =~ /\A\d+\z/ &&
            defined($txg) && $txg =~ /\A\d+\z/;
        push @history,$snapname;
        die "Zu viele Snapshots fuer Vorschau\n" if @history > 1000;
    }
    my $target;
    for my $i (0..$#history) {if ($history[$i] eq $snapshot) {$target=$i;last;}}
    die "Ziel-Snapshot nicht gefunden\n" unless defined $target;
    my @newer = @history[$target+1..$#history];
    my $rootlike = $dataset =~ /(?:\A|\/)ROOT(?:\/|\z)/ || $dataset eq 'rpool';
    my $mountpoint = _run_capture('/usr/sbin/zfs','get','-H','-o','value','mountpoint',$dataset);
    my $is_boot = $mountpoint =~ /\A\/\s*\z/;
    return {
        dataset=>$dataset,snapshot=>$snapshot,newer=>\@newer,
        newer_count=>scalar(@newer),protected=>1,
        requires_offline=>($rootlike || $is_boot ? 1 : 0),
        allowed_to_execute=>0,
        reason=>'Geschuetzter Bereich: keine Live-Loeschung oder Live-Rollback. Externe Sicherung und gesondertes Recovery-Verfahren erforderlich.',
    };
}

__PACKAGE__->register_method({
    name=>'protected_snapshot_review',path=>'protected-snapshot-review',method=>'GET',
    protected=>1,proxyto=>'node',
    permissions=>{check=>['perm','/nodes/{node}',['Sys.Modify']]},
    description=>'Administrator-only read-only preview of protected dataset. No execution endpoint.',
    parameters=>{additionalProperties=>0,properties=>{
        node=>get_standard_option('pve-node'),
        dataset=>{type=>'string',maxLength=>200},
        snapshot=>{type=>'string',maxLength=>128},
    }},
    returns=>{type=>'object',additionalProperties=>1},
    code=>sub {my ($p)=@_;
        _require_zfsmgr_admin($p->{node});
        return _protected_snapshot_review($p->{dataset},$p->{snapshot});
    },
});


1;
