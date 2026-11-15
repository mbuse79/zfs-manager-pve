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
