"""nodectl's port stubs (G3, roadmap §4A "Add port + envelope stubs").

nodectl is the UCC application shell (roadmap §7); it reaches Artifact
Compiler and VM-Factory ONLY through ArtifactPort/FactoryPort, never by
importing their domain code (that would need a running peer or cross-repo
coupling this roadmap explicitly rules out). These stubs are the
Protocol-conformant placeholder nodectl consumes today — every method
refuses `DEPENDENCY_UNAVAILABLE` because no real adapter is wired in yet.

Stage 2 / G5 ("Wire real in-process adapters behind the ArtifactPort/
FactoryPort stubs") replaces the module-level `build_*` functions below
with ones that import the conformant Artifact Compiler / VM-Factory
packages directly (in-process by default; CLI adapter is the tested
fallback per locked decision I.2) — nothing else in nodectl should need to
change, since callers only ever see the Protocol.

Nothing under backend/routers/, backend/ssh_client.py, or
backend/services/factory.py may be called from here — those are the fenced
standalone-only infra paths (see tests/unit/test_infra_fence.py); this
package exists specifically so a future adapter has nothing to bypass them
with.
"""
