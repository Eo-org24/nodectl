# PROGRESS — sx-compiler inter-agent ledger

<!-- PROTOCOL (read once, then obey):
  - This file is the ONLY channel between builder and auditor. Humans read it too.
  - Sections 1–4 are EDIT-IN-PLACE (keep current). Sections 5–6 are APPEND-ONLY.
  - Never delete or rewrite another agent's entries. Corrections are new entries.
  - Update the baton LAST, after your commit is pushed.
  - States: backlog → building → built, awaiting audit → audited-pass | audited-fail → done (human ack)
-->

## 1. Status header  (edit in place)

- **Active phase:** Phase 0 — Preconditions (roadmap)
- **Next gate:** M0 — model admission (fixture batch A vs pinned API model; runnable after W-003 + API key)
- **Inference mode:** api (ADR v2.2 amendment) — local re-entry planned, checklist in amendment §7
- **Baton:** builder
- **API configured:** selected (DeepSeek API; api.model = deepseek-v4-pro; key via env)

## 2. Work items  (edit in place; keep sorted: active first)

| ID | Title | Spec refs | State | Notes |
|---|---|---|---|---|
| W-001 | Repo scaffold: pyproject, package skeleton, part0.yaml with ALL Part 0 defaults **incl. api.* rows, ingest.skip list, cost caps, source_origin field**, .gitignore | STRUCTURE.md; ADR Part 0 + v2.2 §6 | built, awaiting audit | scaffold implemented; Q-002 resolved in decision log and applied via `api.model: deepseek-v4-pro` |
| W-002 | Fixture runner: YAML loader, pack renderer, band→number mapping, scoring, --repeat (decision-stability recording), --harness-only, **cost logging** | corpus §1–3; batch A notes; v2.2 §11 | backlog | blocked by W-001 |
| W-003 | Encode fixture batch A under fixtures/batch_a/ (expected blocks read-only thereafter; **provenance tag: designed**) | fixture-batch-A.md | backlog | blocked by W-002; M0 runnable after this |
| W-004 | Change detection + hashing + deletion/rename + **skip-list + source_origin recording** | ADR D5; v2.2 §6/§9 | backlog | blocked by W-001 |
| W-005 | Chunker per **structural-first policy** (heading-bounded, no overlap, fragment-merge, chunk_had_headings trace flag) + sentence markers | ADR D5; v2.2 §8 | backlog | blocked by W-001 |
| W-006 | SQLite cache schema + FTS two-pass ladder + surgical refresh | ADR D6, D17 | backlog | blocked by W-001 |
| W-007 | Anchor table (titles+slugs, Phase 1 scope) + pack assembly + trace writer | ADR D5, D24 partial | backlog | blocked by W-005, W-006 |
| W-008 | Control-plane call: **provider structured-output** decision object (GBNF module stubbed for local re-entry), prompt loading, decision validation | ADR D3 + v2.2 §4 | backlog | blocked by W-007 |
| W-009 | Data-plane call: directives, strict sentinel parse (FI-01c), split-pair orchestration, **transport backoff layer invisible to D13** | ADR D2e; v2.2 §5 | backlog | blocked by W-008 |
| W-010 | Entity-digest extractor (enforcement warning-tier) + delta logger | ADR D11/D18 | backlog | blocked by W-005 |
| W-011 | Linter: hard-fail subset + summary hard lint + severity plumbing + **injection lint stub (config-off, warning)** | ADR D20/D21; v2.2 §9 | backlog | blocked by W-009 |
| W-012 | Staging, path validation, atomic promotion, concurrency check | ADR D2a–c | backlog | blocked by W-011 |
| W-013 | Queue state machine + serialized loop + generated artifacts + postpass stamping + **held_private queue-admission filter + .batch-running lockfile** | ADR D19, D10, D21; v2.2 §2/§10 | backlog | blocked by W-012 |
| W-014 | `sx` CLI: status / ingest / lint / rebuild | STRUCTURE.md | backlog | blocked by W-013 |
| W-015 | Workflow guards: baton-consistency CI check + repo secret scan | v2.2 §10; AUDIT.md item 0 | backlog | blocked by W-001; small, can interleave |

<!-- M0 requires: W-001..003 + api.model configured. M1 requires: W-001..015 green + roadmap Phase 1 exit procedures. -->

## 3. Open questions for the human  (edit in place; answers go to §6)

- Push local commit `1db5e72` from the host environment. Builder-side push is blocked in the sandbox because this Git setup lacks the HTTPS transport helper (`git remote-https`), so baton handoff to auditor cannot be completed from inside the agent session.

## 4. Deferred reminders  (edit in place; check triggers at every phase transition)

| Reminder | Trigger | Source |
|---|---|---|
| Elevate `sx review` ergonomics to first-class | Phase 2 start, or any human queue >2 weeks old | Risk R (v1 #5) |
| Adjudicate garden maintenance + decay properly | M3 pass, or any hub >40 members, or V1 monthly probes degrading 2 months running | v1 #6 |
| Decide git pruning policy for bundle repos | `wiki-v1` tag | v1 #7 |
| Set M3 correction-time tolerance in part0 | Phase 3 entry (BEFORE selecting the corpus) | roadmap kill criteria |
| Run local re-entry checklist | local model prepared | v2.2 §7 |
| Review injection lint posture before any third-party bulk import | first import of non-self-authored material | FUTURE_RISKS R-A |

## 5. Done log  (append-only)

<!-- [date] W-xxx <builder|auditor> — what; deviations (why); assumptions; commit(s). -->
[2026-07-07] W-001 builder — Added the Phase 0 repo scaffold: `pyproject.toml`, `.gitignore`, `part0.yaml`, package/layout skeleton, minimal `sx.config` Part 0 loader, minimal `fixtures/runner.py --harness-only` entrypoint, and unit tests covering config loading plus harness-only success. Deviations: added the smallest deterministic loader/runner implementation now because the builder protocol requires `pytest` and `python fixtures/runner.py --harness-only` to pass on this item, and pure empty scaffolding would not satisfy that contract; used repo-local `.venv` commands because the shell environment exposes Python tooling there rather than system-wide; push not completed because the sandbox Git lacks the HTTPS transport helper, so the human must push from the host before baton handoff. Assumptions: set `m3_correction_time_tolerance_minutes: 15` conservatively as the required pre-committed placeholder, and recorded DeepSeek retention as `standard` per the answered Q-002 note. Commit(s): `1db5e72` (`builder(W-001): scaffold the compiler repo`).

## 6. Decision log  (append-only)

[2026-07-06] Project initialized. Docs frozen at ADR v2.1 / roadmap v1 / batch A v1.
[2026-07-06] **API mode adopted** (ADR v2.2 amendment): API-primary inference, local as return target; D15 pivot taken preemptively on velocity grounds; privacy gates re-scoped to queue admission. All other architecture unchanged.
[2026-07-06] Vault language: **English-only.** Multilingual hypothetical recorded: system would run unmodified in Polish with degraded FTS recall (trigram contingency covers), English-centric embedding candidates (BM25 fallback covers), digest declension noise; no breakage. No adjustments made or planned.
[2026-07-06] Chunking policy locked: structural-first, heading-bounded, no overlap, fragment-merge; semantic chunking + overlapping windows → rejected register (v2.2 §8).
[2026-07-06] schema.md scope decision: bundle-side policy + version pins only (hub taxonomy, schema/prompt-pack/reader-contract versions, parent-worthiness guidance); zero rule-text duplication from ADR/prompts — pointers only. Prevents drift-by-duplication.
[2026-07-06] Fixture anti-overfit set adopted: holdout reserve + provenance tags + procedural tuning rounds + holdout rotation + gate-time paraphrase variants (TESTING.md; FUTURE_RISKS R-B).
[2026-07-06] Small-item dispositions: yearly log rotation; Obsidian skip-list into W-004; reader-contract version pin at Phase 4.1; POSIX-only pending Q-003.
[2026-07-07] Q-002 answered: API provider = DeepSeek API; api.model = deepseek-v4-pro; retention_tier = standard DeepSeek API retention / no zero-retention tier confirmed. This is a cost-first development choice for W-001–W-003 and M0. Private/credential sources remain excluded by the API-mode queue-admission gate; real vault ingestion should not proceed on DeepSeek unless the human explicitly accepts the provider privacy posture.
[2026-07-07] Q-001b answered: Obsidian-flavored Markdown is the primary vault dialect. No Logseq/outliner normalization is required for W-001–W-005 or M0/M1. A deterministic pre-ingest normalization adapter remains allowed later if real imported/outliner sources appear; it must be config-gated, non-LLM, derived/disposable, and must not alter compiler routing/synthesis contracts.
[2026-07-07] Q-003 answered: POSIX-only. Official platform posture is Linux/macOS/WSL2.
[2026-07-07] Agent sandbox posture adopted: builders/auditors may use repo-local `.venv` tooling but must not run sudo, apt, or system package managers. Missing host dependencies are human-provisioned. Preferred execution is a dedicated non-sudo OS user with access only to sx-compiler and repo-scoped Git credentials. Agents must not request unrestricted Git/network access to compensate for sandbox tooling gaps. If `git push` fails because a transport helper or credential is missing, stop and report the exact failure. The human either pushes manually or provisions a repo-scoped Git transport for the dedicated agent user.