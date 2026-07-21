# AGENTS.md

Guidance for any coding agent (Codex, Claude Code, etc.) working in this repository.
This is one of three UCC Stage-1 repos: **`nodectl`**, **`Artifact-compiler`**, **`VM-Factory`**.
This copy is trimmed to nodectl's own block — see the shared `/UCC/AGENTS.md` template
(one directory up from the three repo clones) for the other two repos' blocks and for
what to re-sync here if the shared core changes.

> **M-c note (this file superseded the repo's old operating-manual `AGENTS.md`):** the
> previous version of this file was a pre-UCC, single-purpose "build the htmx frontend"
> manual (naming the repo `nodepanel`, pointing at `backend/main.py` for routes, claiming
> `fabric` is the only SSH path). All of that predates the UCC Stage-1 work and was stale
> — routes live in `backend/routers/*.py`, not `main.py`; `services/ssh.py` uses `paramiko`
> for the git-credential/transfer/host-key surface, `fabric` is only used by the fenced,
> standalone-only `ssh_client.py`. See `RULES.md`/`MISSION.md` for the same cleanup.

---

## 0. What this repo is

A **UCC Stage-1 conformant standalone tool.** It runs and is tested on its own, and it
conforms to a shared contract layer so three repos can later integrate. The fork onto the
UCC line has **not** been cut yet. Pinned shared-contract version: **`ucc-contracts v0.2.0`**
(vendored under `third_party/ucc-contracts/`).

Two documents outrank this file and each other in this order — read them before non-trivial work:

1. `docs/roadmap/UCC-Shared-Roadmap-To-Fork.md` — the plan, gates, and the path to fork (§8).
2. `docs/reference/UCC-Standards-and-Layout-Reference.md` — the conventions everything conforms to.

**If this file disagrees with those, they win.** If the vendored `ucc-contracts` disagrees with
any prose, the code wins. Do not re-litigate decisions already locked in the roadmap's decisions
table (D1–D6) or its conflict-resolution table.

---

## 1. Shared core — non-negotiable rules (identical in all three repos)

1. **Fork scope is NARROW.** Do **not**: build the UCC product, merge repos, add a broker /
   network service / canonical database, or wire real cross-module adapters. Those are Stage 2
   (post-fork). Port adapters here may stay honest stubs.
2. **Fail closed over fabricate.** If you lack a real ID, hash, token, publication state, or
   record, refuse with a typed `ucc.problem` — never invent one. This is the same principle
   behind the vault and dry-run fixes; apply it everywhere, especially in port methods.
3. **No trusted-path arbitrary shell. No cross-module canonical writes.** Legacy raw-command and
   direct-infra paths survive only as **fenced, standalone-only diagnostics** and must never be
   reachable from a port. See §3 below for the exact fenced symbols.
4. **Fences are enforced by AST call-site tests, not substrings.** Mentioning a fenced symbol in a
   docstring is fine; adding a real call to it will (correctly) fail the guard. **Never "fix" a
   failing fence test by weakening it to text matching** — that regression already happened once
   and was reverted. If a fence test fails, you added a real forbidden call; remove it.
5. **`ucc-contracts` is vendored and pinned.** Never hand-edit schemas, ID rules, lifecycle
   tables, or refusal codes locally. If the contract needs to change, it changes upstream, gets a
   new tag, and is re-vendored — then this repo bumps its pinned version.
6. **Standalone stays usable.** Every change is additive or a fenced relocation. Never remove this
   repo's independent CLI/run path or its existing tests.
7. **Six-field format for every change**, in the PR/patch description:
   current evidence / target contract / smallest conforming change / compatibility impact /
   tests / migration or fallback.
8. **Delivery is via patches.** Clones are read-only (no push creds). Produce `.patch`/diffs and
   files; do not assume you can push. Patches are cumulative and order-sensitive per repo.
9. **Keep the docs in lockstep.** If you change the schema set or a gate's state, update the
   roadmap (§2/§8) and standards reference (§17) in the same change.

### Event / envelope conventions

- Each repo **dual-writes**: the legacy ledger/audit line **and** a schema-conformant `ucc.event`,
  never one instead of the other. The legacy writer stays byte-for-byte as-is.
- `ucc.event.causation_id` is **omitted when absent, never `null`** (unlike `ucc.request`, the event
  schema's `causation_id` is not nullable).
- `producer_sequence` is per-producer, not globally ordered; it is not race-safe under concurrent
  writers (matches the legacy ledgers — do not claim otherwise).
- Real canonical IDs (`art_`, `node_`, …) do not exist yet. Current `subject.id`s are **documented
  placeholders** (deterministic sha256-derived). Do not build logic that assumes they are the final
  canonical IDs; they are replaced in Stage 2.

---

## 2. Making a change here

- Start from the current HEAD; run the full suite **before** touching anything and report the count.
- Make the smallest conforming change. Prefer additive files (new test, new module) over edits to
  load-bearing or vendored code — and verify a "this is vendored, don't touch it" comment is
  actually still true before trusting it (see the M-c note above: this repo's own `ledger.py` had
  exactly that kind of stale claim).
- Re-run the full suite in an **independent fresh clone** before delivering — not just the working
  copy you edited.
- Write the six-field description. State compatibility impact honestly (operational changes count,
  e.g. "connecting to an un-pinned host now hard-fails").

---

## 3. This repo — nodectl

- **Shape:** FastAPI backend (`backend/`, real `create_app()`), HTMX/Jinja UI, `backend/ports/`,
  `backend/services/`. Vendored `third_party/ucc-contracts/`. An in-progress, not-yet-default Vue 3 +
  Vite presentation-layer redesign also lives under `frontend/` (conditionally mounted at `/app` only
  if `frontend/dist/assets` exists) — see `COMPONENT-MAP.md`.
- **Fenced — standalone-only, never behind a port** (guarded by `tests/unit/test_infra_fence.py`,
  AST-based):
  - route `POST /api/nodes/{node_name}/action/{action}` (allowlisted factory scripts over SSH);
  - `backend/ssh_client.py`: `run_factory_script`, `get_virsh_list`, `get_node_manifests`
    (uses the `fabric` library — the *only* fenced path that does; the rest of the app's remote-SSH
    surface, e.g. git deploy keys/transfers/host-keys, goes through `backend/services/ssh.py`, which
    uses `paramiko` directly, not `fabric`);
  - `backend/idempotent_node_action.py`: also an allowed caller of `run_factory_script` (M-b) — it's
    a standalone-route helper for `node_action`, not a port/adapter, so this was a deliberate
    extension of the allow-list, not a weakening;
  - `backend/services/factory.py`: `hypervisor_snapshot()` (`virsh list --all`);
  - `backend/routers/ui.py`: `tab_context()` (calls `hypervisor_snapshot` for the standalone tab);
  - `/api/terminal/ws` echo stub.
- **Ports:** `backend/ports/artifact_port_stub.py`, `factory_port_stub.py`, consumed via
  `app.state.artifact_port` / `app.state.factory_port`. **All methods refuse `DEPENDENCY_UNAVAILABLE`
  by design** — real adapters are Stage 2. The stubs must touch none of the fenced symbols above.
- **Events:** dual-write via `backend/ucc_events.py`, called from the `node_action` route — **not**
  from inside `backend/ledger.py`. `deterministic_id()` (was `_deterministic_id`, made public in M-b)
  derives placeholder subject/actor ids.
- **`backend/ledger.py` provenance (corrected, M-c/D5):** the file's own header used to claim it was a
  vendored copy ("source of truth lives in the soloctl repo, do not edit in place"). That was already
  false before D5 — Artifact-compiler's `soloctl/ledger.py` diverged into a smaller scrub+event-writer
  module some time ago, so there is no live source to sync from. The header now documents the
  divergence instead of asserting a sync contract that doesn't hold; edit this file directly like any
  other nodectl module.
- **Idempotency (M-b, D2, done):** `POST /api/nodes/{node_name}/action/{action}` — pass an
  `X-Idempotency-Key` header to opt in. Builds+validates `ucc.request`/`ucc.result`; replay returns
  HTTP 200 without re-running the action or re-logging the ledger/event (a replay is a cache hit, not
  a second execution); same key + different node/action refuses HTTP 409. Store: `idempotency_records`
  table (migration `003_idempotency_records.sql`) in the existing `nodepanel.db` (filename unchanged by
  D5 — out of that decision's four-item scope, see below), not a second SQLite file. It commits
  `unknown` before dispatch; success replaces that row, definite failure removes it, and ambiguity
  retains it so retry refuses `outcome_unknown` until reconciliation. No auto-expiry. Omitting the
  header keeps the pre-M-b behavior exactly.
- **`nodepanel`→`ucc` rename (D5, done):** writer switched immediately — `Ledger(tool=...)` in
  `backend/app.py` now tags `"nodectl"`; `VALID_TOOL` in `backend/ledger.py` dual-accepts `"nodepanel"`
  for the transition window (readers never enforced `VALID_TOOL` to begin with, so this is a
  no-behavioral-risk contract fix, not a live gate). Git-deploy-key remote paths
  (`backend/services/git_credentials.py`) moved to `~/.ssh/nodectl/`; `scrub()` removes the key at both
  the new and legacy `~/.ssh/nodepanel/` path so nodes provisioned before the rename still get cleaned
  up (`rm -f` is a no-op on a path that doesn't exist — no DB migration needed to track which path a
  credential used). Deliberately **not** touched (not in D5's four-item scope, real compatibility
  weight): `factory_user` (a real remote Linux username — renaming it breaks already-provisioned
  nodes), `database_path`/`session_cookie_name`/write-probe filename/CLI `prog=`.
- **Dev-root isolation + diagnostics (M-c, done):** bare local-dev defaults (`data_root`,
  `staging_root`, `inbox_root`, `ledger_root`, `ucc_events_root`, `database_path`,
  `ssh_known_hosts_path`) live under one git-ignored `.ucc-dev/` — additive only, every deployed
  environment already overrides every one of these via env vars. `secrets/` left untouched (separate
  concern). `backend/diagnostics.py` + `backend/cli.py`: `config show --effective --redacted` (secrets
  always redacted, no un-redacted mode) and `module-health` (a real `ucc.module-registration` record,
  `health` computed by running the same startup check `lifespan()` runs). `COMPONENT-MAP.md`
  classifies every component. The deterministic remediation rule found no filename match between
  the factory action allowlist and `library/scripts/`, so `gpt-ascii.html`, `library/manifest.json`,
  and `library/scripts/` were removed before the fork.
- **Tests:** `pytest`; suites under `tests/unit`, `tests/integration`, `tests/contracts`.
- **M-c hygiene done:** nested `nodectl/nodectl/` duplicate removed (confirmed dead first); `uploads/`
  untracked (content stays on disk).
- **Pending:** none — M-c is complete for this repo as of this change. Next is the fork gate (§6 of
  the roadmap), gated on all three repos' G1–G4 and the full §5 conformance suite.

---

## 4. Out of scope (do not do here)

Real cross-module adapters; canonical record stores; the ~26 domain schemas; projection builder;
UCC application services; broker / network API / server DB; repo merges; multi-operator auth; any
general remote terminal in a trusted path; frontend or deployment-topology decisions beyond the
already-approved Vue redesign in progress under `frontend/`. All of these are Stage 2 or a later
roadmap. If a task seems to require one, stop and flag it against the roadmap.
