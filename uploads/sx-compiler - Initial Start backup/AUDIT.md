# AUDIT.md — Auditor Protocol (role-based: applies to WHOEVER audits)

This file is the auditor's complete job description. It is model-agnostic by design — Claude Code is the default auditor, Codex may substitute — so the role cannot drift when the model changes. **This file is read-only for all agents.**

## Purpose

The auditor exists because the builder runs fire-and-forget. You verify that each chunk (1) implements its work item's scope against the LOCKED spec, (2) passes and *deserves to pass* the test suites, and (3) introduced no violations of the hard rules. You then fix what is small, file what is large, and report everything.

## Inputs

1. `PROGRESS.md` — items marked `built, awaiting audit`; the builder's Done-log entry (including stated assumptions/deviations).
2. The diff: every commit since the last `audit(...)` commit.
3. The specs: `docs/ADR_v2.1.md` (grep the D-numbers named in the work item), `docs/implementation-roadmap.md` (phase scope), `docs/STRUCTURE.md`, `docs/TESTING.md`.

## Checklist (run in order; report against every line)

0. **Baton/prefix consistency:** every commit since last audit carries the prefix matching the baton state at its time; violations are critical findings.
1. **Scope:** diff touches only what the work item covers. Out-of-scope changes → flag, and revert them unless harmless and trivial (then note).
2. **Spec conformance:** behavior matches the cited ADR decisions. Check the specific invariants: path validation before writes; decision validation before synthesis; stamping over trusting (D21); serialized queue; residual lifecycle; staging-only canonical writes.
3. **Anti-gaming sweep (never skip):** diff `fixtures/` and `tests/` — any modification to existing `expected`/`must_not` blocks or any loosened assertion is a **critical finding** regardless of whether the code is otherwise correct.
4. **Constants:** no numerics outside `part0.yaml`.
5. **Run:** `pytest`; `python fixtures/runner.py --harness-only`; model fixtures if the item touches prompts/grammar/pack rendering and an endpoint is configured (`--repeat 2` for data-plane fixtures). Record exact commands + results.
6. **Adversarial pass:** for the new code, ask "what input breaks this?" — malformed sentinels, traversal paths, empty chunks, unicode, concurrent-edit timing. Write at least one new test per plausible break you find (even if it passes).
7. **Boundary check:** no LLM client imports outside `control_plane.py`/`data_plane.py`; no bundle paths referenced; no secrets.
8. **Builder's assumptions:** each stated assumption in the Done-log is either endorsed or challenged in your report.

## Actions you MAY take

- Fix defects **you found in this audit**, in-scope, small (roughly: under ~50 changed lines and no interface changes). Commit separately: `audit(W-xxx): fix <defect>`.
- Add tests and strengthen assertions. Add fixtures (new IDs only).
- Update PROGRESS.md per its protocol: item status (`audited-pass` / `audited-fail: see audits/NNN`), new work items for large findings, Questions for the human, baton.

## Actions you MUST NOT take

- Refactor architecture, rename interfaces, or "improve" working code beyond defect fixes — file a work item instead.
- Modify existing fixture expectations or weaken any test.
- Edit spec docs, this file, CLAUDE.md, AGENTS.md, or previous audit reports.
- Build new features, even obviously needed ones.
- Delete or rewrite PROGRESS.md history.
- Approve your own build work (if you built the item under role-switch, the *other* agent or the human audits it).

## Report format — `audits/NNN-Wxxx.md` (append-only directory; NNN monotonic)

```markdown
# Audit NNN — W-xxx <title>
auditor: <claude-code | codex> | date | commits reviewed: <range>
verdict: PASS | PASS-WITH-FIXES | FAIL

## Checklist results
<one line per checklist item: OK / finding-ref>

## Findings
F1 (critical|major|minor): <what, where, why it matters, ADR ref>
   action: fixed in <commit> | filed as W-yyy | question for human

## Commands run
<exact commands and outcomes>

## Tests added
<paths + what they guard>

## Builder assumptions reviewed
<assumption → endorsed / challenged (why)>

## Disagreements
<only for cross-model handoffs: where you dispute a PRIOR audit's judgment>
```

Verdict semantics: **FAIL** returns the item to the builder (baton → builder, status `audited-fail`); **PASS-WITH-FIXES** means your fixes complete it (baton per phase plan); **PASS** likewise. The report is the artifact; the PROGRESS.md entry is one summary line pointing at it.

## Severity ladder

- **critical:** violates a hard rule, corrupts state, games a test/fixture, breaches the Judgment/Execution Boundary. Verdict cannot exceed FAIL unless fixed in-audit.
- **major:** wrong behavior vs spec, missing error path, untested failure mode.
- **minor:** style, docstring gaps, naming, non-load-bearing inefficiency.

## Drift guard

Each audit, before writing your report, re-read this file's Purpose and MUST-NOT list (30 seconds). If you notice an instruction here conflicting with something an agent wrote in PROGRESS.md, **this file wins** and the conflict goes to Questions.
