from pathlib import Path
p=Path(__file__).parent
api=p/'src/PVE/API2/ZFSSnapshotViewer.pm';s=api.read_text()
anchor='# Retention configuration is read from the existing distro cron entries.'
assert s.count(anchor)==1
addition='''# Read-only inventory: detects but NEVER manages external replication jobs.
# Credentials or ExecStart command arguments must not be exposed to the API.
__PACKAGE__->register_method({
    name => 'host_inventory', path => 'host-inventory', method => 'GET',
    proxyto => 'node', protected => 1,
    permissions => { check => ['perm','/nodes/{node}',['Sys.Audit']] },
    description => 'Read-only host discovery of AutoSnap, monitoring and replication presence.',
    parameters => { additionalProperties => 0,
                    properties => { node => get_standard_option('pve-node') } },
    returns => { type => 'object', additionalProperties => 1 },
    code => sub {
        my ($param) = @_;
        my $raw = _run_capture('/usr/bin/python3',
                               '/usr/lib/pve-zfs-manager/zfsm_host_audit.py','--json');
        my $data = eval { decode_json($raw) };
        die "Hostinventur lieferte ungueltige Daten\\n"
            unless ref($data) eq 'HASH' && ($data->{schema}//0)==1
                   && ref($data->{autosnap}) eq 'HASH';
        return $data;
    },
});

'''
s=s.replace(anchor,addition+anchor);api.write_text(s)
gui=p/'src/manager_patch.py';s=gui.read_text()
anchor="            'Not available': 'Keine Angabe',"
assert s.count(anchor)==1
s=s.replace(anchor,anchor+"\n            'Existing services (read-only discovery)': 'Vorhandene Dienste (nur Erkennung)',\n            'AutoSnap schedules': 'AutoSnap-Zeitpläne',\n            'Ready': 'Bereit',\n            'Needs review': 'Prüfen',\n            'External replication recognized – managed separately': 'Externe Replikation erkannt – separat verwaltet',\n            'No additional cleanup timer created': 'Kein zusätzlicher Bereinigungstimer angelegt',")
anchor="                    { xtype: 'component', itemId: 'zfs-ro-retention-status',\n                      html: zfsL(\"Loading retention rules ...\") },"
assert s.count(anchor)==1
s=s.replace(anchor,anchor+"\n                    { xtype: 'component', html: '<h3>' + zfsL('Existing services (read-only discovery)') + '</h3>' },\n                    { xtype: 'component', itemId: 'zfsm-host-inventory', html:'—' },")
anchor="                        view.zfsRefreshReadOnly = function () {"
assert s.count(anchor)==1
s=s.replace(anchor,"""                        view.zfsmRenderHostInventory=function(){
                            var widget=view.down('#zfsm-host-inventory');
                            if(!widget || widget.destroyed)return;
                            var info=state.hostInventory;
                            if(!info || !info.autosnap || !info.replication){widget.update('—');return;}
                            var a=info.autosnap,r=info.replication,c=info.monitoring||{};
                            var label=a.ready?zfsL('Ready'):zfsL('Needs review');
                            var html='<div style="padding:8px;border:1px solid rgba(128,128,128,.4);border-radius:4px">'+
                                '<b>AutoSnap:</b> '+safe(label)+' · '+Number(a.schedule_count||0)+' '+safe(zfsL('AutoSnap schedules'))+
                                ' · <b>CheckZFS:</b> '+safe(String(c.checkzfs_package||'absent'))+'<br>'+
                                safe(zfsL('External replication recognized – managed separately'))+': '+
                                Number((r.systemd_units||[]).length)+' systemd, '+Number(r.native_pve_jobs||0)+' PVE<br>'+
                                safe(zfsL('No additional cleanup timer created'));
                            var notes=info.warnings||[];
                            if(notes.length){html+='<br><b>'+safe(zfsL('Needs review'))+':</b> '+
                                Ext.Array.map(notes.slice(0,4),safe).join('; ');}
                            widget.update(html+'</div>');
                        };
"""+anchor)
anchor="                                ['zfsmanager-ro/retention', 'retention'],"
assert s.count(anchor)==1
s=s.replace(anchor,anchor+"\n                                ['zfsmanager-ro/host-inventory', 'hostInventory'],")
anchor="                                        if(key==='emergencyStatus') {"
assert s.count(anchor)==1
s=s.replace(anchor,"""                                        if(key==='hostInventory') {
                                            if(!data || !data.autosnap || !data.replication){error('Invalid host inventory');return;}
                                            state.hostInventory=data;
                                            view.zfsmRenderHostInventory();finish();return;
                                        }
"""+anchor)
anchor="                                    if(key==='emergencyStatus'){"
assert s.count(anchor)==1
s=s.replace(anchor,"""                                    if(key==='hostInventory'){
                                        var audit=view.down('#zfsm-host-inventory');
                                        if(audit && !audit.destroyed) audit.update(safe(zfsL('Needs review'))+': '+safe(message));
                                    }
"""+anchor)
gui.write_text(s)
print('GUI/API host audit read-only panel added')
