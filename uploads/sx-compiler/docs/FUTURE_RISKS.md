# FUTURE RISKS & SECOND THOUGHTS — v2

**Changelog vs v1:** dispositions applied per the 2026-07-06 round. Resolved items removed or transformed; API-era risks added; "remind later" items moved to the PROGRESS.md Deferred Reminders table (the ledger reminds; documents don't). v1 archived.

## Active risks

### R-A. Prompt injection via raw sources — MITIGATED-DEFERRED
Project-side now locked (amendment §9): `source_origin` classing + config-off injection lint. Model-side deferred deliberately — API-mode frontier models raise the injection-resistance baseline during the safe self-authored-corpus era. **Tripwire:** first observed meta-instruction in any source → flip the lint to needs_review for `third_party` origin; first third-party bulk import (web clippings etc.) → review this item BEFORE the import, not after.

### R-B. Fixture overfitting — MITIGATED, WATCH
Mechanisms: holdout reserve, provenance tags (`designed | correction | failure_record`), procedural tuning rounds, holdout rotation, gate-time paraphrase variants. **Tripwire:** visible green + holdout red, or designed-origin pass rate diverging above correction-origin pass rate → revert the tuning round.

### R-C. Overconfidence transfer at local re-entry (inversion of old #10) — OWNED
Frontier-M0 passing predicts nothing about local-M0; prompts will silently tune to frontier judgment. Owned by amendment §7: full accumulated corpus as the local admission exam, bootstrap-grade humility on return, delta logged. **Pre-commitment kept:** if local-M0 fails across two candidate models at re-entry, the local premise is revisited without a mourning period — the register survives either answer.

### R-D. Provider-side profile rot (transformed old #4) — OWNED
Model deprecations replace llama.cpp drift. Ritual: version string pinned; forced migration → rerun M0 + full fixtures under the new version → log profile → accept textual divergence (properties are the contract). **Tripwire:** provider deprecation notice → schedule the ritual before the sunset date, not after.

### R-E. API privacy posture — DECISION PENDING (Q-002)
Every pack transits a cloud API until re-entry. Structural controls in place (queue-admission gating of `private` sources, pre-pack secret scan, hash-only request logs). The remaining act is yours: provider + retention tier. **This is the last un-delegatable decision before W-001.**

### R-F. Cost creep — INSTRUMENTED
Throughput risk inverted: API is fast but metered. Caps in part0 (`max_cost_per_batch` hard-pauses), cost-per-unit traced, V2 reports it beside wall-clock, batch API for Stage 1. **Tripwire:** cost-per-unit trending up across batches without corpus growth → prompt/pack bloat audit.

### R-G. Agent-era operational risks — PLANNED (amendment §10)
Baton CI checker + secret scan (W-015); batch lockfile; human-hands-only instruction edits; `docs/archive/`. Residual exposure: you rubber-stamping a proposed diff that weakens anti-gaming rules — the protection is you actually reading proposed diffs to those files, which no mechanism replaces.

### R-H. Chunker quality — RESOLVED-INSTRUMENTED
Structural-first policy locked (amendment §8); `chunk_had_headings` trace annotation; V2 correlation decides whether anything smarter is ever justified. Semantic chunking and overlap are in the rejected register.

## Deferred (live in PROGRESS.md → Deferred Reminders; listed here for completeness only)
Review-queue starvation (trigger: Phase 2 start / any queue >2 weeks) · Garden maintenance & decay adjudication (trigger: M3 pass / hub >40 members / V1 probes degrading 2 months) · Git history pruning (trigger: `wiki-v1` tag) · M3 tolerance setting (trigger: Phase 3 entry) · Local re-entry checklist (trigger: local model prepared).

## Resolved this round
Vault language: English-only; multilingual hypothetical recorded in the decision log (would run unmodified; degraded FTS recall on inflection — trigram contingency covers it; English-centric embedding candidates — BM25 fallback covers it; digest declension noise; no breakage). · Small items: log rotation yearly (adopted); Obsidian skip-list (adopted, W-004); reader-contract version pin (adopted, Phase 4.1); POSIX-only declared pending Q-003 confirm; schema.md scope shrunk to bundle policy + version pins (decision log).

## Standing epistemics note (kept verbatim in spirit)
The remaining unknowns are empirical and gate-owned: API-model wrong-action rate (M0, imminent and cheap), span fidelity, cost-per-unit, correction time, and — deferred — local wrong-action rate at re-entry. No conversation settles these; the gates do.
