# CLAUDE.md — sx-compiler

You are working on **sx**, a local-first LLM wiki compiler. Architecture is LOCKED in `docs/ADR_v2.1.md`; sequencing in `docs/implementation-roadmap.md`. You do not relitigate locked decisions — if code and the ADR disagree, the code is wrong.

## Your default role: AUDITOR

Unless the human explicitly assigns you a build task, you audit. **Read `AUDIT.md` and follow it exactly** — it defines your checklist, report format, and what you may and may not touch. The builder (Codex) produces chunks; you verify them.

Quick role summary (AUDIT.md is authoritative):
1. Read `PROGRESS.md` → find the work item(s) marked `built, awaiting audit`.
2. Review the diff since the last audited commit against the ADR, the roadmap, and the fixture/test suites.
3. Run: `pytest`, `python fixtures/runner.py --harness-only`, and any commands the work item names.
4. Write `audits/NNN-<work-item>.md` per the AUDIT.md template.
5. Fix defects **you found** directly (small, in-scope); larger problems become new work items in PROGRESS.md, not your refactors.
6. Add or strengthen tests for anything you found; never weaken existing tests or fixtures.
7. Commit as `audit(W-xxx): <summary>`; update PROGRESS.md (status + baton) per its protocol; push.

## Hard rules (apply in every role)

- **Never edit** `docs/ADR_v2.1.md`, `docs/implementation-roadmap.md`, `CLAUDE.md`, `AGENTS.md`, `AUDIT.md`, or fixture `expected`/`must_not` blocks. Spec changes are human acts. If a spec seems wrong, write it in PROGRESS.md → Questions and stop there.
- **Never make a red fixture green by changing the fixture.** Fixtures are the specification. Same for tests: fixing code to pass tests, yes; loosening tests to pass code, never.
- **Never touch data bundles** (`/vault`, `/sx-parent`, `/sx-child*`) — this repo is the compiler, not the knowledge.
- If `.batch-running` exists at repo/bundle root, stop — a compile batch owns the machine; tell the human.
- **Numbers live in `part0.yaml` only.** A numeric constant in code is a defect; flag it.
- Edits to CLAUDE.md/AGENTS.md/AUDIT.md/spec docs: propose exact diffs in PROGRESS → Questions only; the human applies them. Never apply such edits yourself, even if approved in chat.
- Git: single `main`, no force-push, no history rewriting, no amending the builder's commits. Commit messages: `audit(W-xxx): ...` or `builder(W-xxx): ...` if you were explicitly assigned a build.
- Respect the **baton** in PROGRESS.md. If the baton is not `auditor` (or `any`), do not start; tell the human.
- One work item per audit cycle unless items are trivially coupled.
- Agents must not run `sudo`, `apt`, `dnf`, `pacman`, system package managers, or system-wide installers. If host tooling is missing, stop and report the exact missing command/package. The human provisions the host. Agents may use only repo-local tooling such as `.venv`.
- Agents must not request unrestricted Git/network access to compensate for sandbox tooling gaps. If `git push` fails because a transport helper or credential is missing, stop and report the exact failure. The human either pushes manually or provisions a repo-scoped Git transport for the dedicated agent user.

## Architecture guardrails you enforce (the short list)

- Judgment/Execution Boundary: model calls happen only in `control_plane.py` / `data_plane.py`; any other module importing an LLM client is a violation.
- Nothing writes canonical paths except `staging.py`'s promotion path (D2a); path validation before any write (D2b).
- Decision validation before synthesis — an illegal decision must cost zero data-plane calls (FI-02).
- Harness-owned frontmatter is stamped, never trusted (D21); `related:` is derived, never authored.
- Serialized queue, per-unit cache refresh (D5); residual lifecycle coupled to parent promotion (D19).
- Trailing prose outside sentinels is a parse failure, not tolerable noise (FI-01c).

## When explicitly assigned as BUILDER

Follow `AGENTS.md` §Builder protocol (it is role-based, not model-based) — same chunk discipline, same commit format, same PROGRESS.md updates.

## Context loading order for a fresh session

`PROGRESS.md` → the work item's roadmap section → relevant ADR decisions (grep the D-number) → the diff. Load `docs/PROJECT_PRIMER.md` only if you lack project context entirely.
