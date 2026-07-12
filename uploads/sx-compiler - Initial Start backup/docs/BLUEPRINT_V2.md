# Master Blueprint v2 — Local-First Federated LLM Wiki

**Status:** Supersedes the original Master Blueprint. This is the *outer architecture*: what the system is, its boundaries, and its federation model. The compiler's inner architecture lives in ADR v2.1; sequencing lives in the implementation roadmap. Where this document and the ADR overlap, the ADR wins.

## 1. What changed since v1, and why

The original Blueprint was written before the compiler existed as a design. Six of its positions have been superseded by later, better-argued decisions:

1. **The compiler is no longer a six-row table.** The two-plane compiler (ADR D2/D3) with residual re-enqueue is the system's center of gravity; the Blueprint's "Ingest: Python script calls selected LLM" row is fully replaced.
2. **The retrieval overlay is built in-process, not borrowed.** v1 said "adopt a qmd-like overlay." Compile-time retrieval turned out to be a compiler subsystem (exact anchors, ALLOWED_TARGETS, pack budgets, traces), which qmd cannot be load-bearing for. qmd survives only as an optional human-facing search tool.
3. **"CLI-first agent interface" is split in two.** Agentic tools are rejected for unattended canonical ingestion (ADR Part III, Option B) but embraced for supervised escape-hatch operations and for *reading* — consumer children are expected to be agentic models navigating the wiki.
4. **Federation gained a second tier.** v1's child bundle always carried a full compiler. v2 recognizes the common case: the **consumer child** (read mount + reader contract + outbox drafts, no compiler). Compiler children are for projects generating enough novel material to warrant their own synthesized wiki.
5. **"Child detects a parent-worthy insight" is no longer a hand-wave.** Deterministic promotion nominations (ADR D23) with a dedup key and rejection ledger replace it for compiler children; consumer children's agents write drafts directly.
6. **The frontmatter schema moved to the ADR and was reconciled.** v1's `type: page` and `status: current` are retired (`page_type`, `status: active`); `related:` is machine-derived; field ownership is a hard matrix (ADR D21). The v1 frontmatter examples in the original document are obsolete — do not copy them.

Everything else in v1 stands: Markdown + YAML as the canonical graph, SQLite as disposable derived cache, deterministic Python for lint/federation, git for versioning, human-gated unidirectional promotion, no CRDTs, no hosted vector DBs, no LangChain/LlamaIndex.

## 2. The system in one paragraph

A compiler ingests raw sources and maintains a structured, interlinked Markdown knowledge base ("the wiki") under a parent bundle. The wiki is both human-readable (any editor) and model-readable (capped pages, one-line summaries, machine-generated hubs/index). Projects consume the wiki through child bundles: usually read-only consumer children that can propose knowledge back through a human-gated drafts channel; occasionally full compiler children with their own synthesized wikis and deterministic promotion nominations. All model judgment is confined to two bounded calls per compile unit; a Python harness owns everything that touches disk or influences future routing. Inference is API-primary during development with a planned local re-entry; local-first refers to state, which never leaves disk except inside compile packs under the D14 queue-admission gates.

## 3. Non-negotiable rules (unchanged from v1, restated)

1. Child never writes to parent `/wiki/`.
2. Child never mutates parent `/vault/` except `/vault/drafts/`.
3. Parent never blindly imports child `/wiki/`.
4. Semantic conflicts are never auto-merged; resolution is a human act.
5. SQLite/vector cache is never synced as authoritative data.
6. Markdown and manifests are the only portable state.
7. (New, from the ADR) The Judgment/Execution Boundary: the model judges within a single call; the harness owns execution and every input that influences future routing.

## 4. Federation SOP (updated)

**Parent → child projection:** scope file (globs + tag excludes; the v1 DSL is simplified — start with globs), projection manifest with per-file hashes, copies into child `raw/`, optional read-only parent-wiki snapshots. **New: a `refresh` command** re-projects changed parent sources into a live child (v1 never addressed mid-project staleness).

**Consumer child (new tier, the default):** read mount or projection + the reader contract (routing, trust semantics for `status`/`has_contradictions`, provenance rule, contribution path) + write access to `outbox/drafts/` only. No compiler, no calibration, no schema pinning beyond the reader contract version.

**Compiler child:** full bundle; same compiler binary and prompts as the parent; nominations per ADR D23; drafts land in the parent's human-review channel; OKF link rewriting at export.

**Promotion:** human reviews drafts/nominations → promotes into `/vault/` → parent export pipeline copies into `/sx-parent/raw/` → parent compiler updates the wiki → future projections inherit. Unchanged from v1.

**Simplification note:** on a single machine, the outbox → sync-script hop may be collapsed to a direct write-allow on `/vault/drafts/`; keep the outbox when children live elsewhere.

## 5. Cold start (updated)

Four stages stand: inventory summaries → hubs → priority pages → long tail. Two refinements: Stage 1 is parallelizable (ADR D5 carve-out); all corpora are disposable until the M3 gate passes — the first retained wiki is the M3 artifact. Full procedure: INGESTION.md.

## 6. Verification (updated)

The deterministic linter (ADR D20) carries the v1 inventory plus: summary lint, identifier admission, span validation, nomination schema, secret scan, generated-artifact drift. Validation is gate-structured (V0–V8 → milestones M0–M4), not a final phase.

## 7. What still needs planning (honest list)

These are the known-open items, all human decisions rather than architecture:

1. **Initial hub taxonomy** — the starting set of hubs for *your* vault's domains (schema.md, Phase 0). The four nomination hubs are configured; the full topical set is not.
2. **Part 0 constant values** — defaults exist; your operating points come from gates.
3. **Vault dialect confirmation** — Obsidian vs Logseq decides whether normalization machinery exists at all.
4. ~~Vault language~~ — resolved: English-only (2026-07-06). Hypothetical multilingual behavior recorded in the decision log.
5. **Backup discipline for the retained wiki** — git is versioning, not backup; offsite strategy is a human process decision.
6. **Review UX** — `sx review` (unified queue surface) is specified as hygiene; its ergonomics will determine whether the human gate stays healthy.
7. **Multi-machine story** — deferred deliberately; everything assumes one machine until it doesn't.

## 8. Document map

| Concern | Document |
|---|---|
| Inner architecture (all decisions) | ADR_v2.1.md |
| Sequencing, gates, kill criteria | implementation-roadmap.md |
| Prompts | V0 corpus doc §2 (control) + data-plane-synthesis-prompt.md |
| Fixtures | v0-golden-corpus doc + fixture-batch-A.md |
| Layout | STRUCTURE.md |
| Ingestion | INGESTION.md |
| Testing | TESTING.md |
| Agent workflow | CLAUDE.md / AGENTS.md / AUDIT.md / PROGRESS.md |
| Onboarding a fresh model | PROJECT_PRIMER.md |
| Known risks | FUTURE_RISKS.md |
