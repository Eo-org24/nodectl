# nodectl — Component Map

M-c deliverable (roadmap §4A "Classify every component"). Every component is
tagged with exactly one of the nine categories the roadmap defines:

`ucc-app` (cross-cutting app composition/infra) · `presentation` (renders UI)
· `materials-exchange` (moves files/credentials to or from a remote node) ·
`command-catalog` (the API surface of controllable actions) ·
`artifact-adapter` (Stage-2 seam toward Artifact-compiler) ·
`factory-adapter` (Stage-2 seam toward VM-Factory) · `diagnostic-only`
(read-only, no mutation) · `legacy-standalone` (fenced — must never be
reachable from a port, per `tests/unit/test_infra_fence.py`) · `remove`
(dead, removed before the fork after the deterministic filename check).

This is a snapshot as of M-c (2026-07-15). Re-derive from the code before
trusting it in a later session — do not assume it stays accurate as the
repo changes.

## `backend/` — core application

| Component | Category | Notes |
|---|---|---|
| `app.py` | ucc-app | `create_app()`, lifespan (startup health check), route/mount wiring. |
| `main.py` | ucc-app | ASGI entrypoint (`uvicorn backend.main:app`). |
| `config.py` | ucc-app | `Settings` (pydantic-settings). Dev-root isolation (M-c) lives here. |
| `db.py` | ucc-app | SQLite connection/schema init (`nodepanel.db` — filename unchanged by D5, see AGENTS.md). |
| `auth.py` | ucc-app | Session issuing/verification (HMAC-signed cookie). |
| `security.py` | ucc-app | CSRF token check, security headers. |
| `paths.py` | ucc-app | `safe_join` — path-traversal guard, shared by materials-exchange routes. |
| `ledger.py` | ucc-app | Append-only audit writer. Not vendored despite the old header comment's claim (corrected in M-c/D5 — see AGENTS.md). `VALID_TOOL` dual-accepts `nodepanel` through the D5 transition window. |
| `ucc_events.py` | ucc-app | G2 event dual-write (`ucc.event` alongside the legacy ledger entry); `deterministic_id()` (D4 placeholder-ID convention). |
| `idempotency_store.py`, `idempotent_node_action.py` | ucc-app | M-b: SQLite-backed idempotent-replay wrapper around the one fenced real operation (`node_action`). |
| `diagnostics.py` | diagnostic-only | M-c: `effective_config()` (secrets always redacted), `module_health()` (`ucc.module-registration`-shaped, computed from the same startup check `lifespan()` runs — never fabricated). |
| `cli.py` | diagnostic-only | `ssh-diagnose`, `config show`, `module-health` — every subcommand is read-only. |
| `ssh_client.py`: `run_factory_script`, `get_virsh_list` | legacy-standalone | **Fenced.** Direct SSH execution of allowlisted scripts / `virsh list --all` against the factory host. Never reachable from a port — `FactoryPort` is a separate seam (see below), not a wrapper around these. |
| `ssh_client.py`: `get_node_manifests`, `normalize_manifest_record` | legacy-standalone | **Fenced.** Reads remote VM node manifest files directly over SFTP. |

## `backend/ports/` — the real Stage-2 seam

| Component | Category | Notes |
|---|---|---|
| `artifact_port_stub.py` | artifact-adapter | Every method refuses `DEPENDENCY_UNAVAILABLE` by design (G3). Consumed as `app.state.artifact_port`. Real adapter is Stage 2 — out of narrow-fork scope. |
| `factory_port_stub.py` | factory-adapter | Same shape, `app.state.factory_port`. **Must never call `ssh_client.py`'s fenced functions or `services/factory.py`'s `hypervisor_snapshot`** — that's the actual fence `test_infra_fence.py` enforces (AST-based, not a naming convention). |

## `backend/routers/`

| Component | Category | Notes |
|---|---|---|
| `api.py` | command-catalog | The controllable-action surface as a whole. Mixed internally — see below. |
| `api.py`: `POST /api/nodes/{node_name}/action/{action}` | legacy-standalone | **Fenced** (allowlisted factory scripts over SSH). Also the one route wrapped in `ucc.request`/`ucc.result` envelopes + M-b idempotency for G2 conformance — envelope conformance and standalone-only execution are independent properties; this route has both. |
| `api.py`: transfer routes (stage/collect) | materials-exchange | Delegates to `services/transfers.py`. |
| `api.py`: git-credential routes | materials-exchange | Delegates to `services/git_credentials.py` (D5-renamed remote paths, dual-accept scrub). |
| `api.py`: host-key probe/approve routes | materials-exchange | Delegates to `services/host_keys.py` — trust establishment before a materials-exchange operation. |
| `health.py` | diagnostic-only | `/healthz`, driven by `app.state.health_ready`/`health_error` (set in `app.py`'s `lifespan()`). |
| `terminal.py` | legacy-standalone | **Fenced.** `/api/terminal/ws` — an echo stub, not a real shell. Origin-checked. |
| `ui.py` | presentation | Jinja/HTMX tab rendering. `tab_context()` calls the fenced `hypervisor_snapshot()` for the standalone dashboard tab — a fenced call site, but the router itself is presentation. |

## `backend/services/`

| Component | Category | Notes |
|---|---|---|
| `ssh.py` | ucc-app | Generic SSH/SFTP transport client shared by both fenced (factory) and materials-exchange (git/transfer/host-key) call sites — not itself a materials-mover. |
| `factory.py`: `hypervisor_snapshot()` | legacy-standalone | **Fenced.** `virsh list --all` against the factory host. |
| `git_credentials.py` | materials-exchange | Deploy-key provisioning/scrub. D5: writes new keys to `~/.ssh/nodectl/`, `scrub()` dual-removes the legacy `~/.ssh/nodepanel/` path too. |
| `host_keys.py` | materials-exchange | SSH host-key probe/approve (trust bootstrap before transfers). |
| `transfers.py` | materials-exchange | Staged file transfer to/from a managed node. |

## Presentation

| Component | Category | Notes |
|---|---|---|
| `templates/*.html` | presentation | Server-rendered Jinja + HTMX partials. The default, shipped UI. |
| `static/` (`input.css`, `output.css`, `vapor.css`, `vendor/htmx.min.js`, `vendor/xterm*`) | presentation | Built/vendored front-end assets for the Jinja UI. |
| `frontend/src/**` (Vue 3 + TS) | legacy-standalone | **In-progress redesign, not dead.** Conditionally mounted at `/app` only if `frontend/dist/assets` exists (`app.py`); 404s otherwise. Backed by `Document pack/NodePanel Vue Frontend Redesign.docx` + `plan.txt` (still present at repo root). Not yet the default UI — tag may change to `presentation` once it replaces the Jinja UI, or the Jinja UI moves to `legacy-standalone` if the Vue rewrite ships first. |

## Resolved `remove` candidates

- `gpt-ascii.html` was dead: no route served it and no template included it.
- The in-code factory action allowlist names `assign`, `snapshot`, and `destroy`.
  None matched `library/scripts/approved/manifest-tool.sh`,
  `library/scripts/approved/tailscale-node-join.sh`, or
  `library/scripts/drafts/experimental-gpu-check.sh`. Under the audit's deterministic
  rule there was no deployment coupling, so `library/manifest.json` and
  `library/scripts/` were deleted before the fork.

## Not part of the taxonomy (build/ops tooling)

`Dockerfile`, `docker-compose.yml`, `build.sh`, `tailwind.config.js`, `pytest.ini`,
`requirements.txt`, `.gitignore`/`.dockerignore`, `README.md`, `docs/*.md` — these
configure or document the app rather than being a component of it.

## Agent-instruction-file reconciliation (M-c, last item)

`AGENTS.md`/`CLAUDE.md`/`RULES.md`/`MISSION.md` reviewed and rewritten — not blanket-deleted — for
contradictions with the current, locked baseline:

- **`AGENTS.md` (repo-local)** was a pre-UCC, single-purpose "wire the htmx frontend" operating
  manual (named the repo `nodepanel`, pointed at `backend/main.py` for routes, claimed `fabric` is
  the only SSH path). Replaced with a trimmed copy of the shared `/UCC/AGENTS.md` template (§0/§1/§2
  verbatim, only this repo's §3 block, §4), carrying forward the M-c note explaining what was wrong
  with the old version so it isn't silently lost.
- **`CLAUDE.md`** didn't exist in this repo yet — added as a copy of the shared root `CLAUDE.md`
  (which needed one fix of its own: it used "this repo's vendored ledger" as an example of
  load-bearing code to be careful with, which is exactly the claim that turned out to be false —
  reworded to tell the reader to verify a vendoring claim rather than trust it, both here and in the
  shared template so the other two repos get the corrected wording too).
- **`RULES.md`**: two of six original rules were factually wrong by M-c — rule 4 ("the dashboard
  does not possess a database") is directly contradicted by `backend/db.py`/`nodepanel.db`, load-bearing
  for git credentials, host keys, and M-b's idempotency records; rule 3 ("route all system commands
  through `run_factory_script`/`fabric`") predates `backend/services/ssh.py`, a second,
  `paramiko`-based SSH surface that now handles git deploy keys/transfers/host-keys and isn't fabric
  at all. Rewritten in place with the corrections, not deleted — a "hard constraints" file that's
  actively wrong is worse than one that's merely dated.
- **`MISSION.md`**: described phase 1–4 of the original prototype build-out. Phases 1–3 are done;
  phase 4 (`/api/nodes/create`, a worker-creation form) was never built and, per the now-locked
  narrow-fork scope (no real cross-module adapters / canonical record store), is Stage-2 scope, not
  live authorization to build it now. Rewritten to point at `AGENTS.md`/the roadmap as the actual
  current mission driver instead of a stale phase list.

This is the same category of problem found and fixed mid-flight during the D5 and dev-root work
(`ledger.py`'s stale vendoring claim) — expect the same kind of check to be worth doing in
`Artifact-compiler`'s `HANDOFF_NOTES.md` and VM-Factory's `AGENTS.md` / `ai-worker-factory-plan.md` /
`factory-panel-convergence.md` / `FIRE-AWAY.md` before assuming those are current either.
