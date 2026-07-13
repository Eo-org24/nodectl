# AGENTS.md — sx-compiler

You are working on **sx**, a local-first LLM wiki compiler. Architecture is LOCKED in `docs/ADR_v2.1.md`; sequencing in `docs/implementation-roadmap.md`; layout in `docs/STRUCTURE.md`. You never relitigate locked decisions. If the spec seems wrong or ambiguous, record it in `PROGRESS.md` → Questions and either proceed with the most conservative reading (stating your assumption in the work-item notes) or stop if the ambiguity is load-bearing.

## Your default role: BUILDER (fire-and-forget chunks)

You are given one work item (`W-xxx`) at a time — from the human directly or from PROGRESS.md → Backlog (top unblocked item). A work item is done when ALL of:

1. The code implements exactly the item's scope — no more. Adjacent improvements you notice become PROGRESS.md backlog suggestions, not commits.
2. `pytest` green; `python fixtures/runner.py --harness-only` green; model fixtures run too if the item touches prompts/grammar/pack rendering and a model endpoint is configured (`part0.yaml → api.model + key env`), otherwise note "model fixtures not run — no endpoint".
3. You added unit tests for the new code (see `docs/TESTING.md` layer 1). Fixtures you may **add**, never modify.
4. Docstrings map code to ADR decisions ("Implements D2c").
5. `PROGRESS.md` updated per its protocol: item status → `built, awaiting audit`, Done-log entry (what/how/deviations/assumptions), Questions if any arose, **baton → auditor**.
6. Committed and pushed: one logical commit (or few, each coherent), message `builder(W-xxx): <imperative summary>`. No force-push, no history rewriting, single `main`.

## Hard rules

- **Never edit:** `docs/ADR_v2.1.md`, `docs/implementation-roadmap.md`, `CLAUDE.md`, `AGENTS.md`, `AUDIT.md`, fixture `expected`/`must_not` blocks, `audits/*` (auditor territory), other agents' Done-log entries.
- **Never weaken a test or fixture to make it pass.** If a fixture seems wrong, PROGRESS.md → Questions; the human arbitrates. This is the single most important rule in this file.
- **Never touch data bundles** (`/vault`, `/sx-parent`, `/sx-child*`).
- If `.batch-running` exists at repo/bundle root, stop — a compile batch owns the machine; tell the human.
- Numbers live in `part0.yaml` only — never hardcode a constant.
- Edits to CLAUDE.md/AGENTS.md/AUDIT.md/spec docs: propose exact diffs in PROGRESS → Questions only; the human applies them. Never apply such edits yourself, even if approved in chat.
- Model calls exist only in `sx/control_plane.py` and `sx/data_plane.py` (Judgment/Execution Boundary).
- Respect the **baton**: build only when it reads `builder` (or `any`). Never run concurrently with the auditor.
- Dependencies: stdlib-first. Adding a dependency requires a PROGRESS.md question UNLESS it is on the pre-approved list: `pyyaml`, `pytest`, `hypothesis`, `numpy` (Phase 2), `llama-cpp-python` or an OpenAI-compatible client for the local endpoint.
- Secrets/tokens never in code, config, or commits. Git auth comes from the environment.
- Agents must not run `sudo`, `apt`, `dnf`, `pacman`, system package managers, or system-wide installers. If host tooling is missing, stop and report the exact missing command/package. The human provisions the host. Agents may use only repo-local tooling such as `.venv`.
- Agents must not request unrestricted Git/network access to compensate for sandbox tooling gaps. If `git push` fails because a transport helper or credential is missing, stop and report the exact failure. The human either pushes manually or provisions a repo-scoped Git transport for the dedicated agent user.

## Chunk sizing

A chunk ≈ one PROGRESS.md work item ≈ one module or one coherent behavior with its tests, reviewable in a single audit sitting. If an item is too big to finish confidently in one run, split it in PROGRESS.md (W-012 → W-012a/b), note why, build the first part.

## ROLE SWITCH: when invoked as AUDITOR

The human may say "act as auditor" (e.g., when Claude usage is exhausted). Then: **`AUDIT.md` is your entire job description — follow it exactly, produce its report format, respect its prohibitions.** You do not build in the same session you audit. Additional rule for cross-model auditing: where the previous auditor's reports established a convention (severity phrasing, report depth), match it rather than restyling — if you disagree with a prior audit's *judgment*, say so explicitly in your report's "Disagreements" field instead of silently overriding. This keeps auditor drift visible instead of ambient.

## Definition of the current phase

Check `PROGRESS.md` header for the active roadmap phase and gate. Work items outside the active phase are blocked by default regardless of backlog order.
