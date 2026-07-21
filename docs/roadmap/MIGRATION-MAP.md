# MIGRATION-MAP.md — nodectl component → future UCC service/port

**Purpose:** closes fork-gate criterion **H6** (roadmap §6.6) — *"Migration map recorded:
current component → future UCC service/port."* Also serves as the **Stage 2 backlog**.

**Source:** derived from `COMPONENT-MAP.md` (M-c snapshot, 2026-07-15). That file says what
each component *is today*; this file says what each becomes *on the UCC line*.

**Scope:** `nodectl` only — it is the repo that forks onto the UCC line. `Artifact-compiler`
and `VM-Factory` stay standalone and are consumed through ports; their migration is
"expose the port, change nothing else."

**Status of every "Stage 2" row below: not authorized work.** This is a map, not a
mandate. Nothing here may be built before the fork gate passes.

**Authority basis:** ownership per SPEC-001 §D; planes per 2-of-2 §F; ports per
UCC-Standards §13. Where a row moves authority away from `nodectl`, the reason is that
`nodectl` currently holds authority that the locked matrix assigns elsewhere.

---

## 1. The three authority corrections this map encodes

Most rows are mechanical. Three are not — they are places where `nodectl` today *owns*
something the locked baseline says it must not, and the map records the correction:

1. **Hypervisor observation** (`get_virsh_list`, `hypervisor_snapshot`) — VM-Factory is
   the sole authority for hosts/nodes and their observed runtime state (§D). `nodectl`
   reading `virsh` directly is a second, competing source of truth. → `FactoryPort`.
2. **Controller↔node transfers** (`transfers.py`) — 2-of-2 §F.3 is explicit: *"VM-Factory
   separately owns controller-to-node and node-to-controller operational transfers."*
   `nodectl` staging files onto a managed node is VM-Factory's authority, not UCC's.
   → `FactoryPort`. (UCC keeps the *general* exchange plane: operator/browser↔UCC,
   external repos↔UCC.)
3. **Credential provisioning** (`git_credentials.py`) — credential *leases* are
   VM-Factory-owned (§D); repository *registrations* (which reference a credential) are
   UCC-owned materials (2-of-2 §F.2). This component currently does both. → splits.

These three are why "wire real adapters" is not a pure swap: three responsibilities leave
`nodectl` entirely.

---

## 2. Migration table

Target vocabulary: **ArtifactPort** / **FactoryPort** (the only cross-module seams);
**UCC app services** (Project/Job/Assignment/Operation); **UCC exchange** (`exchange/`);
**UCC materials** (`materials/`); **Command Catalog** (`catalog/`); **projection**
(disposable SQLite); **producer event stream** (`events/`); **retire** (deleted once its
replacement is real); **stays** (no authority change).

### 2.1 Core application (`backend/`)

| Component | Today | Future target | Stage 2 action |
|---|---|---|---|
| `app.py` | ucc-app | UCC application composition root | Stays. Add app-service wiring; ports move from stubs to real adapters. |
| `main.py` | ucc-app | ASGI entrypoint | Stays unchanged. |
| `config.py` | ucc-app | Path resolver + config precedence (SPEC-001 §C.6) | Stays. `.ucc-dev/` → logical category resolver (XDG per 2-of-2 §F.12). Domain code stops seeing raw paths. |
| `db.py` / `nodepanel.db` | ucc-app | **Splits by authority.** Idempotency records → canonical UCC operation journal (§D). Everything else → disposable projection. | Separate the two. Canonical rows must survive a projection rebuild; projection rows must be droppable. **This is the row most likely to be got wrong** — today one SQLite file holds both classes. |
| `auth.py` | ucc-app | Single-operator local boundary | Stays. Multi-operator auth is explicitly out of scope (§9 guardrails). |
| `security.py` | ucc-app | CSRF + headers | Stays. |
| `paths.py` (`safe_join`) | ucc-app | Shared path containment from `ucc-contracts` | **Retire** — replace with the vendored primitive so all three repos share one implementation (roadmap §1 rule 1). Keep until the shared one is proven equivalent. |
| `ledger.py` | ucc-app | Producer event stream (`events/ucc/`) + projection | **Retire after** the `ucc.event` stream is authoritative. Today's dual-write is the transition. Legacy JSONL stays readable (never rewritten). |
| `ucc_events.py` | ucc-app | UCC producer event-stream writer | Stays. `deterministic_id()` **retires** when real ULIDs land (closes **D4**). |
| `idempotency_store.py`, `idempotent_node_action.py` | ucc-app | UCC operation journal + idempotency layer (§D "Cross-module operation journal → UCC") | Generalize from one wrapped op to the app-service layer. F-007's durable in-flight/`unknown` refusal is already present and must be preserved. |
| `diagnostics.py` | diagnostic-only | Module registry + health view (UCC owns module registration, §D) | Stays. `module_version` placeholder resolves when a release process exists. |
| `cli.py` | diagnostic-only | UCC operator CLI | Stays; grows the one proof command. |
| `ssh_client.py`: `run_factory_script`, `get_virsh_list` | **legacy-standalone (fenced)** | **`FactoryPort`** (`list_eligible_nodes`, `get_node_health`, typed ops) | **Retire.** VM-Factory owns hypervisor observation and node action. Delete only once `FactoryPort` is real and proven — the fence exists precisely so this can't be quietly re-plumbed. |
| `ssh_client.py`: `get_node_manifests`, `normalize_manifest_record` | **legacy-standalone (fenced)** | **`FactoryPort`** (node manifest is VM-Factory-owned, §D) | **Retire** with the above. |

### 2.2 Ports (`backend/ports/`) — the swap points

| Component | Today | Future target | Stage 2 action |
|---|---|---|---|
| `artifact_port_stub.py` | artifact-adapter (refuses all) | Real in-process `ArtifactPort` → `soloctl` | Swap `build_artifact_port()`. Callers see only the Protocol, so nothing else changes. CLI adapter kept as tested fallback (locked I.2). |
| `factory_port_stub.py` | factory-adapter (refuses all) | Real in-process `FactoryPort` → VM-Factory engine | Swap `build_factory_port()`. Absorbs §2.1's fenced functions and §2.4's transfers. |

### 2.3 Routers (`backend/routers/`)

| Component | Today | Future target | Stage 2 action |
|---|---|---|---|
| `api.py` (as a surface) | command-catalog | **Command Catalog** (`catalog/`, UCC-owned, typed) | Routes become typed catalog operations (`ucc_builtin` / `published_artifact_revision` / `vm_factory_operation`). Catalog entries may **never** hold arbitrary shell strings (2-of-2 §F.9). |
| `api.py`: `POST /api/nodes/{n}/action/{a}` | **legacy-standalone (fenced)** | Typed `FactoryPort` ops (`reset_node`, `quarantine_node`, …) + Command Catalog | **Retire.** Its `ucc.request`/`ucc.result` envelope + idempotency wrapper are *kept* and lift to the app-service layer — the envelope work was never wasted, only its execution path retires. ⚠️ This route wraps **destroy** — see F-007; it must not re-execute under ambiguity. |
| `api.py`: transfer routes | materials-exchange | **`FactoryPort`** (controller↔node transfers are VMF-owned, 2-of-2 §F.3) | Authority moves out of `nodectl`. See §1.2. |
| `api.py`: git-credential routes | materials-exchange | **Splits:** registration → UCC materials; lease → `FactoryPort` | See §1.3. |
| `api.py`: host-key probe/approve | materials-exchange | **`FactoryPort`** (host-key binding is node identity, Part-G §3) | Authority moves to VM-Factory. |
| `health.py` | diagnostic-only | `/healthz` | Stays. |
| `terminal.py` | **legacy-standalone (fenced)** | **Stays fenced, permanently** | Locked: *"Any retained terminal is a separate operator diagnostic capability"* (1-of-2 §1.23) and is never reachable by automation. Not a migration target — a permanent exclusion. |
| `ui.py` | presentation | UCC operator view over projections | Stays. `tab_context()`'s fenced `hypervisor_snapshot()` call → `FactoryPort.get_node_health`. |

### 2.4 Services (`backend/services/`)

| Component | Today | Future target | Stage 2 action |
|---|---|---|---|
| `ssh.py` | ucc-app | Transport detail **inside** VM-Factory's adapter | **Retire from `nodectl`** once transfers/host-keys/credentials move. UCC application code must not hold an SSH client at all (SPEC-001 §C.7 UI/authority boundary). |
| `factory.py`: `hypervisor_snapshot()` | **legacy-standalone (fenced)** | **`FactoryPort.get_node_health` / `list_eligible_nodes`** | **Retire.** See §1.1. |
| `git_credentials.py` | materials-exchange | **Splits:** repo registration + credential *reference* → UCC materials (`materials/repositories/`); key provisioning + scrub → VM-Factory **credential lease** with cleanup evidence (§D, Part-G §7) | The D5 dual-path `scrub()` retires with it. Uncertain cleanup must quarantine the node. |
| `host_keys.py` | materials-exchange | **`FactoryPort`** | Retire from `nodectl`. |
| `transfers.py` | materials-exchange | **`FactoryPort`** typed transfer ops | See §1.2. UCC keeps only operator/browser↔UCC and external↔UCC exchange. |

### 2.5 Presentation

| Component | Today | Future target | Stage 2 action |
|---|---|---|---|
| `templates/*.html` | presentation | UCC operator views, projection-backed | Stays. Must read projections/app services only — never perform canonical writes (SPEC-001 §C.7). |
| `static/` | presentation | Same | Stays. |
| `frontend/src/**` (Vue) | legacy-standalone | **Open decision** — frontend framework is explicitly unresolved (§9 guardrails) | No Stage 2 action. Either becomes `presentation` when it ships, or the Jinja UI does. Do not force this decision as part of the fork. |

### 2.6 Remove candidates

| Component | Today | Verdict | Action |
|---|---|---|---|
| `gpt-ascii.html` | remove | Dead — no route serves it, no template includes it | Deleted before the fork. |
| `library/manifest.json`, `library/scripts/{approved,drafts}/*.sh` | remove | The allowlist names `assign`, `snapshot`, `destroy`; none matched the candidate filenames | Deleted before the fork; no Stage 2 asset migration. |

The filename check was run before deletion. The in-code action labels are `assign`,
`snapshot`, and `destroy`; the deleted scripts were `manifest-tool.sh`,
`tailscale-node-join.sh`, and `experimental-gpu-check.sh`. No deployment coupling was
present under the audit's rule.

### 2.7 Out of taxonomy

`Dockerfile`, `docker-compose.yml`, `build.sh`, `tailwind.config.js`, `pytest.ini`,
`requirements.txt`, ignore files, docs — configure/document the app. No migration target.
`docker-compose.yml` gains any new logical path category as it appears (the missing
`UCC_EVENTS_ROOT` mount, found in M-c, is the cautionary example).

---

## 3. Stage 2 ordering implied by this map

1. **Real `ArtifactPort`** (needs AC canonical records) — lowest risk, no authority moves.
2. **Real `FactoryPort`** (needs VMF `NodeState` split + typed ops) — then retire
   §2.1's fenced functions and `factory.py`.
3. **Move transfers + host-keys + credential provisioning** to VM-Factory — the largest
   authority change; do it after `FactoryPort` is proven.
4. **Split `db.py`** into canonical journal vs disposable projection; stand up the
   projection builder; prove delete-and-rebuild.
5. **Retire `deterministic_id()`** once real ULIDs exist (closes D4).
6. **Retire the legacy ledger** once the event stream is authoritative.
7. **Command Catalog** over the surviving typed routes.

`terminal.py` stays fenced throughout. The frontend decision stays open throughout.

---

## 4. Maintenance

Re-derive from code before trusting this in a later session — it is a snapshot, and
`COMPONENT-MAP.md` carries the same warning for the same reason. If a component is added,
it must appear in **both** files or the fork-gate criterion silently rots.
