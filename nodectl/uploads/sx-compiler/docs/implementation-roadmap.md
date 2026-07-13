# Implementation Roadmap — Local-First Federated LLM Wiki

**Status:** DRAFT for confirmation.
**Governing documents:** Master Blueprint, ADR v2, OQ1–OQ3 Lockdown (confirmed), V0 Golden Corpus doc.
**Prime risk being managed:** project mortality. The full decision register is months of solo work; this roadmap sequences it so every phase ends with something that runs, and no phase depends on work that only pays off two phases later.

## Operating principles

1. **Gates, not dates.** Phases exit through validation gates (the ADR's V-gates mapped to milestones M1–M4). Calendar estimates are provided for planning honesty but nothing unlocks by time.
2. **Everything is disposable until M3.** All corpora compiled before the M3 gate passes are throwaway copies of vault material. The first *retained* wiki is the M3 artifact itself. This is what makes shipping a skeleton without residual, vectors, or full admission machinery safe.
3. **Selection rule applies to sequencing too.** The most deterministic components (harness, linter, fixtures) are built before the judgment-dependent ones (threshold calibration, prompt tuning), because deterministic components don't rot while later work proceeds.
4. **No harness change ships without green fixtures** (V0 discipline) — the fixture runner is therefore the *first* code written, not an afterthought.

---

## Phase 0 — Preconditions (≈1 week of evenings)

Everything needed before compiler code exists.

**In scope:**
- Repo scaffold per Blueprint layout; Part 0 config file (page cap, chunk size, band constants placeholder, DF threshold, denylist, nomination hubs, pinned execution profile skeleton).
- Vault dialect confirmation; if Obsidian-flavored, formally delete the Logseq normalization step from scope.
- `schema.md` v1: control-plane prompt (drafted — corpus doc §2), data-plane synthesis prompt (to write), sticky-summary rule, contradiction phrasing protocol, frontmatter template with the **ownership matrix** (companion-queue item 1) and the reconciled `type`/`page_type`/`status` enums (item 2) — these must exist before the post-pass is coded, so they land here.
- **Fixture runner**: loads YAML fixtures, renders packs, calls the model, scores per §3 of the corpus doc (bands→numbers mapping lives here). Runs against the pinned API model.
- Fixture batch A (the M1 set, ~12 — see manifest below).

**Exit gate — M0 (model admission):** the pinned API model (part0 `api.model`) passes fixture batch A via the provider's structured-output mechanism, `--repeat 2`, decision-stability rate recorded. Runs as soon as W-003 and an API key exist. (Local-model M0 re-runs at re-entry — amendment §7.)

## Phase 1 — Walking Skeleton (≈2–3 weeks)

Parent-only, throwaway corpora, minimum vertical slice that ingests → routes → synthesizes → validates → promotes.

**In scope:**
- Change detection (source hashing vs manifest), chunking with sentence-marker rendering.
- **FTS/BM25-only retrieval** (the sanctioned embeddings-off fallback): exact anchors on **titles + slugs only**, BM25 candidates, 1-hop link expansion, budgeted pack. No vectors, no RRF (degenerate single-list ordering), no alias table.
- Control call (grammar includes the `residual` field for forward-compatibility; **harness discards any non-null residual with a logged warning** — prompts and fixtures don't change when residual lands in Phase 2).
- Data call with sentinel parsing; post-pass stamps harness-owned frontmatter per the ownership matrix and derives `related:` mechanically (companion item 3).
- **Entity digest: extraction yes, enforcement warning-only.** Extraction is pure deterministic Python and is required for D12 contradiction packs to exist at all; the claim-preservation check (disappearance → needs_review) runs but only warns. This split lets contradiction routing work in the skeleton without betting the phase on digest completeness.
- Reference tokenizer authority (needed for `target_state` / R5).
- Linter hard-fail subset: sentinels, frontmatter schema, page cap, path safety, broken links (with the exactly-one-match autofix), **summary hard lint**; plus slug/title collision as a hard check with **quarantine on failure** (the D13 retry ladder is Phase 2 — skeleton failure handling is quarantine-only).
- Staging → atomic rename promotion; D2c optimistic concurrency hash check (a few lines, cheap insurance).
- Machine-generated index, hubs, `log.md` append, manifests; surgical SQLite refresh per unit (D17); serialized queue with the D19 state machine reduced to `queued → compiling → promoted | quarantined`.

**Explicitly deferred:** vectors, residual mechanics, alias table + admission tiers, D13 retry ladder, escalation, rename semantics, preview compile, warning-tier summary lint, nomination machinery.

**Exit gate — M1 (determinism smoke + corruption resistance):**
- Same queue, two runs, pinned profile → identical control-plane decisions (Tier 1); canonical outputs identical or variance documented (Tier 2). (Tier 1 N/A until local re-entry; record decision-stability instead)
- Fault-injection fixtures (malformed sentinels, illegal paths, cap breach, schema violations) → **zero canonical files changed**, all failures quarantined with structured records (V5 discipline).
- Recovery: delete `.sx/cache/`, rebuild from Markdown, content hashes match (V8-lite).
- Fixture batch A still green.

## Phase 2 — Retrieval Calibration + Residual (≈2–3 weeks)

Still throwaway corpora. This phase turns the skeleton into the full ADR compiler.

**In scope:**
- Vector pass + RRF fusion (single-SQL CTE); threshold calibration mapping bands to numbers (owner-gated Part 0 constants).
- Alias table + admission tiers + live contested-alias/DF demotion; title-admission failure → **full D13 retry ladder** (retry with failure appended → quarantine).
- Residual re-enqueue complete: span validation, slice-before-synthesis, lifecycle coupling, derived refs, depth cap.
- Entity-digest enforcement promoted from warning to its D20 severity; digest-delta lines in `log.md` (the semantic changelog).
- Warning-tier summary lint (title-restatement, generic openers, DF-genericity, body-coverage).
- Fixture batch B → full V0 corpus (~25–30, manifest below), including data-plane property fixtures.

**Exit gate — M2 (retrieval evaluation, V1):**
- 30-query set (10 exact / 10 cross-document synthesis / 10 vague discovery) comparing hub-routing-only vs BM25-only vs vector-only vs fusion — run from both the compiler's seat and the **consumer's seat**, with tokens-loaded-per-answered-query recorded.
- H1 (code-identifier retrieval) green; `fts-misses.log` reviewed for the trigram decision (D6).
- Full V0 corpus green. **Decision point:** if fusion does not beat BM25-only by the Part 0 margin, vectors are cut from the critical path (kept as config-off) — a simplification win, not a failure.

## Phase 3 — First Retained Ingest (≈1–2 weeks calendar; mostly batch runtime + review)

The real vault, staged cold start, and the gate that decides whether the wiki goes live.

**In scope:**
- Staged cold start: Stage 1 per-source inventory summaries with the **parallelism carve-out** (companion item 4 — summaries mutate no shared graph state; determinism invariant applies to graph-mutating units only); Stage 2 hub generation; Stage 3 priority pages; Stage 4 long tail, async.
- Wall-clock per compile unit measured from the first batch (the throughput unknown, finally quantified).
- Human review workflow: correction time per page logged; every correction converted into a V0 fixture (the accumulating-corpus loop); **qualitative-claim drift sampling** (companion item 5) alongside entity-based checks.

**Exit gate — M3 (cold-start test + link-quality audit, V2):** on 50–100 representative files —
- pages per source, duplicate-concept rate, orphan rate, stale-page rate within Part 0 tolerances;
- cost per compile unit;
- misplacement rate, `residual_rate`, `span_fidelity`, reason distribution, summary-attributed misroutes recorded;
- link-quality audit: broken links zero, orphans zero-or-explained, link density sane, hub membership spot-checked;
- **median human correction time per page below the tolerance you set before the run** (set it in Part 0 now, not after seeing results).
Failing the gate is expected once: tune `schema.md`, discard the corpus, rerun on a fresh copy. The run that passes is **the** wiki — retained from that point on.

## Phase 4 — Federation (≈2 weeks)

**In scope, in order:**
1. **Consumer-child tier first** (cheap, immediately useful): reader contract finalized (companion item 6; outline exists), projection script with glob/exclude scope file, projection manifest with hashes, `refresh` command for mid-project re-projection, outbox drafts channel. A real project should start consuming the wiki here — this is also live V1 consumer-seat data.
2. **Compiler-child tier:** nomination machinery (triggers, configured maps, dedup key, two-class rejection ledger), OKF link rewriting at export, lineage-divergence lint (child schema pinned vs parent evolved), secret-scan on the promotion path.

**Exit gate — M4 (federation round-trip):** one full cycle on a real project — project → child consumes → nominations/drafts emitted → human promotes one draft → parent re-ingests → a fresh child projection inherits the promoted knowledge. Exclusion rules verified (private/credential tags never cross the boundary).

---

## Fixture manifests

**Batch A (M0/M1 gate, ~12):** F01 exact-anchor merge; F03 + F03b (R2 calibrated + bootstrap suppression); F04 sibling branch; F05 contradiction (digest extraction present); F06 discard; F07 split at cap; F09 stale re-ingest; H1 code-identifier retrieval; H2 hub drift; 2× fault-injection (malformed sentinels, illegal path); 1× data-plane property fixture (frontmatter/cap/links/summary hard lint).

**Batch B (M2 gate, to ~25–30 total):** F02 alias merge; F08 acronym collision; F10 ×3 residual variants + interleaved-concept accepted-loss fixture; residual-null abuse; H3 span validation; H4 contested-alias demotion; H5 nomination trigger/dedup/ledger (deterministic — cheap); title-admission failure → retry → quarantine; bootstrap variants F04b/F05b; second contradiction type (date/version conflict); split-section selection among multiple headings; escalation trigger (two equally plausible targets); discard boundary pair (near-durable logistics; boilerplate duplicate vs first occurrence); further data-plane property fixtures (digest preservation, sticky summary).

## Kill / pivot criteria (decided now, while calm)

- **M0 fails across two candidate local models** → D15 pivot: control-plane-only on the small model with data plane escalated, or revisit the local-first constraint consciously. Do not start Phase 1 on a model that can't route. — taken preemptively 2026-07-06 (velocity); inverse risk (overconfidence transfer) owned by amendment §7.
- **M2: fusion ≤ BM25 + margin** → cut vectors from critical path permanently (config-off).
- **M3: median correction time above tolerance after two schema.md tuning rounds** → stop coding entirely; the problem is editorial policy, not machinery. Prompt work only until a rerun passes.
- **Any phase exceeding 2× its estimate** → cut scope to the gate's minimum, ship the gate, move on. The backlog exists so deferral is cheap.

## Backlog (only-if-earned; each entry names its justifying metric)

| Item | Unlocking evidence |
|---|---|
| Hysteresis on DF demotion | V2 shows alias flapping causing routing instability |
| Non-contiguous span lists | `mixed_scope_misplacement_rate` material at M3 |
| `page_type` grammar + LLM promotion classifier | nomination list noisy or missing material (M4+) |
| Digest-delta merge nominations | merge-blindness confirmed costly in practice |
| Escalation ladder w/ privacy-gated frontier | quarantine rate high on cases a frontier model demonstrably fixes |
| Preview compile | human demand during Phase 3 review |
| MCP exposure; qmd as human search overlay | consumer-child usage patterns ask for it |
| Rename semantics via git detection | spurious stale-marks observed on real renames |

## Companion-queue placement (all seven items homed)

Ownership matrix + enum reconciliation → Phase 0 (`schema.md`). `related:` derivation → Phase 1 post-pass. Stage-1 parallelism carve-out → Phase 3. Qualitative-drift label + sampling → Phase 3 / M3 metrics. Reader contract → Phase 4.1 (draft exists). Walking-skeleton milestone → this document (Phase 1/M1).

## Honest estimate

Phases 0–2: ~5–7 weeks of solo evenings. Phase 3: dominated by batch runtime and review sittings, not coding. Phase 4: ~2 weeks. **~2.5 months to a federated system with a retained wiki** — with the caveat that these estimates are the least-reviewed numbers in the entire document chain, which is precisely why the kill criteria above are scope-cuts rather than schedule-slips. API mode shortens Phase 0–2 (no local serving setup; M0 immediate after W-003) and converts the throughput unknown into a cost unknown — both measured, not guessed.
