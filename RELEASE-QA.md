# RC10 Fix2 validation — 15 November 2026

Version `1.0.0-34~rc10+fix2`. Fixes the standalone cluster SSH address resolver:
strictly refresh PVE::Cluster state before calling PVE::SSHInfo; require a known
member IP and refuse DNS fallback. Preserve node host-key aliases and strict SSH
verification. No changes to system DNS, SSH or Fabric configuration.

305 distinct tests: 284 normal plus 25 fakeroot, with four overlaps. Sixteen normal
root skips and five deselected ownership cases are run separately with fakeroot.
New real Perl subprocess fixtures start with an empty membership cache and verify
internal IPv4/IPv6 resolution and refusal of an unknown member. The Perl -T worker
regression remains enabled.

Operator confirmation on 15 November 2026: real cluster rollout from a PVE 9.2.26
coordinator installed Fix2 successfully on two existing PVE nodes, versions 9.2.26
and 9.2.21. Both previously lacked the manager package. Integration checks, watcher
and timer reported OK. Evidence is operator-provided logs/screenshot, not an
independent developer host session. This confirms fresh manager installation on
existing hosts; it does not establish a freshly installed PVE OS or every GUI/
snapshot action. Transport IP/interface was not shown. Interrupted dpkg and
multiple simultaneous coordinators remain untested. See
qa/RC10-FIX2-OPERATOR-CLUSTER-REPORT.json. The tested DEB/ZIP remain unchanged.

---
Historical Fix1 validation follows.

# RC10 Fix1 validation — 15 November 2026

Version `1.0.0-34~rc10+fix1`. The operator reported a cluster task start failure
under Proxmox Perl taint mode. The original RC10 error was reproduced exactly at
its system() invocation under `perl -T`. Narrow captures now validate and untaint
only the accepted argument grammars; the child environment is locally sanitized.
Taint mode, authorization and all snapshot protections remain enabled.

302 distinct tests: 281 normal plus 25 fakeroot, with four overlaps. The 16 normal
skips and five deselected ownership cases are covered by the fakeroot run. These
are isolated fixtures, including real subprocesses under Perl -T and upgrades
from the exact previous RC9/RC10 GUI/API bytes. No fixed-version host test is yet
confirmed. Real cluster installation, disconnect during dpkg and multiple real
coordinators remain untested. This is a test package, not a public release.

---
Historical RC10 validation follows.

# RC10 test package validation — 15 November 2026

Version `1.0.0-34~rc10`, optional confirmed cluster installation using the complete
verified RC10 bundle registered locally by the ZIP installer. No public release
and no real host/cluster installation performed in this development session.

300 distinct tests passed: 279 normal; 25 with fakeroot, including four overlapping
cases. The 16 skipped normal root fixtures and five deselected ownership cases
were all run separately with fakeroot. Real ExtJS 7 browser checks passed in DE/EN
with isolated API fixtures. Published RC9 GUI/API bytes were upgraded in an isolated
filesystem with node configuration, schedules and secrets preserved. Cache tests
verify full manifests, DEB metadata, corruption, symlinks, modes and version checks.

Not tested: actual cluster SSH, actual cross-node installation through this feature,
real interruption during dpkg, multiple real coordinators or real offline rescue.
RC9 operator confirmations do not validate RC10. See docs/RC10-TESTANLEITUNG-DE.md.

---

Historical RC9 validation follows; it describes the previous package only.

# RC9 release validation / Veröffentlichungsnachweis

Release candidate `v1.0.0-34-rc9`, Debian version `1.0.0-34~rc9`.
Tested DEB SHA256: **f48f7cfef9aacd070a3185c896b49b85149c90fe4b4595a15929bd2dee6a776f**.

On 15 November 2026 the operator reported "alle tests bestanden" and explicitly
requested publication, following the requested tests on the fresh test PVE and
existing host. PVE versions observed in the development session were 9.1.1 and
9.2.26. This is an operator confirmation, not an independent host session by Codex.
No blanket claim of every destructive path or real rescue boot follows from it.

The RC9 development runner reported 238 regular tests passed, 9 skipped and 5
selected ownership cases excluded. A separate fakeroot run passed 18 tests,
including the nine root-only mocks and five ownership cases, with four overlaps:
**252 distinct tests passed**. The expected ZIP duplicate-name warning is a negative
fixture. Logs are under qa/. These are local results, not automatically a CI claim.

Real ExtJS 7.0.0.168 browser tests passed in DE/EN with mocked Proxmox API responses:
two snapshot tabs, collapsed technical sections, details control, filtering,
selection/expansion persistence and mandatory retention preview. No API writes.
The screenshots use fixture data and are not production-host screenshots.

All 40 DEB runtime files match src. Compared with RC8, 37 are byte-identical; only
manager_patch.py and the installer/CLI version strings changed. Fifteen separately
recorded safety/API/inventory files are unchanged. See qa/rc9-artifact-check.json.

The public source tree keeps current public documentation separately from the
exact manuals embedded in the tested DEB. build_deb.sh uses packaging/rc9-tested-docs
for those manuals. Rebuilds must match all payload/control file contents; archive
timestamps can change the rebuilt DEB hash. Publication uses the original tested
DEB, never the verification rebuild. Root LICENSE and Debian copyright files keep
the public scoped-review status; historical packaged notices are retained as evidence.

The private test ZIP contained internal project handover files. The public ZIP
omits them and adds public release documentation, so its checksum is new. The
DEB and executable bootstrap/installer bytes are unchanged. The previous private
ZIP SHA256 was d184fcc958c84cb86eeb081ae48027b62026799b784f62b60697930899fe1e81.
The old v1.0.0-32 release and its assets remain unchanged.
