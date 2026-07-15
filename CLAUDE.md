# CLAUDE.md

Guidance for Claude Code in this repository. This is the nodectl-derived UCC Stage 2
integration line; the preserved Stage-1 standalone line remains at
`Eowerd24/nodectl@nodectl-phase0-conformant-standalone`.

## Read these first (authoritative, in precedence order)

1. **`AGENTS.md`** (same directory) — the canonical, full agent guidance: the
   non-negotiable rules, the event/envelope conventions, and this repo's fenced
   paths, ports, and pending work. **Everything in AGENTS.md applies to you.**
   It is kept as the single source of truth so guidance can't drift between tools.
2. `docs/roadmap/UCC-Shared-Roadmap-To-Fork.md` — the plan, gates, path to fork (§8).
3. `docs/reference/UCC-Standards-and-Layout-Reference.md` — the conventions.

If this file or AGENTS.md disagrees with the roadmap/standards, those win. If the
vendored `ucc-contracts` disagrees with any prose, the code wins.

## The five things to never get wrong

1. **Stage 2 scope is bounded and authorized** — real in-process adapters, canonical
   records/schemas, a disposable projection, the application-service skeleton, one
   fixture-backed operator view, and XDG resolution are in scope. Broker/network module
   APIs, canonical server DB, repo merge, multi-operator auth, full vertical proof, and a
   general remote terminal are not. (AGENTS.md §1.1)
2. **Fail closed over fabricate** — refuse with a typed `ucc.problem` rather than
   invent an ID, hash, token, or state. (AGENTS.md §1.2)
3. **Don't cross the fences** — the standalone-only infra/shell paths listed in
   AGENTS.md must never be reached from a port. Fence tests are **AST-based**;
   never weaken one to a substring match to make it pass. (AGENTS.md §1.3–1.4)
4. **`ucc-contracts` is vendored + pinned** — never hand-edit its schemas, IDs,
   lifecycle tables, or refusal codes locally. (AGENTS.md §1.5)
5. **Six-field format for every change**, delivered as patches (clones are
   read-only). Keep the repo independently runnable and green. (AGENTS.md §1.7–1.8)

## Working notes for Claude Code

- Run the full test suite before and after any change, in an independent fresh
  clone for final verification — not just the working copy you edited.
- Prefer additive files over edits to vendored or load-bearing code — anything
  under `third_party/`, and any module whose own header claims to be synced
  from elsewhere. **Verify that claim before trusting it**, don't just take the
  comment's word for it: nodectl's `backend/ledger.py` claimed for a long time
  to be a vendored copy kept in sync with Artifact-compiler's `soloctl/ledger.py`,
  but the two had already diverged into different modules — the claim was
  stale, not a real constraint (fixed in M-c; see AGENTS.md §3).
- When you change the schema set or a gate's state, update the roadmap (§2/§8)
  and standards reference (§17) in the same change.
- Per-repo specifics (exact fenced symbols, port files, build quirks such as
  VM-Factory's no-editable-install layout) live in **AGENTS.md §3** — consult the
  block for whichever repo this is.

## Out of scope

See AGENTS.md §4. Real in-process adapters, canonical records/domain schemas, and the
disposable projection are Stage 2 work here. If a task needs a broker/network module API,
canonical server database, repo merge, full vertical proof, or trusted-path terminal, stop
and flag it against the roadmap rather than building it.
