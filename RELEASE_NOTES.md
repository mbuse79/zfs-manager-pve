# BuMaVory ZFS Manager 1.1

Version 1.1 publishes the operator-confirmed RC10 Fix2 functionality with consistent
package, CLI, GUI and cluster bundle identification. Optional cluster installation
uses explicit selection, verified local package copies, repeated preflight and
confirmation. Existing cluster addresses/root SSH trust are used; no DNS fallback
for unknown members. Existing node settings and safety controls remain.

The operator confirmed the predecessor's rollout on PVE 9.2.26 and 9.2.21.
The exact 1.1 binary is newly built and automatically tested, not independently
reinstalled on real hosts. Real offline rescue, interrupted dpkg and concurrent
real coordinators remain unverified. See RELEASE-QA.md.

Use the full ZIP and docs/INSTALL-1.1.md. Bare DEB installation does not register
a distribution bundle. Project and third-party licenses remain separately scoped.
