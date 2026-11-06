#!/usr/bin/env python3
"""Snapshot-enabled read-only GUI, upgrades installed 0.4.0b.

Requires the working v0.4.0a navigation test to be present. No PVE API,
Proxmox proxy configuration, service, pool or guest is changed.
"""
from pathlib import Path
import argparse
import datetime
import hashlib
import os
import shutil
import subprocess
import sys

import patch_nav as nav

TARGET = nav.PVE_JS
BACKUP_ROOT = Path('/root/pve-zfs-manager-readonly-backups')
START = '        // BEGIN PVE-ZFS-MANAGER-READONLY-v0.4.0c\n'
END = '        // END PVE-ZFS-MANAGER-READONLY-v0.4.0c\n'

BLOCK = START + r'''        // Read-only local-node card. No global function overrides.
        // Uses only built-in authenticated Proxmox GET API endpoints.
        if (caps.nodes['Sys.Audit']) {
            me.items.push({
                xtype: 'panel',
                title: 'ZFS Manager (Lesen)',
                iconCls: 'fa fa-database',
                itemId: 'zfsmanager-readonly',
                bodyPadding: 16,
                scrollable: true,
                layout: { type: 'vbox', align: 'stretch' },
                defaults: { margin: '0 0 12 0' },
                tbar: [
                    {
                        text: 'Aktualisieren',
                        iconCls: 'fa fa-refresh',
                        handler: function (btn) {
                            var view = btn.up('panel');
                            if (view && view.zfsRefreshReadOnly) {
                                view.zfsRefreshReadOnly();
                            }
                        },
                    },
                ],
                items: [
                    {
                        xtype: 'component',
                        html: '<h2>ZFS Manager – Nur Anzeige</h2>' +
                            '<p>Lokaler Knoten: Live-Abfrage über die Proxmox-API auf Port 8006.</p>',
                    },
                    {
                        xtype: 'component',
                        html: '<h3>Festplatten</h3>' +
                            '<p>PVE-Status ist nicht gleichbedeutend mit einer vollständigen SMART-Diagnose.</p>',
                    },
                    {
                        xtype: 'grid',
                        itemId: 'zfs-ro-disks',
                        height: 200,
                        store: Ext.create('Ext.data.Store', {
                            fields: ['devpath', 'model', 'size', 'health', 'wearout', 'type', 'used'],
                            data: [],
                        }),
                        columns: [
                            { text: 'Gerät', dataIndex: 'devpath', flex: 1, renderer: safeZFSValue },
                            { text: 'Modell', dataIndex: 'model', flex: 2, renderer: safeZFSValue },
                            { text: 'Größe', dataIndex: 'size', width: 110, renderer: zfsBytes },
                            { text: 'PVE-Status', dataIndex: 'health', width: 120, renderer: safeZFSValue },
                            {
                                text: 'SMART / Verschleiß', dataIndex: 'wearout', width: 160,
                                renderer: function (v, meta, rec) {
                                    var model = String(rec.get('model') || '');
                                    if (/QEMU|VMware|VBOX|Virtual/i.test(model)) {
                                        return 'Virtuelle Disk – kein SMART';
                                    }
                                    if (v === null || v === undefined || String(v) === 'N/A') {
                                        return 'Nicht verfügbar';
                                    }
                                    return safeZFSValue(v);
                                },
                            },
                        ],
                    },
                    { xtype: 'component', itemId: 'zfs-ro-disks-status', html: 'Festplatten werden geladen …' },
                    { xtype: 'component', html: '<h3>ZFS-Pools</h3>' },
                    {
                        xtype: 'grid',
                        itemId: 'zfs-ro-pools',
                        height: 190,
                        store: Ext.create('Ext.data.Store', {
                            fields: ['name', 'health', 'size', 'alloc', 'free', 'frag'],
                            data: [],
                        }),
                        columns: [
                            { text: 'Pool', dataIndex: 'name', flex: 1, renderer: safeZFSValue },
                            { text: 'Status', dataIndex: 'health', width: 135, renderer: safeZFSValue },
                            { text: 'Gesamt', dataIndex: 'size', width: 115, renderer: zfsBytes },
                            { text: 'Belegt', dataIndex: 'alloc', width: 115, renderer: zfsBytes },
                            { text: 'Frei', dataIndex: 'free', width: 115, renderer: zfsBytes },
                            { text: 'Fragmentierung', dataIndex: 'frag', width: 120,
                              renderer: function (v) {
                                  return (v === null || v === undefined) ? '—' : safeZFSValue(v) + '%';
                              } },
                        ],
                    },
                    { xtype: 'component', itemId: 'zfs-ro-pools-status', html: 'Pools werden geladen …' },
                    { xtype: 'component', html: '<h3>ZFS-Snapshots</h3>' +
                        '<p>Nur Anzeige. Erstellen, Löschen, Rollback und Aufbewahrung bleiben gesperrt.</p>' },
                    {
                        xtype: 'textfield',
                        itemId: 'zfs-ro-snapshot-filter',
                        fieldLabel: 'Dataset / Snapshot filtern',
                        labelWidth: 190,
                        emptyText: 'z. B. rpool/data oder hourly',
                        listeners: {
                            change: function (field, value) {
                                var grid = field.up('panel').down('#zfs-ro-snapshots');
                                if (!grid) { return; }
                                var store = grid.getStore();
                                store.clearFilter();
                                var term = String(value || '').toLowerCase().trim();
                                if (term) {
                                    store.filterBy(function (rec) {
                                        return String(rec.get('name') || '').toLowerCase().indexOf(term) >= 0;
                                    });
                                }
                            },
                        },
                    },
                    {
                        xtype: 'grid',
                        itemId: 'zfs-ro-snapshots',
                        height: 330,
                        store: Ext.create('Ext.data.Store', {
                            fields: ['name', 'dataset', 'snapshot', 'creation', 'used', 'referenced'],
                            data: [],
                        }),
                        columns: [
                            { text: 'Dataset', dataIndex: 'dataset', flex: 1, renderer: safeZFSValue },
                            { text: 'Snapshot', dataIndex: 'snapshot', flex: 2, renderer: safeZFSValue },
                            {
                                text: 'Erstellt', dataIndex: 'creation', width: 180,
                                renderer: function (v) {
                                    var n = Number(v);
                                    return isFinite(n) && n > 0
                                        ? Ext.String.htmlEncode(new Date(n * 1000).toLocaleString('de-DE')) : '—';
                                },
                            },
                            { text: 'Verwendet', dataIndex: 'used', width: 115, renderer: zfsBytes },
                            { text: 'Referenziert', dataIndex: 'referenced', width: 120, renderer: zfsBytes },
                        ],
                    },
                    { xtype: 'component', itemId: 'zfs-ro-snapshots-status', html: 'Snapshots werden geladen …' },
                ],
                listeners: {
                    afterrender: function (view) {
                        var safe = function (value) {
                            return Ext.String.htmlEncode(String(value === null || value === undefined ? '' : value));
                        };
                        view.zfsRefreshReadOnly = function () {
                            var routes = [
                                ['zfs-ro-disks', 'zfs-ro-disks-status', 'disks/list'],
                                ['zfs-ro-pools', 'zfs-ro-pools-status', 'disks/zfs'],
                                ['zfs-ro-snapshots', 'zfs-ro-snapshots-status', 'zfsmanager-ro/snapshots'],
                            ];
                            Ext.Array.each(routes, function (route) {
                                var grid = view.down('#' + route[0]);
                                var status = view.down('#' + route[1]);
                                status.update('Lade Daten …');
                                grid.setLoading(true);
                                Proxmox.Utils.API2Request({
                                    url: '/nodes/' + encodeURIComponent(nodename) + '/' + route[2],
                                    method: 'GET',
                                    success: function (response) {
                                        grid.setLoading(false);
                                        var data = response && response.result && response.result.data;
                                        if (!Ext.isArray(data)) {
                                            grid.getStore().loadData([]);
                                            status.update('Unerwartetes API-Antwortformat.');
                                            return;
                                        }
                                        var store = grid.getStore();
                                        store.clearFilter();
                                        store.loadData(data);
                                        if (route[0] === 'zfs-ro-snapshots') {
                                            var filter = view.down('#zfs-ro-snapshot-filter');
                                            var term = filter && String(filter.getValue() || '').toLowerCase().trim();
                                            if (term) {
                                                store.filterBy(function (rec) {
                                                    return String(rec.get('name') || '').toLowerCase().indexOf(term) >= 0;
                                                });
                                            }
                                        }
                                        status.update(data.length + ' Eintrag/Einträge geladen.');
                                    },
                                    failure: function (response) {
                                        grid.setLoading(false);
                                        grid.getStore().loadData([]);
                                        status.update('API-Fehler: ' + safe(response &&
                                            (response.htmlStatus || response.statusText || 'Unbekannter Fehler')));
                                    },
                                });
                            });
                        };
                        view.zfsRefreshReadOnly();
                    },
                },
            });
        }
''' + END

# functions referenced by individual grid renderers are local to initComponent
# and added before the component configuration (still strictly within node.Config).
HELPER_BEGIN = '        // BEGIN PVE-ZFS-MANAGER-READONLY-HELPERS-v0.4.0b\n'
HELPER_END = '        // END PVE-ZFS-MANAGER-READONLY-HELPERS-v0.4.0b\n'
HELPERS = HELPER_BEGIN + r'''        var safeZFSValue = function (value) {
            return Ext.String.htmlEncode(String(value === null || value === undefined ? '' : value));
        };
        var zfsBytes = function (value) {
            var n = Number(value);
            if (!isFinite(n) || n < 0) {
                return '—';
            }
            var u = ['B', 'KiB', 'MiB', 'GiB', 'TiB', 'PiB'];
            var k = 0;
            while (n >= 1024 && k < u.length - 1) {
                n /= 1024;
                k++;
            }
            return n.toFixed(k ? 1 : 0) + ' ' + u[k];
        };
''' + HELPER_END


