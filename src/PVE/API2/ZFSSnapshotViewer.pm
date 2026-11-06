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
use JSON::PP qw(decode_json encode_json);
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
        # Perl -T: explicitly untaint the fixed verb and each validated ZFS operand.
        # No shell, flags from external input, or arbitrary executable path.
        my ($verb, @operands) = @argv;
        POSIX::_exit(126) unless defined($verb) && $verb =~ /\A(snapshot|destroy|rollback)\z/;
        $verb = $1;
        my @safe;
        for my $arg (@operands) {
            POSIX::_exit(126) unless defined($arg) &&
                $arg =~ /\A([A-Za-z0-9_.:\/@%+\-]+)\z/ && length($arg) <= 400;
            push @safe, $1;
        }
        exec { '/usr/sbin/zfs' } '/usr/sbin/zfs', $verb, @safe;
        POSIX::_exit(127);
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
    # Guest snapshots deliberately have ONE approval dialog regardless of
    # range length or naming. The API still checks the signed, current plan,
    # full delete range, stopped guest and administrative permissions.
    $plan->{high_risk} = 0;
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

# Group the disks from the current Proxmox guest configuration. An unchanged
# fingerprint and a stopped guest are mandatory on every preview/revalidation.
sub _rollback_group_plan {
    my ($dataset, $snapshot) = @_;
    my $owner = _validate_test_guest($dataset, 1, 0);
    die "Andere Gastdatentraeger nicht auf ZFS\n" if $owner->{other_disks};
    my @disks = sort { $a->{dataset} cmp $b->{dataset} }
        grep { ($_->{guest}//'') eq $owner->{guest} && ($_->{vmid}//0) == $owner->{vmid} }
        @{_guest_access_rows()};
    die "Unvollstaendige Laufwerksgruppe\n" if !@disks || @disks != $owner->{disk_count};
    my @plans;
    my $total = 0;
    for my $disk (@disks) {
        die "Gastkonfiguration/Status geaendert\n" unless
            $disk->{fingerprint} eq $owner->{fingerprint} &&
            $disk->{state} eq 'stopped' && !$disk->{protected} &&
            $disk->{can_delete} && !$disk->{other_disks};
        my $current = _validate_test_guest($disk->{dataset}, 1, 0);
        die "Gastlaufwerke geaendert\n" unless $current->{fingerprint} eq $owner->{fingerprint};
        my $p = _guest_plan($disk->{dataset}, $snapshot);
        _assert_no_bookmarks($disk->{dataset});
        _check_clone_dependencies($disk->{dataset}, [$snapshot, @{$p->{newer}}]);
        _check_snapshot_holds($disk->{dataset}, [$snapshot, @{$p->{newer}}]);
        if ($p->{newer_count}) {
            my ($range, $dryrun) = _dry_run_destroy_range($disk->{dataset},$p->{newer}[0],$p->{newer}[-1]);
            $p->{bounded_range}=$range; $p->{dry_run}=$dryrun;
        } else { $p->{bounded_range}=''; $p->{dry_run}=''; }
        $total += $p->{newer_count};
        push @plans, $p;
    }
    die "Dataset nicht mehr in Gastgruppe\n" unless grep { $_->{dataset} eq $dataset } @plans;
    my $signature = sha256_hex(join('|',$owner->{fingerprint},$snapshot,
        map { $_->{dataset}.':'.$_->{token}.':'.$_->{bounded_range} } @plans));
    return { dataset=>$dataset, snapshot=>$snapshot, token=>$signature,
        guest=>$owner->{guest}, vmid=>$owner->{vmid}, stopped=>1,
        disks=>\@plans, disk_count=>scalar(@plans), newer_count=>$total,
        newer=>[map { @{$_->{newer}} } @plans],
        dry_run=>join("\n",map { $_->{dataset}."\n".$_->{dry_run} } @plans),
        high_risk=>0, non_atomic=>1 };
}
sub _rollback_preview {
    my ($dataset, $snapshot) = @_;
    return _rollback_group_plan($dataset, $snapshot);
}

sub _delete_test_guest_snapshot {
    my ($dataset,$snapshot,$token,$confirm,$critical_ack) = @_;
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
    my ($dataset,$snapshot,$token,$confirm,$critical_ack) = @_;
    die "Snapshotname ungueltig\n" unless defined $snapshot && $snapshot =~ /\A[A-Za-z0-9_.:-]{1,128}\z/;
    die "Bestaetigung fehlt\n" unless defined($confirm) && $confirm eq "ROLLBACK:$snapshot";
    my $lock = _guest_lock();
    my $plan = _rollback_preview($dataset,$snapshot);
    _verify_preview($plan, 'ROLLBACK', $token);
    # Preflight every disk BEFORE the first modification; operations are not atomic.
    # Never fall back to a partial single-disk operation on failure.
    for my $d (@{$plan->{disks}}) {
        _assert_no_bookmarks($d->{dataset});
        _check_clone_dependencies($d->{dataset}, [$snapshot,@{$d->{newer}}]);
        _check_snapshot_holds($d->{dataset}, [$snapshot,@{$d->{newer}}]);
        if ($d->{newer_count}) {
            _dry_run_destroy_range($d->{dataset},$d->{newer}[0],$d->{newer}[-1]);
        }
    }
    my @finished;
    for my $d (@{$plan->{disks}}) {
        if ($d->{newer_count}) { _run_zfs_write('destroy',$d->{bounded_range}); }
        _run_zfs_write('rollback',"$d->{dataset}\@$snapshot");
        push @finished, $d->{dataset};
    }
    return {dataset=>$dataset,snapshot=>$snapshot,rollback=>1,
        disk_count=>$plan->{disk_count},finished=>\@finished,
        removed_newer_count=>$plan->{newer_count},non_atomic=>1};
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
        critical_ack=>{type=>'integer',minimum=>0,maximum=>1,optional=>1},
    }},
    returns=>{type=>'object',additionalProperties=>1},
    code=>sub {my ($p)=@_;_require_zfsmgr_admin($p->{node});return _delete_test_guest_snapshot($p->{dataset},$p->{snapshot},$p->{token},$p->{confirm},$p->{critical_ack})},
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
        critical_ack=>{type=>'integer',minimum=>0,maximum=>1,optional=>1},
    }},
    returns=>{type=>'object',additionalProperties=>1},
    code=>sub {my ($p)=@_;_require_zfsmgr_admin($p->{node});return _rollback_test_guest($p->{dataset},$p->{snapshot},$p->{token},$p->{confirm},$p->{critical_ack})},
});


# VM/LXC grouped operations: explicitly selected disks, stable guest ownership,
# one snapshot name and a signed, refreshed destructive preview.
sub _selected_guest_disks {
    my ($selection,$must_stop,$mode) = @_;
    die "Ungueltige Laufwerksauswahl\n" unless defined($selection) && length($selection) <= 4096;
    my $names = eval { decode_json($selection) };
    die "Keine gueltige Laufwerksliste\n" unless ref($names) eq 'ARRAY' && @$names && @$names <= 32;
    my %seen;
    my @sorted=sort @$names;
    for my $ds (@sorted) {
        die "Ungueltiger/mehrfacher Datentraeger\n" unless defined($ds)
            && $ds =~ /\A[A-Za-z0-9_.:~-]+(?:\/[A-Za-z0-9_.:~-]+)*\z/
            && !$seen{$ds}++;
    }
    my @rows;
    my ($owner,$fingerprint);
    for my $ds (@sorted) {
        my $g=_validate_test_guest($ds,$must_stop,0,$mode eq 'create');
        die "Geschuetzter oder nicht freigegebener Gast\n" if $g->{protected};
        if ($mode eq 'create') {die "Erstellung nicht freigegeben\n" unless $g->{can_create};}
        else {die "Aenderung nicht freigegeben\n" unless ($mode eq 'rollback' ? $g->{can_rollback} : $g->{can_delete});}
        my $id=($g->{guest}//'').':'.($g->{vmid}//'');
        die "Datentraeger gehoeren nicht zum selben Gast\n" if defined($owner) && $owner ne $id;
        die "Gastkonfiguration waehrend Auswahl geaendert\n" if defined($fingerprint) && $fingerprint ne $g->{fingerprint};
        $owner=$id; $fingerprint=$g->{fingerprint};
        push @rows,$g;
    }
    return (\@sorted,$fingerprint,\@rows);
}
sub _group_snapshot_plan {
    my ($selection,$snapshot,$mode)=@_;
    die "Ungueltiger Snapshot-Name\n" unless defined($snapshot)
        && $snapshot =~ /\A[A-Za-z0-9_.:-]{1,128}\z/;
    my ($disks,$fingerprint)=_selected_guest_disks($selection,1,$mode eq 'GROUP-ROLLBACK' ? 'rollback' : 'modify');
    my @plans;
    for my $ds (@$disks) {
        my $p=$mode eq 'GROUP-DELETE' ? _delete_guest_plan($ds,$snapshot) : _guest_plan($ds,$snapshot);
        _assert_no_bookmarks($ds) if $mode eq 'GROUP-ROLLBACK';
        _check_clone_dependencies($ds,[$snapshot,@{$p->{newer}}]);
        _check_snapshot_holds($ds,[$snapshot,@{$p->{newer}}]);
        if ($mode eq 'GROUP-ROLLBACK' && $p->{newer_count}) {
            my ($range,$dry)=_dry_run_destroy_range($ds,$p->{newer}[0],$p->{newer}[-1]);
            $p->{bounded_range}=$range;$p->{dry_run}=$dry;
        }
        push @plans,$p;
    }
    my $signature=sha256_hex(join('|',$mode,$fingerprint,$snapshot,
        map { $_->{dataset}.':'.$_->{token}.':'.($_->{bounded_range}//'') } @plans));
    return {dataset=>$disks->[0],snapshot=>$snapshot,token=>$signature,
        disks=>\@plans,disk_count=>scalar(@plans),selected=>$disks,
        newer_count=>0+(eval { my $sum=0;$sum+=$_->{newer_count} for @plans;$sum } // 0),
        non_atomic=>1};
}
sub _group_modify {
    my ($selection,$snapshot,$mode,$token,$confirm)=@_;
    die "Bestaetigung fehlt\n" unless defined($confirm) && $confirm eq $mode.':'.$snapshot;
    my $lock=_guest_lock();
    my $plan=_group_snapshot_plan($selection,$snapshot,$mode);
    _verify_preview($plan,$mode,$token);
    # Recheck every selected disk and every destructive dependency before writing.
    for my $p (@{$plan->{disks}}) {
        _check_clone_dependencies($p->{dataset},[$snapshot,@{$p->{newer}}]);
        _check_snapshot_holds($p->{dataset},[$snapshot,@{$p->{newer}}]);
        _assert_no_bookmarks($p->{dataset}) if $mode eq 'GROUP-ROLLBACK';
    }
    my @done;
    for my $p (@{$plan->{disks}}) {
        if ($mode eq 'GROUP-DELETE') {
            _run_zfs_write('destroy',$p->{bounded_range});
        } else {
            _run_zfs_write('destroy',$p->{bounded_range}) if $p->{newer_count};
            _run_zfs_write('rollback',$p->{dataset}.'@'.$snapshot);
        }
        push @done,$p->{dataset};
    }
    return {snapshot=>$snapshot,finished=>\@done,disk_count=>scalar(@done),non_atomic=>1};
}
sub _group_create {
    my ($selection,$confirm)=@_;
    die "Bestaetigung fehlt\n" unless defined($confirm) && $confirm eq 'CREATE-GROUP';
    my $lock=_guest_lock();
    my ($disks,$fingerprint)=_selected_guest_disks($selection,0,'create');
    my $pool;
    for my $ds (@$disks) {
        my ($p) = split '/', $ds;
        die "Gemeinsamer Snapshot benoetigt denselben ZFS-Pool\n" if defined($pool) && $pool ne $p;
        $pool=$p;
    }
    my $snap='zfsmgr-'.POSIX::strftime('%Y%m%d-%H%M%S',localtime()).'-'.$$;
    # Single ZFS snapshot invocation: selected datasets share one consistency point.
    _run_zfs_write('snapshot',map { $_.'@'.$snap } @$disks);
    return {snapshot=>$snap,disk_count=>scalar(@$disks),datasets=>$disks};
}
__PACKAGE__->register_method({
    name=>'guest_group_create',path=>'guest-group-create',method=>'POST',protected=>1,proxyto=>'node',
    permissions=>{check=>['perm','/nodes/{node}',['Sys.Modify']]},
    parameters=>{additionalProperties=>0,properties=>{
        node=>get_standard_option('pve-node'),selection=>{type=>'string',maxLength=>4096},
        confirm=>{type=>'string',maxLength=>40},
    }}, returns=>{type=>'object',additionalProperties=>1},
    code=>sub {my ($p)=@_;_require_zfsmgr_admin($p->{node});return _group_create($p->{selection},$p->{confirm})},
});
for my $spec (['group_delete','guest-group-delete','GROUP-DELETE'],
              ['group_rollback','guest-group-rollback','GROUP-ROLLBACK']) {
    my ($name,$path,$mode)=@$spec;
    __PACKAGE__->register_method({
        name=>$name.'_preview',path=>$path.'-preview',method=>'GET',protected=>1,proxyto=>'node',
        permissions=>{check=>['perm','/nodes/{node}',['Sys.Modify']]},
        parameters=>{additionalProperties=>0,properties=>{
            node=>get_standard_option('pve-node'),selection=>{type=>'string',maxLength=>4096},
            snapshot=>{type=>'string',maxLength=>128},
        }},returns=>{type=>'object',additionalProperties=>1},
        code=>sub {my ($p)=@_;_require_zfsmgr_admin($p->{node});
            return _sign_preview(_group_snapshot_plan($p->{selection},$p->{snapshot},$mode),$mode);},
    });
    __PACKAGE__->register_method({
        name=>$name,path=>$path,method=>'POST',protected=>1,proxyto=>'node',
        permissions=>{check=>['perm','/nodes/{node}',['Sys.Modify']]},
        parameters=>{additionalProperties=>0,properties=>{
            node=>get_standard_option('pve-node'),selection=>{type=>'string',maxLength=>4096},
            snapshot=>{type=>'string',maxLength=>128},token=>{type=>'string',maxLength=>80},
            confirm=>{type=>'string',maxLength=>160},
        }},returns=>{type=>'object',additionalProperties=>1},
        code=>sub {my ($p)=@_;_require_zfsmgr_admin($p->{node});
            return _group_modify($p->{selection},$p->{snapshot},$mode,$p->{token},$p->{confirm});},
    });
}

# v1.0.0-22: exact snapshot deletion. No ranges, recursive flags or newer snapshots.
# Multi-disk delete is non-atomic; a failure after the first disk is reported.
sub _exact_group_delete_plan {
    my ($selection,$snapshot)=@_;
    die "Ungueltiger Snapshotname\n" unless defined($snapshot) && $snapshot =~ /\A[A-Za-z0-9_.:-]{1,128}\z/;
    my ($disks,$fingerprint)=_selected_guest_disks($selection,1,'modify');
    my @plans;
    for my $ds (@$disks) {
        my $p=_guest_plan($ds,$snapshot); # requires stopped guest and exact existing snapshot
        _check_clone_dependencies($ds,[$snapshot]);
        _check_snapshot_holds($ds,[$snapshot]);
        my $dry=_run_capture('/usr/sbin/zfs','destroy','-n','-v',"$ds\@$snapshot");
        push @plans,{dataset=>$ds,snapshot=>$snapshot,newer_count=>$p->{newer_count},
            dry_run=>$dry,identity=>$p->{token}};
    }
    my $signature=sha256_hex(join('|','EXACT-GROUP-v1',$fingerprint,$snapshot,
        map { $_->{dataset}.':'.$_->{identity} } @plans));
    return {dataset=>$disks->[0],snapshot=>$snapshot,token=>$signature,
        disks=>\@plans,disk_count=>scalar(@plans),newer_preserved=>1,non_atomic=>1};
}
sub _exact_group_delete {
    my ($selection,$snapshot,$token,$confirm)=@_;
    die "Bestaetigung fehlt\n" unless defined($confirm) && $confirm eq 'DELETE-EXACT:'.$snapshot;
    my $lock=_guest_lock();
    my $plan=_exact_group_delete_plan($selection,$snapshot);
    _verify_preview($plan,'DELETE-EXACT',$token);
    # Revalidation of full guest group and clone/hold checks precedes first write.
    for my $p (@{$plan->{disks}}) {
        _check_clone_dependencies($p->{dataset},[$snapshot]);
        _check_snapshot_holds($p->{dataset},[$snapshot]);
        _run_capture('/usr/sbin/zfs','destroy','-n','-v',$p->{dataset}.'@'.$snapshot);
    }
    my @done;
    for my $p (@{$plan->{disks}}) {
        _run_zfs_write('destroy',$p->{dataset}.'@'.$snapshot);
        push @done,$p->{dataset};
    }
    return {snapshot=>$snapshot,finished=>\@done,disk_count=>scalar(@done),
        newer_preserved=>1,non_atomic=>1};
}
__PACKAGE__->register_method({
    name=>'guest_group_delete_exact_preview',path=>'guest-group-delete-exact-preview',
    method=>'GET',protected=>1,proxyto=>'node',
    permissions=>{check=>['perm','/nodes/{node}',['Sys.Modify']]},
    parameters=>{additionalProperties=>0,properties=>{
        node=>get_standard_option('pve-node'),selection=>{type=>'string',maxLength=>4096},
        snapshot=>{type=>'string',maxLength=>128},
    }},returns=>{type=>'object',additionalProperties=>1},
    code=>sub {my ($p)=@_;_require_zfsmgr_admin($p->{node});
        return _sign_preview(_exact_group_delete_plan($p->{selection},$p->{snapshot}),'DELETE-EXACT');},
});
__PACKAGE__->register_method({
    name=>'guest_group_delete_exact',path=>'guest-group-delete-exact',
    method=>'POST',protected=>1,proxyto=>'node',
    permissions=>{check=>['perm','/nodes/{node}',['Sys.Modify']]},
    parameters=>{additionalProperties=>0,properties=>{
        node=>get_standard_option('pve-node'),selection=>{type=>'string',maxLength=>4096},
        snapshot=>{type=>'string',maxLength=>128},token=>{type=>'string',maxLength=>80},
        confirm=>{type=>'string',maxLength=>160},
    }},returns=>{type=>'object',additionalProperties=>1},
    code=>sub {my ($p)=@_;_require_zfsmgr_admin($p->{node});
        return _exact_group_delete($p->{selection},$p->{snapshot},$p->{token},$p->{confirm});},
});

# v1.0.0-23: exact host snapshot deletion, independent of range deletion.
# All host protection rules and the two confirmations remain mandatory.
sub _host_exact_plan {
    my ($dataset,$snapshot)=@_;
    die "Ungueltiger Snapshotname\n" unless defined($snapshot) && $snapshot =~ /\A[A-Za-z0-9_.:-]{1,128}\z/;
    my $info=_host_dataset_info($dataset);
    my $list=_list_guest_snaps($dataset);
    my $exists=grep { $_->{name} eq $snapshot } @$list;
    die "Snapshot nicht gefunden\n" unless $exists == 1;
    _check_clone_dependencies($dataset,[$snapshot]);
    _check_snapshot_holds($dataset,[$snapshot]);
    my $dry=_run_capture('/usr/sbin/zfs','destroy','-n','-v',"$dataset\@$snapshot");
    my $sig=sha256_hex(join('|','HOST-EXACT-v1',$dataset,$snapshot,$info->{mounted},$info->{mountpoint},
        map {$_->{name}.':'.$_->{created}.':'.$_->{txg}} @$list));
    return {dataset=>$dataset,snapshot=>$snapshot,token=>$sig,dry_run=>$dry,
        newer_preserved=>1,high_risk=>1,system_dataset=>$info->{system_dataset},
        scope=>'host',delete_count=>1};
}
sub _host_exact_delete {
    my ($dataset,$snapshot,$token,$confirm,$critical_ack)=@_;
    die "Zweite rote Warnung nicht bestaetigt\n" unless defined($critical_ack) && $critical_ack eq '1';
    die "Host-Loeschbestaetigung fehlt\n" unless defined($confirm) && $confirm eq 'HOST-DELETE-EXACT:'.$snapshot;
    my $lock=_guest_lock();
    my $plan=_host_exact_plan($dataset,$snapshot);
    _verify_preview($plan,'HOST-DELETE-EXACT',$token);
    _check_clone_dependencies($dataset,[$snapshot]);
    _check_snapshot_holds($dataset,[$snapshot]);
    _run_capture('/usr/sbin/zfs','destroy','-n','-v',"$dataset\@$snapshot");
    _run_zfs_write('destroy',"$dataset\@$snapshot");
    return {dataset=>$dataset,snapshot=>$snapshot,deleted_count=>1,newer_preserved=>1};
}
__PACKAGE__->register_method({
    name=>'host_snapshot_delete_exact_preview',path=>'host-snapshot-delete-exact-preview',
    method=>'GET',protected=>1,proxyto=>'node',
    permissions=>{check=>['perm','/nodes/{node}',['Sys.Modify']]},
    parameters=>{additionalProperties=>0,properties=>{
        node=>get_standard_option('pve-node'),dataset=>{type=>'string',maxLength=>200},snapshot=>{type=>'string',maxLength=>128},
    }},returns=>{type=>'object',additionalProperties=>1},
    code=>sub {my ($p)=@_;_require_zfsmgr_admin($p->{node});
        return _sign_preview(_host_exact_plan($p->{dataset},$p->{snapshot}),'HOST-DELETE-EXACT');},
});
__PACKAGE__->register_method({
    name=>'host_snapshot_delete_exact',path=>'host-snapshot-delete-exact',
    method=>'POST',protected=>1,proxyto=>'node',
    permissions=>{check=>['perm','/nodes/{node}',['Sys.Modify']]},
    parameters=>{additionalProperties=>0,properties=>{
        node=>get_standard_option('pve-node'),dataset=>{type=>'string',maxLength=>200},snapshot=>{type=>'string',maxLength=>128},
        token=>{type=>'string',maxLength=>80},confirm=>{type=>'string',maxLength=>160},
        critical_ack=>{type=>'integer',minimum=>0,maximum=>1},
    }},returns=>{type=>'object',additionalProperties=>1},
    code=>sub {my ($p)=@_;_require_zfsmgr_admin($p->{node});
        return _host_exact_delete($p->{dataset},$p->{snapshot},$p->{token},$p->{confirm},$p->{critical_ack});},
});


# v1.0.0-26: exact batch snapshot deletion. Never ranges, never newer snapshots.
# A complete, signed preflight is mandatory; per-disk ZFS writes are not atomic.
sub _batch_names {
    my ($json)=@_;
    my $names=eval {decode_json($json)};
    die "Ungueltige Snapshot-Auswahl\n" unless ref($names) eq 'ARRAY' && @$names && @$names <= 32;
    my %seen;
    for my $name (@$names) {
        die "Ungueltiger oder doppelter Snapshot\n" unless defined($name)
            && $name =~ /\A[A-Za-z0-9_.:-]{1,128}\z/ && !$seen{$name}++;
    }
    return [sort @$names];
}
sub _batch_plan {
    my ($scope,$selection,$dataset,$names_json,$allow_partial)=@_;
    my $names=_batch_names($names_json);
    my @targets;
    my $first;
    my $disks;
    my $missing_targets=[];
    if($scope eq 'guest') {
        ($disks)=_selected_guest_disks($selection,1,'modify');
        # v1.0.0-26: explicit matrix, including missing targets. Nothing is
        # silently skipped. Only actual snapshots may enter the signed plan.
        my @missing;
        my @matrix;
        for my $ds (@$disks) {
            my $existing=_list_guest_snaps($ds);
            my %available=map { $_->{name} => $_ } @$existing;
            for my $snap (@$names) {
                if (!$available{$snap}) {
                    push @missing, "$ds\@$snap";
                    next;
                }
                my $p=_guest_plan($ds,$snap);
                _check_clone_dependencies($ds,[$snap]);
                _check_snapshot_holds($ds,[$snap]);
                my $dry=_run_capture('/usr/sbin/zfs','destroy','-n','-v',"$ds\@$snap");
                push @targets,{dataset=>$ds,snapshot=>$snap,identity=>$p->{token},dry_run=>$dry};
            }
        }
        die "Keiner der ausgewaehlten Snapshots ist vorhanden\n" unless @targets;
        if (@missing && !$allow_partial) {
            die "Unvollstaendige Snapshot-Gruppe: ".join(', ',@missing)."\n";
        }
        $missing_targets=\@missing;
        $first=$disks->[0];
    } elsif($scope eq 'host') {
        for my $snap (@$names) {
            my $p=_host_exact_plan($dataset,$snap);
            push @targets,{dataset=>$dataset,snapshot=>$snap,identity=>$p->{token},dry_run=>$p->{dry_run}};
        }
        $first=$dataset;
    } else {die "Ungueltiger Bereich\n";}
    my @list=map {$_->{dataset}.'@'.$_->{snapshot}} @targets;
    my $identity=sha256_hex(join('|','BATCH-EXACT-26',$scope,($allow_partial ? 1:0),@list,@$missing_targets,map {$_->{identity}} @targets));
    return {dataset=>$first,snapshot=>join(',',@$names),snapshots=>$names,
        targets=>\@targets,delete_count=>scalar(@targets),scope=>$scope,
        missing_targets=>$missing_targets,partial_group=>(scalar(@$missing_targets) ? 1 : 0),
        token=>$identity,non_atomic=>1,newer_preserved=>1,
        used_bytes_are_not_reclaim_estimate=>1};
}
sub _batch_delete {
    my ($scope,$selection,$dataset,$names,$token,$confirm,$critical_ack,$allow_partial)=@_;
    die "Bestaetigung fehlt\n" unless defined($confirm) && $confirm eq 'DELETE-BATCH-EXACT';
    my $lock=_guest_lock();
    my $plan=_batch_plan($scope,$selection,$dataset,$names,$allow_partial);
    die "Zweite Bestaetigung fehlt\n" if ($scope eq 'host' || $plan->{partial_group}) && (!defined($critical_ack) || $critical_ack ne '1');
    _verify_preview($plan,'DELETE-BATCH-EXACT',$token);
    # Validate every target before touching any. A failure stops future writes;
    # already completed writes cannot be rolled back automatically.
    for my $t (@{$plan->{targets}}) {
        _check_clone_dependencies($t->{dataset},[$t->{snapshot}]);
        _check_snapshot_holds($t->{dataset},[$t->{snapshot}]);
        _run_capture('/usr/sbin/zfs','destroy','-n','-v',$t->{dataset}.'@'.$t->{snapshot});
    }
    my @done;
    for my $t (@{$plan->{targets}}) {
        my $target=$t->{dataset}.'@'.$t->{snapshot};
        eval {_run_zfs_write('destroy',$target);1} or do {
            my $err=$@;
            die "Teilweise Loeschung: ".join(',',@done)."; Fehler bei $target: $err";
        };
        push @done,$target;
    }
    return {deleted=>\@done,deleted_count=>scalar(@done),non_atomic=>1,newer_preserved=>1};
}
for my $scope (qw(guest host)) {
    my $prefix=$scope eq 'guest' ? 'guest' : 'host';
    __PACKAGE__->register_method({
        name=>$prefix.'_snapshot_batch_exact_preview',path=>$prefix.'-snapshot-batch-exact-preview',
        method=>'GET',protected=>1,proxyto=>'node',
        permissions=>{check=>['perm','/nodes/{node}',['Sys.Modify']]},
        parameters=>{additionalProperties=>0,properties=>{
            node=>get_standard_option('pve-node'),
            selection=>{type=>'string',optional=>1,maxLength=>4096},
            dataset=>{type=>'string',optional=>1,maxLength=>200},
            snapshots=>{type=>'string',maxLength=>5000},
            allow_partial=>{type=>'integer',optional=>1,minimum=>0,maximum=>1},
        }},returns=>{type=>'object',additionalProperties=>1},
        code=>sub {my($x)=@_;_require_zfsmgr_admin($x->{node});
            return _sign_preview(_batch_plan($scope,$x->{selection},$x->{dataset},$x->{snapshots},$x->{allow_partial}),'DELETE-BATCH-EXACT');},
    });
    __PACKAGE__->register_method({
        name=>$prefix.'_snapshot_batch_exact',path=>$prefix.'-snapshot-batch-exact',
        method=>'POST',protected=>1,proxyto=>'node',
        permissions=>{check=>['perm','/nodes/{node}',['Sys.Modify']]},
        parameters=>{additionalProperties=>0,properties=>{
            node=>get_standard_option('pve-node'),
            selection=>{type=>'string',optional=>1,maxLength=>4096},
            dataset=>{type=>'string',optional=>1,maxLength=>200},
            snapshots=>{type=>'string',maxLength=>5000},
            allow_partial=>{type=>'integer',optional=>1,minimum=>0,maximum=>1},
            token=>{type=>'string',maxLength=>80},confirm=>{type=>'string',maxLength=>80},
            critical_ack=>{type=>'integer',optional=>1,minimum=>0,maximum=>1},
        }},returns=>{type=>'object',additionalProperties=>1},
        code=>sub {my($x)=@_;_require_zfsmgr_admin($x->{node});
            return _batch_delete($scope,$x->{selection},$x->{dataset},$x->{snapshots},
                $x->{token},$x->{confirm},$x->{critical_ack},$x->{allow_partial});},
    });
}

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
            # API returns stable, locale-neutral English fallback tokens. The Proxmox
            # browser translates status values using its active GUI language.
            push @rows,{name=>$pool, state=>$state//'Unknown',scan=>$scan//'Not available',
                errors=>$errors//'Not available'};
        }
        return \@rows;
    },
});


# RC9: Separate host snapshot mutations. Guest ownership never uses this route.
# The outer ZFS pool root, boot datasets and other host filesystems may have
# snapshots deleted ONLINE after double acknowledgement, but their live DATA
# must never be rolled back while mounted or used as the operating system.
sub _host_dataset_info {
    my ($dataset) = @_;
    die "Ungueltiger Host-Datasetname\n" unless defined($dataset) && length($dataset) <= 200
        && $dataset =~ /\A[A-Za-z0-9_.:~-]+(?:\/[A-Za-z0-9_.:~-]+)*\z/;
    die "Gastartige Datasetnamen muessen die Gast-Schnittstelle verwenden\n"
        if $dataset =~ m{/(?:vm|subvol)-[0-9]+-disk-[0-9]+(?:-[A-Za-z0-9_.-]+)?\z};
    # Fail closed even for volumes whose name does not match the usual pattern.
    for my $guest (@{_guest_access_rows()}) {
        die "Zugeordnetes Gast-Dataset muss die Gast-Schnittstelle verwenden\n"
            if ref($guest) eq 'HASH' && defined($guest->{dataset}) && $guest->{dataset} eq $dataset;
    }
    my $raw = _run_capture('/usr/sbin/zfs','list','-H','-d','0',
        '-t','filesystem,volume','-o','name,type,mounted,mountpoint',$dataset);
    my @lines=grep {length($_)} split /\n/,$raw;
    die "Host-Dataset nicht eindeutig gefunden\n" unless @lines == 1;
    my ($name,$type,$mounted,$point)=split /\t/,$lines[0],-1;
    die "Dataset-Typ ist nicht freigegeben\n" unless defined($name) && $name eq $dataset
        && defined($type) && $type eq 'filesystem'
        && defined($mounted) && $mounted =~ /\A(?:yes|no|-)\z/
        && defined($point);
    # Host ZVOLs require an independent Proxmox volume ownership scan.
    # Do not guess that an unrecognized VM volume is safe.
    my $pool=(split m{/},$dataset,2)[0];
    my $boot = ($dataset eq $pool || $dataset =~ m{(?:\A|/)ROOT(?:/|\z)}
        || $point eq '/' || $dataset =~ m{(?:\A|/)(?:boot|efi)(?:/|\z)});
    return { type=>$type, mounted=>$mounted, mountpoint=>$point,
             system_dataset=>$boot ? 1 : 0 };
}
sub _host_plan {
    my ($dataset,$snapshot,$mode) = @_;
    die "Ungueltiger Snapshotname\n" unless defined($snapshot)
        && $snapshot =~ /\A[A-Za-z0-9_.:-]{1,128}\z/;
    die "Ungueltige Aktion\n" unless $mode eq 'HOST-DELETE' || $mode eq 'HOST-ROLLBACK';
    my $info = _host_dataset_info($dataset);
    my $list = _list_guest_snaps($dataset);
    my $pos;
    for my $i (0..$#$list) {
        if ($list->[$i]{name} eq $snapshot) {$pos=$i;last;}
    }
    die "Snapshot nicht gefunden\n" unless defined($pos);
    my @newer=map {$_->{name}} @{$list}[$pos+1..$#$list];
    my @delete= $mode eq 'HOST-DELETE' ? ($snapshot,@newer) : @newer;
    _check_clone_dependencies($dataset,\@delete);
    _check_snapshot_holds($dataset,\@delete);
    # A rollback of the chosen snapshot cannot proceed with clones/bookmarks.
    if ($mode eq 'HOST-ROLLBACK') {
        _assert_no_bookmarks($dataset);
        _check_clone_dependencies($dataset,[$snapshot]);
        _check_snapshot_holds($dataset,[$snapshot]);
    }
    my $dry='';my $range='';
    if (@delete) {
        ($range,$dry) = _dry_run_destroy_range($dataset,$delete[0],$delete[-1]);
    }
    my $signature = sha256_hex(join('|','HOST-V1',$mode,$dataset,$snapshot,
        $info->{mounted},$info->{mountpoint},
        map {$_->{name}.':'.$_->{created}.':'.$_->{txg}} @$list));
    my $offline=($info->{system_dataset} || $info->{mounted} eq 'yes') ? 1 : 0;
    return {dataset=>$dataset,snapshot=>$snapshot,newer=>\@newer,
        newer_count=>scalar(@newer),delete_list=>\@delete,delete_count=>scalar(@delete),
        delete_last=>(@delete ? $delete[-1] : ''),bounded_range=>$range,dry_run=>$dry,
        token=>$signature,high_risk=>1,scope=>'host',
        system_dataset=>$info->{system_dataset},requires_offline=>($mode eq 'HOST-ROLLBACK' ? $offline : 0),
        allowed_to_execute=>($mode eq 'HOST-ROLLBACK' ? (!$offline ? 1 : 0) : 1),
        reason=>($mode eq 'HOST-ROLLBACK' && $offline
            ? 'Offline-Rollback erforderlich: laufender Host oder gemountetes Dateisystem. Kein Live-Rollback.' : ''),
    };
}
sub _host_delete {
    my ($dataset,$snapshot,$token,$confirm,$critical_ack) = @_;
    die "Zweite rote Warnung nicht bestaetigt\n" unless defined($critical_ack) && $critical_ack eq '1';
    die "Host-Loeschbestaetigung fehlt\n" unless defined($confirm) && $confirm eq "HOST-DELETE:$snapshot";
    my $lock=_guest_lock();
    my $plan=_host_plan($dataset,$snapshot,'HOST-DELETE');
    _verify_preview($plan,'HOST-DELETE',$token);
    _check_clone_dependencies($dataset,$plan->{delete_list});
    _check_snapshot_holds($dataset,$plan->{delete_list});
    _dry_run_destroy_range($dataset,$snapshot,$plan->{delete_last});
    _run_zfs_write('destroy',$plan->{bounded_range});
    return {dataset=>$dataset,snapshot=>$snapshot,deleted_count=>$plan->{delete_count}};
}
sub _host_rollback {
    my ($dataset,$snapshot,$token,$confirm,$critical_ack) = @_;
    die "Zweite rote Warnung nicht bestaetigt\n" unless defined($critical_ack) && $critical_ack eq '1';
    die "Host-Rollback-Bestaetigung fehlt\n" unless defined($confirm) && $confirm eq "HOST-ROLLBACK:$snapshot";
    my $lock=_guest_lock();
    my $plan=_host_plan($dataset,$snapshot,'HOST-ROLLBACK');
    _verify_preview($plan,'HOST-ROLLBACK',$token);
    die "ROLLBACK NUR OFFLINE: Dataset ist gemountet oder gehoert zum Host-Bootpfad. Rescue-System erforderlich.\n"
        unless $plan->{allowed_to_execute};
    if ($plan->{newer_count}) {
        _dry_run_destroy_range($dataset,$plan->{newer}[0],$plan->{newer}[-1]);
        _run_zfs_write('destroy',$plan->{bounded_range});
    }
    _run_zfs_write('rollback',"$dataset\@$snapshot");
    return {dataset=>$dataset,snapshot=>$snapshot,rollback=>1,removed_newer_count=>$plan->{newer_count}};
}

# Queue a ROOT/OFFLINE rollback request after both explicit GUI confirmations.
# Queuing itself never executes a ZFS write; a separate rescue environment is
# mandatory. The rescue CLI checks the HMAC, expiry and exact live snapshot list.
our $OFFLINE_DIR='/var/lib/pve-zfs-manager/offline-rollback';
sub _host_rollback_stage {
    my ($dataset,$snapshot,$token,$confirm,$critical_ack) = @_;
    die "Zweite rote Warnung nicht bestaetigt\n"
        unless defined($critical_ack) && $critical_ack eq '1';
    die "Host-Rollback-Bestaetigung fehlt\n"
        unless defined($confirm) && $confirm eq "HOST-ROLLBACK:$snapshot";
    my $lock=_guest_lock();
    my $plan=_host_plan($dataset,$snapshot,'HOST-ROLLBACK');
    _verify_preview($plan,'HOST-ROLLBACK',$token);
    die "Nur offline erforderliche Datasets duerfen als Rescue-Auftrag vorgemerkt werden\n"
        unless $plan->{requires_offline};
    my $info=_host_dataset_info($dataset);
    my $expires=time+86400;
    my $mac=hmac_sha256_hex(join('|','ZFSMGR-OFFLINE-1',$dataset,$snapshot,
        $plan->{token},$expires),_preview_secret());
    if (!-e $OFFLINE_DIR) {make_path($OFFLINE_DIR,{mode=>0700});}
    my @st=lstat($OFFLINE_DIR);
    die "Unsicherer Offline-Rollback-Ordner\n" unless @st && -d _ && !-l $OFFLINE_DIR
        && $st[4]==0 && ($st[2]&0777)==0700;
    my @existing=glob("$OFFLINE_DIR/plan-*.json");
    die "Es liegt bereits ein Offline-Rollback-Auftrag vor; erst manuell pruefen/archivieren\n"
        if @existing;
    my $filename="$OFFLINE_DIR/plan-".time."-$$.json";
    my $content=encode_json({version=>1,dataset=>$dataset,snapshot=>$snapshot,
        fingerprint=>$plan->{token},expires=>$expires,signature=>$mac,
        mountpoint=>$info->{mountpoint},mounted_at_preview=>$info->{mounted},
        newer=>$plan->{newer},created_at=>time});
    _write_private($filename,$content."\n");
    return {dataset=>$dataset,snapshot=>$snapshot,staged=>1,
        pending_file=>$filename,offline_required=>1,
        message=>'Offline-Auftrag sicher hinterlegt. Keine Daten veraendert. ZFS-Rescue-System erforderlich.'};
}
__PACKAGE__->register_method({
    name=>'host_rollback_stage',path=>'host-rollback-stage',method=>'POST',
    protected=>1,proxyto=>'node',
    permissions=>{check=>['perm','/nodes/{node}',['Sys.Modify']]},
    description=>'Prepare a signed 24h offline rescue rollback; no live ZFS writes.',
    parameters=>{additionalProperties=>0,properties=>{
        node=>get_standard_option('pve-node'),dataset=>{type=>'string',maxLength=>200},
        snapshot=>{type=>'string',maxLength=>128},token=>{type=>'string',maxLength=>80},
        confirm=>{type=>'string',maxLength=>160},
        critical_ack=>{type=>'integer',minimum=>0,maximum=>1},
    }},
    returns=>{type=>'object',additionalProperties=>1},
    code=>sub {my ($p)=@_;_require_zfsmgr_admin($p->{node});
        return _host_rollback_stage($p->{dataset},$p->{snapshot},$p->{token},
            $p->{confirm},$p->{critical_ack});},
});

for my $task (
    ['host_snapshot_delete_preview','host-snapshot-delete-preview','GET','HOST-DELETE'],
    ['host_rollback_preview','host-rollback-preview','GET','HOST-ROLLBACK'],
) {
    my ($name,$path,$method,$mode)=@$task;
    __PACKAGE__->register_method({
        name=>$name,path=>$path,method=>$method,protected=>1,proxyto=>'node',
        permissions=>{check=>['perm','/nodes/{node}',['Sys.Modify']]},
        description=>'Signed administrator-only host snapshot preview with explicit critical risk.',
        parameters=>{additionalProperties=>0,properties=>{
            node=>get_standard_option('pve-node'),dataset=>{type=>'string',maxLength=>200},
            snapshot=>{type=>'string',maxLength=>128},
        }},
        returns=>{type=>'object',additionalProperties=>1},
        code=>sub {my ($p)=@_;_require_zfsmgr_admin($p->{node});
            return _sign_preview(_host_plan($p->{dataset},$p->{snapshot},$mode),$mode);},
    });
}
for my $task (
    ['host_snapshot_delete','host-snapshot-delete','HOST-DELETE'],
    ['host_rollback','host-rollback','HOST-ROLLBACK'],
) {
    my ($name,$path,$mode)=@$task;
    __PACKAGE__->register_method({
        name=>$name,path=>$path,method=>'POST',protected=>1,proxyto=>'node',
        permissions=>{check=>['perm','/nodes/{node}',['Sys.Modify']]},
        description=>'Elevated host operation; signed preview and second acknowledgement required.',
        parameters=>{additionalProperties=>0,properties=>{
            node=>get_standard_option('pve-node'),dataset=>{type=>'string',maxLength=>200},
            snapshot=>{type=>'string',maxLength=>128},token=>{type=>'string',maxLength=>80},
            confirm=>{type=>'string',maxLength=>160},
            critical_ack=>{type=>'integer',minimum=>0,maximum=>1},
        }},
        returns=>{type=>'object',additionalProperties=>1},
        code=>sub {my ($p)=@_;_require_zfsmgr_admin($p->{node});
            return $mode eq 'HOST-DELETE'
                ? _host_delete($p->{dataset},$p->{snapshot},$p->{token},$p->{confirm},$p->{critical_ack})
                : _host_rollback($p->{dataset},$p->{snapshot},$p->{token},$p->{confirm},$p->{critical_ack});},
    });
}

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
