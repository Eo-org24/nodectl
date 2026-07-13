# Architecture Decision Record — LLM Wiki Compiler (v2.1)

**Status:** LOCKED — supersedes ADR v2 and the OQ1–OQ3 Lockdown (both fully merged here; this is now the single architecture contract).
**Amended by:** ADR_v2.2_API_Mode_Amendment.md (API-primary inference; load together until merged).
**Date:** 2026-07-06

**v2.1 change log vs v2:** (1) Judgment/Execution Boundary added as named invariant; (2) D3 amended — residual re-enqueue; (3) D5 amended — residual lifecycle, slicing, sentence markers; (4) D2 amended — split orchestration (two calls, child-first promotion); (5) new D23 — promotion nominations; (6) new D24 — routing identifier authority; (7) D21 amended — ownership matrix, summary admission, enum reconciliation, mechanical `related:`; (8) D19 amended — Stage-1 parallelism carve-out, residual queue states; (9) Part 0 additions; (10) rejected register additions; (11) new Accepted Limitations & Labeled Uncertainty section; (12) gate metric additions.

**Lock discipline (unchanged):** three layers — architecture contract (locked; changes require a new revision), operating constants (Part 0, empirical, gate-owned), implementation hygiene (roadmap items). Per-decision status: LOCKED / LOCKED-AMENDED / CONSTANTS-HELD.

---

## Named Invariant — Judgment/Execution Boundary

The model judges within a single bounded call. The harness executes.

The harness owns all filesystem mutation, source slicing, queue lifecycle, retrieval packing, cache refresh, generated artifacts, and every input that can influence future routing. The model may classify, select, cite, and synthesize only inside contracts whose outputs are mechanically validated before they affect canonical state.

**Corollary (selection rule):** choose the most deterministic viable mechanism first; add model-assisted upgrades only when a V-gate metric proves deterministic mechanisms insufficient.

**Named exception:** page summaries are model-authored yet influence routing (they are the candidate descriptions the control plane reads). They cannot be harness-authored, so they are governed by admission checks and stability rules instead of ownership transfer (D21).

---

## Part 0 — Operating Constants Table

Empirical defaults, gate-owned; none are architectural truths.

| Constant | Default | Owner gate | Notes |
|---|---|---|---|
| Page body cap (mutable pages) | 1,200 tokens | V7 | Counted by the pinned reference tokenizer (D16) |
| Legacy-page segmentation trigger | 6,000 tokens | V7 | Linter flags for mechanical split |
| Chunk size | 400–800 tokens | V2 | Recursive paragraph split above 1,000 |
| R2 merge threshold (cosine) | ≥ 0.80 | V1 | Invalid after any embedding-model swap |
| R3 branch band (cosine) | 0.60–0.80 | V1 | Same calibration rule |
| RRF smoothing k | 60 | V1 | |
| BM25 column weights | title 4.0 / heading 3.0 / body 1.0 | V1 | |
| FTS / vector top-k | 12 each | V1 | |
| Fused candidates kept | 6 (+ all anchors) | V1 | |
| Neighbor stubs | ≤ 20 local / ≤ 40 frontier | V2 | ~25 tokens each |
| Context pack budget | ≈ 6.5k local / ≈ 12k frontier | V2, V4 | Slot allocation in D5 |
| Outbound-link quota | ≥ 2 per page | V3 | Validation hypothesis |
| Retry count before escalate/quarantine | 1 | V2 | |
| Brute-force vector ceiling | ~5,000 chunks | V2 | sqlite-vec/ANN beyond |
| Bootstrap conservatism | bias `create_page` when uncertain | V1, V2 | D4 |
| **Residual recursion depth** | 1 (2 by config) | V2 | new in v2.1 |
| **Genericity DF threshold** | 0.08 | V1 | + static denylist (e.g., dag, router, queue, cache, compiler) |
| **Nomination hubs** | architecture, patterns, incidents, glossary | M4 usage | config, not architecture |
| **Summary length cap** | 160 chars | V2 | hard lint |
| **M3 correction-time tolerance** | set before first retained ingest | V2 | pre-committed, not post-hoc |

---

## Part I — The Two Load-Bearing Decisions

### D1. Page granularity — LOCKED-AMENDED
All LLM-mutable pages are atomic-leaning concept pages under **one** body cap (Part 0; reference tokenizer). No per-page-type cap exceptions for mutable pages. Long content takes sanctioned paths: generated read surfaces (outside the LLM write set, cap-exempt) or frontier synthesis under D14 (cap unchanged). Rationale: whole page = atomic write unit deletes the diffing problem; regeneration stays inside local-model adherence windows; fragmentation risk is empirical, owned by V7.

### D2. Mutation mechanics: Two-Plane Compiler — LOCKED-AMENDED
Control plane: one grammar-constrained routing call. Data plane: complete Markdown pages between `<<<PAGE path="...">>>` / `<<<END PAGE>>>` sentinels. No JSON around content, no diffs, no agentic loop. Python owns all I/O, retrieval packing, routing artifacts, cache refresh. Everything outside sentinels is discarded unread.

- **2a Atomic staging/promotion:** parse → lint (D20) → staging dir → fsync → atomic rename → manifests last. Crash leaves old state or new state, never a torn file.
- **2b Path safety:** sentinel paths are untrusted. Vault-relative POSIX only; reject absolute, `..`, symlink escapes, ambiguous paths, anything outside `ALLOWED_TARGETS`; generated-artifact writes rejected unconditionally.
- **2c Optimistic concurrency:** target hash recorded at pack-assembly; re-hashed at promotion; mismatch → abort, requeue, rebuild pack. Editor-agnostic (protects against any concurrent writer).
- **2d Salvage list:** constrained decoding (control plane); surgical SQLite refresh; trigram contingency; async-batch posture. (Single-SQL RRF removed — D8.)
- **2e Split orchestration (new in v2.1):** one `split_target` decision spawns **two sequential data-plane calls**, each one complete page: child first (split section + new content), then parent regeneration (minus section, plus wikilink to child). Both stage together; **promotion order child-before-parent** so the parent's link never dangles; the pair promotes or quarantines as a unit.

---

## Part II — Decision Register

### D3. Control-plane decision contract — LOCKED-AMENDED (v2.1: residual)
Action enum: `merge_into | create_page | split_target | contradiction | discard`. **Single primary action per compile unit** — no ordered action lists, no decomposer.

```json
{
  "action": "merge_into | create_page | split_target | contradiction | discard",
  "target_path": "string from ALLOWED_TARGETS or null",
  "new_page": { "title": "", "slug": "", "hub": "" },
  "reason_code": "exact_title | high_similarity | scope_mismatch | size_cap | conflict",
  "required_links": ["pages/related.md"],
  "candidate_ids": [], "claim_ids": [],
  "split_section": "heading path or null",
  "uncertainty": "low | medium | high",
  "escalation_recommended": false,
  "residual": {
    "span_type": "sentence_markers",
    "start_marker": "S4", "end_marker": "S7",
    "reason": "distinct_concept | second_update | unclear_scope"
  }
}
```

`residual` may be null. It flags durable material outside the primary action; the harness slices and re-enqueues it as a derived compile unit. `reason` is **diagnostic-only** (no machinery branches on it; distribution is a V2 metric). `evidence` quote fields remain rejected — traceability lives in the D5 trace. Python validates `target_path`, slug, candidate/claim IDs against the pack.

**C′ consistency rationale (recorded).** Sentinel-block patching was rejected because grammar constrains shape, not anchoring — and a residual span *is* anchoring. The admitting asymmetry: C′ anchored **edits to canonical output** (fuzzy failure silently corrupts); residual anchors **selection of input**. *Mechanical* failure (unrecoverable markers, invalid span) is corruption-impossible — harness drops the residual, primary commits, locked-contract loss mode plus lint warning. *Semantic* failure (valid but misplaced span) degrades to misplacement — the pre-existing loss mode — never page corruption. V0 span-fidelity fixtures test the semantic half.

### D4. Merge vs. Branch rules — CONSTANTS-HELD
R1–R7 locked (exact-anchor merge; high-similarity merge; sibling branch + mandatory candidate link; low-similarity branch under HUB_HINT; size-cap split; slug-collision rejection; conflict outranks merge; embeddings-off BM25 fallback; ≥2 links on create/split). Thresholds in Part 0; embedding swap invalidates cosines. **Error-cost asymmetry:** false branch cheap, false merge contaminates provenance → bias `create_page` under uncertainty; ties break to branch. **Bootstrap mode:** first ingest runs uncalibrated; merge requires exact anchor or R2 with `uncertainty: low`. Link quota is a V3 hypothesis.

### D5. Compile-time retrieval SOP — LOCKED-AMENDED (v2.1: residual mechanics)
14-step pipeline stands (change detection → chunking → keyphrases → exact anchors → FTS/BM25 → optional vectors → RRF → 1-hop stubs → hub hint → budgeted pack → control call → data call → post-pass → mechanical routing artifacts).

- **Retrieval trace:** per-unit JSON (hashes, keyphrases, anchors, results, fusion, allowed targets, action, pack token count, pack hash → D16) under `.sx/cache/traces/`, disposable.
- **Exact-anchor softening:** anchors are preferred candidates, never automatic; reject on contradiction/namespace/page-type/scope mismatch. Structural backstop in D24 (contested-alias demotion).
- **Deletion/rename semantics:** manifest-present, disk-absent = deletion → dependent pages `status: stale` + needs_review; pages never auto-deleted. Same content hash under new path = rename → mechanical manifest/`sources:` rewrite, no recompile.
- **Batch-order determinism:** strictly serialized loop, per-unit cache refresh (unit N+1 sees post-N state); order = source path, then chunk ordinal; different order = harness bug.
- **Sentence markers (v2.1):** harness renders `[S1]…` markers into the control-plane view of the chunk; markers are stripped before any data-plane call.
- **Slice-before-synthesis (v2.1):** on valid residual, the harness slices before the primary data-plane call; primary synthesis receives only the primary remainder.
- **Residual lifecycle (v2.1):** residual admitted to the queue only when its parent unit reaches `promoted`; on parent retry/requeue (incl. 2c aborts)/quarantine, the residual is discarded — the re-run re-emits it or not. Derived refs `#<ordinal>!r<n>`; depth per Part 0; derived units sort immediately after their parent. Post-parent-commit pack visibility follows from the per-unit refresh already mandated here (with D17 mechanics); recorded consequence: the parent's freshly promoted page appears naturally in the residual's retrieval — the self-healing path for semantically misplaced spans.
- **Span validation (v2.1):** admit only if proper subset of chunk; non-empty primary remainder; markers exist exactly once; boundaries mechanically recoverable; depth within cap. Proportional size checks are warnings, never hard failures.
- **Stage-1 parallelism carve-out (v2.1, closes companion item):** the determinism invariant applies to **graph-mutating** compile units. Cold-start Stage-1 inventory summaries depend only on their own source and mutate no shared graph state; they may run in parallel.

### D6. FTS layer — CONSTANTS-HELD
FTS5, `porter unicode61`, columns title/heading_path/text, weights per Part 0. Two-pass query ladder (quoted phrases → sanitized unquoted → trigram secondary only if `fts-misses.log` justifies during V2). Operator stripping. Tokenizer fixtures are Phase 0 hygiene (H1).

### D7. Vector layer — CONSTANTS-HELD
Derived, disposable, gitignored, never canonical/synced; loop must not depend on it. Embedding model selected by V1 (candidates: nomic-embed-text-v1.5, bge-small-en-v1.5, Qwen3-Embedding-0.6B class); pinned in config; swap invalidates thresholds + full re-embed + V1 recalibration. **Embedding asymmetry:** raw notes vs synthesized prose is an asymmetric task; task-prefix protocol fixed per candidate before scoring. Brute-force NumPy to the Part 0 ceiling; sqlite-vec beyond; ANN post-MVP.

### D8. Rank fusion — LOCKED-AMENDED
RRF (BM25 and cosine are incomparable distributions; never linear-weighted). Implemented **in Python**; removes SQLite ≥3.39 dependency. Cross-encoder rerank is Phase 2+ escalation.

### D9. Neighborhood context — LOCKED-AMENDED
1-hop stubs (path + title + `summary:`) default; full neighbor bodies never load in the standard loop; frontier/supervised escalation may load selected bodies only with trace-recorded justification.

### D10. Routing artifacts are machine-generated — LOCKED-AMENDED
`hubs/*.md`, `index.md`, `log.md`, manifests: deterministic scripts from frontmatter + `page-manifest.json`; never in `ALLOWED_TARGETS`. DO-NOT-EDIT headers; human edits to generated files = needs_review + regenerate + report overwritten content.

### D11. Merge semantics and claim preservation — LOCKED-AMENDED
No-append rule: `merge_into` re-synthesizes the entire page; claims leave only via Contradiction Protocol or split child with link; ≤2 sentences of a linked page's scope restated. **Entity digest** (deterministic: numbers+units, dates, versions, config keys+values, code identifiers, API names, proper nouns; keyed to heading_path + source_ref). Entity present before, absent after, no Contradictions entry or split destination → needs_review (never hard fail). One table serves D11 and D18. Digest **deltas are logged per promotion to `log.md`** — the semantic changelog that keeps whole-page-rewrite diffs reviewable.

### D12. Contradiction protocol — LOCKED-AMENDED
Never blend into false consensus; never silently replace; standing claim stays, attributively phrased; structured YAML per dispute in `## Contradictions` with claim_ids; child bundles emit outbox drafts (`requires_human_review: true`); contradiction outranks merge (R7); resolution is human. Claim-level marking: `status: active` + `has_contradictions: true`; `contested` reserved for centrally disputed pages; `stale` reserved for source-hash drift. **Same-source supersession rule (v2.1, from F09):** conflicting values whose new source_ref is the *edited same source* are updates, never disputes; dated change language likewise signals update, not contradiction (the F01/F05 boundary — worded identically in both prompts).

### D13. Failure and retry policy — LOCKED-AMENDED
One retry with violations named (lower local temperature) → escalate if D14 permits → else quarantine to `manifests/needs-review.json`, continue queue. Never guess, never write unvalidated output. Structured failure records per event (unit, type incl. `concurrency_abort` and v2.1 `identifier_admission`, violations, retry count, flags) — raw material for V2. **Title-admission failures route here** (D24).

### D14. Escalation ladder and agentic escape hatch — LOCKED-AMENDED
Triggers: double lint failure; no clear retrieval winner or >6 serious candidates; mutation >3 pages; pack over local budget; contradiction touching canonical architecture decisions. Privacy gates: `allow_frontier_escalation=false` default (false → quarantine); secret scan + source privacy classification + affirmative config before any frontier call; logs carry hashes never text. Agentic escape hatch (taxonomy redesign, mass renames, migrations) human-supervised only; staging branch; full lint + full SQLite rebuild before promotion.

### D15. Model floor and hardware — CONSTANTS-HELD
Tested deployment profile, not law: 24–32B local instruct, quantized (~20–24 GB VRAM class), pack ≤ ~6.5–8k. Deployed model pinned in config, validated at V0/V4 (roadmap gate **M0** operationalizes this before any harness code). 7–8B permitted for control plane only on V0 pass; else inventory/summarization only. Locked part: identical filesystem behavior local and frontier.

### D16. Determinism — LOCKED-AMENDED
Tier 1 (byte-identical) only under pinned execution profile (model/tokenizer/build hashes, seed, sampling, backend, threads, prompt-pack hash). Tier 2 (structural) is the mixed-mode guarantee. Batch-order invariant conditional on D5 serialization (Stage-1 carve-out noted there). Token-counting authority: one pinned reference tokenizer in the linter. **v2.1:** the pack hash additionally covers the routing-identifier table version and admission-policy version (D24), so live demotion never silently changes packs.

### D17. Cache refresh — LOCKED-AMENDED
Surgical refresh (delete+reinsert changed chunks; re-embed changed text hashes; full rebuild always available, mandatory after escape-hatch ops). Chunks keyed `document_id + heading_path + ordinal + text_hash`; embeddings `text_hash + embedding_model`; transactional; failed refresh rolls back entirely.

### D18. Claims structure — LOCKED-AMENDED
Full semantic claims table deferred to Phase 2, gated on V2 evidence. MVP contradiction handling rests on the D11 entity digest: mechanical prefilter (same key different value; negation/status pairs; date/version conflicts), disappearance detection, stable claim_ids. R7 in-context detection on top.

### D19. Ingestion posture — LOCKED-AMENDED
Async batch locked. Cold-start staging: inventory → hubs → priority pages → long tail; **Stage 1 parallelizable per D5 carve-out**. Optional synchronous preview compile (writes nothing canonical). Queue state machine (v2.1 additions in brackets):

```text
queued → packed → decided → synthesized → linted → promoted
                     ↘ failed_retry → escalated | quarantined
promotion may → concurrency_abort → requeued (D2c)
[decided may emit residual → residual_pending → queued (on parent promoted)
                                              → discarded (on parent requeue/quarantine)]
```

### D20. Deterministic linter — LOCKED-AMENDED
Inventory as v2 (sentinels; frontmatter schema; cap; links; slug/alias dedupe; H3 depth; no-append; claim preservation; sources include source_ref; contradiction schema + outbox; link quota; junk-edge heuristic; orphans; stale drift; secret scan; generated-artifact drift; draft schema) **plus v2.1: summary hard lint; identifier admission checks; span structural validation; nomination-record schema.** Three severities: **hard_fail** (blocks promotion → D13), **needs_review** (quarantine/approval per config), **warning** (recorded, never blocks — includes proportional residual checks and summary warning tier). Only hard-fail-clean compiles promote; only fully clean compiles advance `source-manifest.json` silently.

### D21. Canonical frontmatter — LOCKED-AMENDED (v2.1: ownership matrix; enum reconciliation)

**Canonical field table (reconciles Blueprint drift: Blueprint's `type` is retired in favor of `page_type`; `status: current` → `active`):**

| Field | Values / form | Owner |
|---|---|---|
| title | string | **model** (create/split-child) then admission-gated (D24); harness preserves thereafter |
| summary | ≤160 chars, one line | **model**, sticky rule + admission checks (below) |
| tags | list | **model** |
| proposed_aliases | list, transport-only | **model proposes**; post-pass strips to needs_review queue; never promoted |
| page_type | concept \| hub \| draft \| contradiction \| source_summary | harness |
| status | active \| contested \| deprecated \| stale | harness |
| slug, aliases | normalized; alias table | harness/human per D24 |
| created, last_verified | dates | harness |
| sources, source_hashes | provenance | **harness** (union of prior + compile unit's source_ref; model never authors provenance) |
| related | derived from body wikilinks | **harness** (D10 consistency; model-authored `related:` retired) |
| origin, schema_version, compiler_version, has_contradictions | — | harness |

**Enforcement:** the model emits exactly its owned fields; the post-pass **discards** anything else and stamps authoritative values (warning records the attempt). Corruption of harness-owned fields is structurally impossible.

**Summary admission (named invariant exception).** Hard lint: present, single line, ≤ Part 0 cap, no markup/wikilinks, ≠ title verbatim, unique normalized. Warning tier: title-restatement, generic openers, DF-genericity, body-coverage. Stability: sticky-summary prompt rule; post-pass logs old→new deltas; change-without-heading-change → warning. Measurement: data-plane property fixtures (V0); summary-attributed misroutes (V2).

### D22. Naming and layout — LOCKED
Master Blueprint layout authoritative (`/sx-parent/`, `/sx-child/<slug>/`, `.sx/cache/index.db`). Path safety per D2b system-wide. Federation rules untouched: unidirectional promotion, human-gated drafts, no CRDTs, no child writes to parent `/wiki/`, Markdown + manifests as the only portable state. **v2.1 addendum:** two federation tiers — **consumer child** (read mount + reader contract + outbox drafts; no compiler) and **compiler child** (full bundle). Consumer children are the expected common case.

### D23. Promotion nominations (new in v2.1) — LOCKED
No `emit_draft` action. Compiler-children emit **deterministic promotion nominations** post-compile; consumer children's agents write OKF drafts directly (safe: quarantined, human-gated channel).

**Triggers:** (1) action = `contradiction`; (2) `create_page` into `promotion_policy.nomination_hubs`; (3) action targets a page whose `sources:` the projection manifest maps to `/vault/decisions/`, `/vault/glossary/`, or `/vault/incidents/` (the partial merge-blindness repair; remaining merge-blindness accepted, D11 digest-delta as the owned upgrade).

**Field derivation:** `claim_type` and `promotion_target` derived via configured maps (trigger 1 → contradiction; trigger 2 → hub_class_map; trigger 3 → path_target_map). **Never model-assigned.**

**Dedup key:** `hash(promotion_target + sorted(source_refs) + claim_type)` — titles excluded (unstable across recompiles).

**Rejection ledger:** `permanent` suppresses the key forever; `not_now` stores source content hashes at rejection and suppresses only while unchanged (deliberate hash sensitivity for exactly one class; the key stays hash-free).

**Upgrade path:** `page_type` grammar extension / LLM classifier only on V2/M4 evidence of noise or missed material. Accepted leak: `new_page.hub` is model-chosen, so the model implicitly gates its own pages' nomination — tolerable (filter set is config; hub assignments auditable on human-facing hub pages; nominations human-gated).

### D24. Routing identifier authority (new in v2.1) — LOCKED
`title`, `slug`, `aliases` are harness-owned; the model proposes, never installs. Rationale: identifiers feed exact anchors and steer future merges — free authorship is a self-reinforcing routing loop, including the prompt-injection variant.

- **Auto-admitted (harness):** deterministic title variants only (case/slug/punctuation normalization, singular/plural, trusted-import exact titles) — all still collision-checked.
- **Needs review:** model-proposed aliases (via `proposed_aliases` transport), source-derived nicknames, acronyms, abbreviations, synonyms.
- **Denied/softened:** generic terms, denylist, contested homonyms, multi-candidate identifiers, DF above threshold.
- **Contested-alias demotion, live:** evaluated at every anchor-table build (DF drifts; admission-time-only gates go stale); demoted aliases stay as softened candidates. Flapping accepted in v0 (mild consequence); hysteresis is the recorded fix.
- **Title-admission failure:** → D13 retry with the specific failure appended; persistent → quarantine. The harness never silently renames.
- Alias table: `UNIQUE(document_id, normalized_alias)` (per-document; global uniqueness rejected — see register); authority ∈ {human, harness, import}; anchor eligibility computed at build time, not implied by table presence.

---

## Part III — Rejected Register

| Rejected | Clarification |
|---|---|
| Option A: bespoke JSON patch harness | JSON fine for the tiny decision object; JSON-wrapped content/edits rejected |
| Option B: agentic CLI in the loop | Rejected for unattended canonical ingestion; valid as D14 supervised hatch and for **consumer-child reads** |
| Option C′: GBNF SEARCH/REPLACE + difflib | Grammar constrains shape, not anchoring; silent-corruption vector. Residual (D3) is admitted under the recorded input/output asymmetry |
| Large mutable canonical pages | Generated read surfaces explicitly allowed |
| `evidence` quotes in control JSON | Option A in miniature; traceability = D5 trace |
| Sentence-hash claim digests | False-positive storm under regeneration; entity digest supersedes |
| Per-page-type cap exceptions | Erodes D2's premise |
| Single-SQL RRF CTE | Python fusion, no SQLite version dependency |
| `status: stale` for contradictions | Namespace reserved for hash drift |
| LLM-written hubs/index/manifests | Foundational (D10) |
| Full semantic claims table in MVP | Entity digest bridges; Phase 2 on V2 evidence |
| CRDTs, hosted vector DBs, Postgres/Chroma, cloud sync | Per Blueprint |
| LangChain/LlamaIndex as runtime deps | Ideas may be reimplemented under local-first constraints |
| **Pre-control-plane decomposer** (v2.1) | Hidden second planner: duplicates the pack or decides without it; heuristic version has poor recall + false splits; leaked routing pre-emption |
| **Ordered multi-action control output** (v2.1) | Partial-failure semantics; ordering dependencies; discards single-call reliability |
| **`emit_draft` enum action** (v2.1) | Category error: promotion is a federation side effect, not a routing action; conflicts with mutually-exclusive enum |
| **Arbitrary model-authored source splitting** (v2.1) | Residual is the bounded, validated form |
| **Global `UNIQUE(normalized_alias)`** (v2.1) | Homonyms are legitimate (F08 premise); structural demotion solves the detectable case; F08 retained as defense-in-depth |
| **Model-authored `related:`** (v2.1) | Routing data must be machine-generated (D10); derived from body wikilinks |

**Deferred, not rejected (v2.1):** non-contiguous residual span lists (pending `mixed_scope_misplacement_rate`); hysteresis on DF demotion; `page_type` grammar extension; LLM promotion classifier; digest-delta merge nominations; cross-encoder rerank; full claims table.

---

## Part IV — Validation Gates

- **V0 — Golden corpus (precedes all compiler code).** Now ~25–30 fixtures across four kinds: control-plane, data-plane **property** fixtures, harness fixtures (retrieval, linter, admission, nomination ledger), fault-injection. Batch A (13) gates M0/M1; batch B completes coverage at M2. No harness change ships without green fixtures. Fixtures accumulate: every human correction during V2 becomes a fixture. Model admission (D15) runs here.
- **V1 — 30-query retrieval evaluation.** Hub-only vs BM25 vs vector vs RRF; run from compiler seat **and consumer seat** with tokens-per-answered-query; owns cosine thresholds, RRF k, weights, top-k, embedding model + prefix protocol, DF genericity threshold.
- **V2 — 50–100 file cold-start ingest.** Adds v2.1 metrics: misplacement rate, `residual_rate`, `span_fidelity`, residual reason distribution, residual retry/quarantine rates, `mixed_scope_misplacement_rate`, summary-attributed misroutes, wall-clock per compile unit, **qualitative-claim drift sampling** (the entity digest's named blind spot), correction time vs the pre-committed tolerance.
- **V3 — Link-quality audit.** Quota vs junk-edge warnings vs correction time.
- **V4 — Determinism smoke test.** Byte-identical under pinned profile; shuffled queue rejected/re-sorted; **property-stability repeat rule for data-plane fixtures**.
- **V5 — Corruption resistance.** Malformed outputs (incl. trailing prose outside sentinels, illegal/traversal paths, residual abuse) → zero canonical files changed; decision-validation failures must show **zero data-plane calls**.
- **V6 — Escalation privacy test.** Unchanged.
- **V7 — Page-fragmentation audit.** Unchanged; owns cap + segmentation trigger.
- **V8 — Recovery test.** Kill mid-run at each queue state incl. `residual_pending`; no partial writes; manifests not advanced; cache rebuild restores consistency; concurrency-abort path exercised.

Roadmap milestones M0–M4 sequence these (see implementation-roadmap.md).

---

## Part V — Implementation Hygiene (roadmap items)

As v2 (trace writer; tokenizer fixtures; failure records; queue machine; linter severity plumbing; DO-NOT-EDIT generation; entity-digest extractor; staging/path validator; concurrency check; profile pinning + pack hashing; deletion/rename handling) **plus v2.1:** sentence-marker renderer + span slicer; residual lifecycle in the queue machine; nomination emitter + rejection ledger; alias table + admission checker + live demotion; summary lint + sticky-delta logger; split-pair orchestration; `sx review` unified queue surface (nominations, quarantine, needs_review, alias proposals).

---

## Accepted Limitations & Labeled Uncertainty (v2.1)

1. **Residual contiguity:** interleaved multi-concept chunks lose non-contiguous members to the locked-contract loss mode; watched by `mixed_scope_misplacement_rate`.
2. **Merge-blindness (partial):** merges outside D23 trigger-3 paths never nominate; digest-delta upgrade owned.
3. **Qualitative-claim drift:** the entity digest cannot see claims without entities; V2 human sampling owns it.
4. **Semantic span failure:** no structural rule guarantees span placement; V0 fidelity fixtures + V2 metrics own it.
5. **Empirical unknowns no document can settle:** local-model wrong-action rate (M0), span fidelity in the wild, batch throughput, correction time. The v2 Lock Statement stands: remaining uncertainty is resolved by gates, not documents.

---

## Lock Statement

The spine is locked: atomic concept pages → whole-page regeneration through a two-plane compiler with residual re-enqueue → Python-owned validation with atomic, concurrency-checked, child-first-split promotion → machine-generated routing artifacts and harness-owned routing identifiers → deterministic promotion nominations → privacy-gated escalation → local-first Markdown as the only canonical state — all under the Judgment/Execution Boundary. Constants remain gate-owned. Further prose review is negative-yield; the next information arrives from M0.
