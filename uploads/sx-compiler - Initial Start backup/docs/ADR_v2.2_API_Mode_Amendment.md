# ADR Amendment v2.2 — API-Mode Inference (+ consolidated dispositions)

**Status:** CONFIRMED upon human merge. Amends ADR_v2.1.md (add to its header: "Amended by v2.2 — API mode").
**Prime change:** inference moves from local-primary to **API-primary with local as the planned return target**. All architecture, all decisions, and all rationale stand — including decisions originally motivated by local-model limitations. This is recorded as a *preemptive, velocity-driven* execution of the D15 pivot the roadmap pre-committed to, not an evidence-driven one. The project remains **local-first in state** (Markdown on disk is the only canonical store); inference locality becomes a deployment option.

---

## 1. D15 — Model profile (recast)

Primary driver: a pinned frontier API model (provider + exact model version string in `part0.yaml`; Q-002 selects). The locked sentence carries the whole amendment: **identical filesystem behavior local and frontier** — the harness cannot tell which model answered. Local 24–32B remains the deployment target; its admission runs at re-entry (§7). 7–8B control-plane clause dormant until local returns.

**Option B rejection maintained under API mode (recorded).** With a frontier primary, the agentic-CLI loop becomes *capable* again; it stays rejected for unattended canonical ingestion because the two-plane design's properties are model-independent: corruption-impossibility by construction, decision-validation-before-synthesis, full auditability via traces, and the planned local return (a harness serving both modes must be built for the weaker one). Future reviewers proposing "you're on frontier now, use an agent" are relitigating a settled decision without new evidence.

## 2. D14 — Privacy gates (re-scoped, not removed)

In local mode, gates sat at the escalation boundary. In API mode **every pack transits a cloud API**, so the gates move upstream to **queue admission**:

- Sources tagged `private`/`credential` (frontmatter or config allowlist) are **excluded from compilation entirely** while `inference_mode: api`. They queue as `held_private` and compile only when local returns.
- Secret scan runs **pre-pack** (before any API call), not merely pre-escalation.
- The escalation tier is N/A in API mode (primary *is* frontier); ladder = retry → quarantine. Full ladder returns with local mode.
- Provider requirements (Q-002): zero-/minimal-retention tier where available; no training on submitted content; recorded in the decision log.
- Escalation-log rule generalizes: **API request logs record source hashes and trace IDs, never text.**

## 3. D16 — Determinism (Tier 1 dormant)

APIs guarantee neither seeds nor stable weights. Tier 1 (byte-identity) is claimed **only** under a local pinned profile and is dormant until re-entry. Tier 2 (structural) — fixed pack ordering, validation, script-generated artifacts, pack hashing — is the guarantee in API mode, exactly as it already was for mixed mode. Repeat runs measure **decision-stability rate** as a health metric, not a pass/fail. Profile-rot vector transforms: provider model deprecation replaces llama.cpp drift; ritual unchanged (pin version string → on forced migration rerun M0 + full fixtures under the new version → log new profile → accept textual divergence; properties, not bytes, are the contract).

## 4. D3/D2 — Decision-shape mechanism (provider-appropriate)

The contract is "the decision object validates against the schema." Mechanism: GBNF grammar (local) / provider structured-output or JSON-schema mode (API). Harness-side validation (`ALLOWED_TARGETS`, IDs, slugs, span rules) is unchanged and was always the real guarantee. Sentinel protocol for the data plane is unchanged in both modes.

## 5. D13/D19 — Transport, cost, batching

- **Transport retries are infrastructure, invisible to D13.** Rate limits, 5xx, timeouts → bounded exponential backoff at the client layer; they never consume the semantic retry budget or emit failure records (a 529 is weather, not a reasoning failure). Persistent transport failure pauses the queue and surfaces to the human; it never quarantines units.
- **Cost guardrails (Part 0 additions):** `api.max_cost_per_batch`, `api.max_cost_per_unit_warn`; cost-per-unit logged in traces; V2/M3 reports cost alongside wall-clock. Batch exceeding its cap pauses cleanly at the next unit boundary.
- **D19 batch mapping:** the async posture maps onto provider batch APIs (≈50% discount, hours-scale latency — a fit, not a compromise). Serialization constraint note: units with retrieval dependencies stay sequential; **Stage-1 inventory summaries (already parallel-sanctioned) are the batch-API sweet spot.**

## 6. Part 0 — New/changed rows

| Constant | Default | Owner | Notes |
|---|---|---|---|
| inference_mode | api | config | `api` \| `local` |
| api.model | (Q-002) | M0 | exact version string, pinned |
| api.retention_tier | (Q-002) | human | zero-retention preferred |
| api.max_cost_per_batch | set at W-001 | V2 | hard pause |
| pack budget | frontier column active (≈12k) | V2 | local column dormant, retained |
| ingest.skip | .canvas, attachments dirs, binaries | W-004 | Obsidian artifact skip-list; dataview blocks pass through as text |
| log rotation | yearly (`log-YYYY.md`) | hygiene | append-only preserved |
| source_origin | self \| third_party | manifest field | injection-risk classing (Risk 1) |
| chunking policy | structural-first (see §8) | V2 | W-005 spec |

## 7. Local re-entry checklist (formal, so return day is a procedure, not a project)

1. Pin the local execution profile (model/tokenizer/build hashes, seed, sampling).
2. **M0-local:** run the FULL accumulated fixture corpus (batch A + B + every correction-origin fixture from the API era) — the API era builds the local model's admission exam.
3. V4 Tier 1 under the pinned profile.
4. Bootstrap-grade humility: create-bias mandatory for the first local batches regardless of calibration age; prompts were implicitly tuned to frontier judgment (Risk 10 inversion) — expect and log the delta.
5. Cosine thresholds survive only if the embedding model is unchanged (they are embedding-owned, not LLM-owned); otherwise V1 recalibration.
6. Flip `inference_mode: local`; `held_private` sources release into the queue; full D14 ladder reactivates.

## 8. Chunking policy (Risk 9 resolution → D5 step-2 note; W-005 spec)

Structural-first, strictly deterministic: split at headings when present; **never cross a heading boundary**; paragraph-group within headings toward the Part 0 size band; tolerate undersized chunks rather than boundary-crossing ones; merge trailing fragments into their same-heading predecessor; **no overlapping windows** (a compiler must ingest each claim exactly once — overlap is a retrieval trick that poisons provenance). Trace annotation `chunk_had_headings: bool`; V2 correlates residual_rate against structureless sources before anything smarter is considered. **Rejected:** semantic/embedding-based chunk boundaries (model-assisted before deterministic-proven-insufficient — selection-rule violation); overlapping windows (provenance duplication).

## 9. D20/manifest — Injection posture (Risk 1 project-side, locked now)

- `source_origin` recorded per source at projection/snapshot time; defaults `self`, human marks `third_party` (web clippings, shared docs, anything not self-authored).
- Injection-pattern lint: **warning tier, config-off** at v0; scans raw sources for instruction-like imperatives; intended to flip to needs_review for `third_party` sources at the first observed meta-instruction incident (FUTURE_RISKS tripwire).
- Model-side hardening (classifier pass, prompt armor) explicitly deferred: API-mode frontier models raise the baseline during the safe-corpus era.

## 10. Part V hygiene additions (Risk 8 mechanisms)

Baton-consistency checker in CI (commit prefix vs PROGRESS baton) + repo secret scan — W-015. Batch lockfile: `sx` creates `.batch-running` at batch start, removes at end; agents refuse to operate while present (agent-file patches). Instruction-file edits are human-hands-only: agents propose exact diffs in PROGRESS Questions; approved diffs are applied by the human. `docs/archive/` for superseded documents (DOC_MAINTENANCE).

## 11. Gate wording deltas

- **M0** = pinned API model + structured-output mechanism vs batch A (`--repeat 2`; decision-stability recorded). Runs as soon as W-003 + an API key exist — earlier and cheaper than planned.
- **M1** Tier 1 byte-check → N/A-until-local; keep repeat run as measurement; all V5/V8 checks unchanged.
- **Kill-criterion note:** the "two local models fail M0" pivot is recorded as taken preemptively; its inverse risk (overconfidence transfer) is owned by §7.4.
- **V2/M3:** + cost-per-unit; correction-time tolerance unchanged and still pre-committed.
