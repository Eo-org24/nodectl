# DOC MAINTENANCE — the standard for updating the core file set

This is the tutorial you asked for, and it is also the *rulebook*: every future update round (including ones produced by AI chats) follows this, so the document chain stays auditable instead of accreting versions. The 2026-07-06 round is the worked example of every rule below.

## 1. The four document classes, and how each updates

| Class | Files | Update mechanism |
|---|---|---|
| **LOCKED specs** | ADR (+ its amendments), prompt docs, fixture expectation blocks | **Amendment pattern** — never edit in place. A new dated amendment file with a "Supersedes/Amends" header and per-section deltas. The base doc gets ONE header line: "Amended by: <file>". |
| **Living plans** | roadmap, BLUEPRINT_V2, STRUCTURE, TESTING, INGESTION, GETTING_STARTED, PRIMER | **Edit in place via patch list** — small exact old→new edits, applied by human or agent, committed with a message naming the round. If a round changes >⅓ of a living doc, produce a full replacement with a changelog header instead. |
| **Ledgers** | PROGRESS.md (§append sections), audits/ | **Append-only.** Never rewritten; corrections are new entries. PROGRESS §1–4 are the exception (edit-in-place status), per its own protocol. |
| **Agent instruction files** | CLAUDE.md, AGENTS.md, AUDIT.md | Edit-in-place, but **human hands only** — agents propose exact diffs in PROGRESS Questions; you apply. |

## 2. The amendment lifecycle (LOCKED docs)

1. Amendment drafted → reviewed → CONFIRMED (human word, logged in PROGRESS §6).
2. Base doc + amendment **travel together** (agents load both; the base's header line guarantees discovery).
3. **Merge cadence:** fold amendments into a full new version when EITHER two amendments accumulate OR a phase boundary passes. The merged version carries a changelog listing every folded delta (v2.1 is the worked example — it folded the lockdown).
4. On merge: superseded files move to `docs/archive/` **immediately** — physical removal from the loading path, not an honor system. The PRIMER's "do not load" list is the backup, not the mechanism.

## 3. The five invariant rules (apply to every round)

1. **Single source per fact.** Every rule/number/enum lives in exactly one file; everything else points. Numbers live only in part0.yaml; the update test for any new paragraph is "does this restate something that already has a home?" — if yes, replace prose with a pointer. (This is why schema.md was shrunk to pointers + bundle policy.)
2. **Changelog or it didn't happen.** Every replacement and amendment opens with a delta list against what it supersedes, specific enough for the review chain to audit without diffing.
3. **Dispositions are recorded, not just applied.** Rejected → rejected register with reason. Accepted-with-limitation → named limitation + watching metric. Deferred → PROGRESS Deferred Reminders with a trigger condition. "We discussed it" is not a state.
4. **One decision-log line per human decision** (PROGRESS §6) — the log is the tiebreaker when documents disagree about what was decided, because documents freeze and the ledger moves.
5. **Version pins propagate.** Anything a bundle inherits (schema_version, prompt-pack hashes, reader_contract_version) bumps when its source doc changes; schema.md is the pin registry.

## 4. Receiving updates from an AI chat (the delivery contract)

When any chat (this one or a future one) changes the documents, it must deliver in this exact shape — hold it to this:

- **LOCKED doc changed** → an amendment file (never a rewritten base).
- **Living doc, small change** → an entry in a dated `PATCHES_YYYY-MM-DD.md` with exact old→new text.
- **Living doc, large change / ledgers** → full replacement with changelog header; prior version explicitly named for archive/.
- **New concern** → new doc, added to STRUCTURE's docs/ tree and BLUEPRINT_V2's document map via the same patch file.
- Plus one PROGRESS §6 decision-log block covering the round.

If a chat hands you a wholesale rewritten ADR "for convenience," refuse it — that's how silent drift enters a locked contract.

## 5. Applying a round (your 10-minute checklist)

1. Read the PATCHES file top to bottom; apply each edit (or hand the file to an agent with "apply PATCHES_<date> literally, nothing else").
2. Drop new files into docs/; move named superseded files to docs/archive/.
3. Paste the round's decision-log block into PROGRESS §6; update §1–4 per the round.
4. Commit once: `docs: apply round YYYY-MM-DD (<one-line summary>)`.
5. Skim the PRIMER — if state-of-play changed and the round didn't patch it, the round was incomplete; go back to the chat.

## 6. This round's application map (worked example)

Amendment: ADR_v2.2_API_Mode_Amendment.md (travels with ADR_v2.1). Patches: PATCHES_2026-07-06.md (11 targets). Full replacements: FUTURE_RISKS.md, PROGRESS.md (v1s → archive; already staged in `superseded/`). New: this file. Archive also: ADR_Amendment_OQ1-OQ3_Lockdown_CONFIRMED.md (folded into v2.1 previously — should have been archived then; do it now).
