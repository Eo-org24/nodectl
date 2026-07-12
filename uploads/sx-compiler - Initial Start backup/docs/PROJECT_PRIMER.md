# PROJECT PRIMER — sx: Local-First Federated LLM Wiki

**Dual purpose:** the general project overview, AND the onboarding document for any fresh model/chat continuing this work. If you are a model reading this cold: this file plus the reading order below is your complete priming path.

## What this project is (three paragraphs)

**sx** is a Karpathy-style LLM wiki: an LLM acts as a *compiler* that ingests raw personal notes and synthesizes a structured, interlinked Markdown knowledge base. Plain Markdown + YAML frontmatter is the only canonical state; SQLite/FTS/vectors are disposable acceleration; deterministic Python owns everything that touches disk. The wiki serves double duty — human-readable in any editor, and machine-readable as token-efficient working memory for models doing project work.

The compiler is a **two-plane** design. In the current development profile, inference is API-primary, with local 24–32B-class inference retained as the planned return target. A constrained *control plane* routes each source chunk (merge / create / split / contradiction / discard, plus an optional *residual* span for multi-concept chunks), and a *data plane* regenerates complete capped pages between sentinels. Nothing the model emits touches canonical paths without mechanical validation, staging, and atomic promotion. The governing invariant remains model-independent: **the model judges within a single call; the harness owns execution and every input that influences future routing.**

Federation is parent/child with a human gate: the parent bundle holds the canonical wiki; projects consume it as *consumer children* (read + human-gated drafts out, no compiler) or *compiler children* (own synthesized wiki + deterministic promotion nominations). Unidirectional, no CRDTs, no auto-merge of meaning. The project is currently at the end of its design phase: architecture locked, prompts drafted, first fixture batch specified, implementation not yet begun.

## State of play (as of 2026-07-07)

- **Locked:** ADR v2.1 — all 24 decisions + the invariant + v2.2 amendment (API-primary inference, local re-entry planned). Do not relitigate; the register records why every alternative died.
- **Drafted, human-approved:** roadmap (gates M0–M4, walking skeleton, kill criteria); control-plane + data-plane prompts; fixture batch A (13); agent workflow (CLAUDE/AGENTS/AUDIT/PROGRESS).
- **Decided since the API-mode round:** Q-002 selects DeepSeek API with `api.model = deepseek-v4-pro` as the cost-first starter provider; POSIX-only platform posture; Q-001b selects Obsidian-flavored Markdown as the primary vault dialect. No Logseq/outliner normalization is required for W-001–W-005 or M0/M1; a deterministic, config-gated, non-LLM pre-ingest normalization adapter remains allowed later only if real imported/outliner sources appear.
- **Pending:** all code (starts at W-001 in PROGRESS.md); fixture batch B; remaining Part 0 operating values/cost caps; reader-contract finalization (Phase 4.1); `schema.md` assembly from the prompt docs.

## Reading order for a fresh model

1. This file.
2. `BLUEPRINT_V2.md` — outer architecture + what superseded v1.
3. `ADR_v2.1.md` — skim Part 0 + the invariant + D1–D5, then treat the rest as reference (grep D-numbers on demand).
4. `implementation-roadmap.md` — phases, gates, current position.
5. Then only what the task needs: prompts docs for prompt work; fixture docs for fixture work; STRUCTURE/GETTING_STARTED for repo work; PROGRESS.md always, for current state.

**Do not load:** the original Master Blueprint, ADR v2, or the standalone lockdown — all superseded and merged; loading them reintroduces reconciled drift (e.g., the retired `type:`/`status: current` fields).

## Vocabulary (the ten terms that carry everything)

**compile unit** — one chunk moving through the pipeline · **pack** — the budgeted retrieval context for one unit · **exact anchor** — title/slug/alias hit; preferred candidate, never automatic · **residual** — control-plane-flagged leftover span, harness-sliced, re-enqueued · **entity digest** — deterministic per-page table of numbers/dates/identifiers; claim preservation + contradiction prefilter · **promotion** — atomic rename from staging into canonical paths · **nomination** — deterministic promotion candidate from a compiler child · **generated read surface** — hubs/index/log/manifests; machine-written, never in ALLOWED_TARGETS · **bootstrap mode** — uncalibrated first-ingest conservatism (create-biased) · **gate** — validation milestone that owns constants (V0–V8 / M0–M4).

## Rules for continuing this project in a new chat

1. **Locked means locked.** Proposals that reopen ADR decisions need new *evidence* (a gate metric, a failed fixture), not new arguments. The review phase ended with two consecutive rounds of purely mechanical findings — further prose review is negative-yield.
2. **Numbers are not sacred; structure is.** Part 0 constants are meant to move via their owner gates.
3. **The style of this project is adversarial review with recorded dispositions.** New documents get a changelog against what they supersede; rejected ideas go to the register with reasons; accepted limitations get named and assigned a watching metric.
4. **When in doubt about current state, trust PROGRESS.md over any document** — documents freeze; the ledger moves.
5. **The empirical unknowns cannot be settled by conversation:** local-model wrong-action rate (M0), span fidelity, batch throughput, correction time. If asked to speculate on these, say they're gate-owned and help run the gate instead.
6. **Do not relitigate Option B on "you're on frontier now" grounds.** The two-plane design's properties are model-independent (amendment §1); agentic ingestion remains rejected for the unattended loop.
7. **Do not reopen vault dialect unless real source evidence requires it.** The active dialect is Obsidian-flavored Markdown. Logseq/outliner normalization is out of scope for W-001–W-005 and M0/M1. A future adapter may exist only as deterministic, config-gated pre-ingest normalization; it must not change compiler routing or synthesis contracts.

## The one-message priming block (paste this into a new chat along with the docs)

> Continue the sx project (local-first federated LLM wiki compiler). Architecture is LOCKED in docs/ADR_v2.1.md under the Judgment/Execution Boundary invariant, running API-primary inference with planned local re-entry under ADR_v2.2; selected starter API provider is DeepSeek with `api.model = deepseek-v4-pro`; primary vault dialect is Obsidian-flavored Markdown, with no Logseq/outliner normalization in scope for W-001–W-005 or M0/M1. Sequencing is in docs/implementation-roadmap.md; live state is in PROGRESS.md. Read PROJECT_PRIMER.md first and follow its reading order and rules — especially: don't relitigate locked decisions, don't load superseded documents, and route empirical questions to their owner gates. Current task: <fill in>.