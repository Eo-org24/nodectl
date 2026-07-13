# INGESTION — when to start, how to run it, how to review it

## When (the short answer)

| Ingest type | Earliest point | Corpus status |
|---|---|---|
| Dry runs (5–15 files) | M1 passed (walking skeleton) | throwaway, deleted after inspection |
| Calibration runs | Phase 2, feeding V1 | throwaway |
| **First retained ingest** | **M2 passed + residual live + tolerance pre-set** | becomes THE wiki if M3 passes |
| Long-tail / ongoing | after M3 | retained, incremental |

Do not retain anything compiled before residual support exists: bootstrap misplacement is autocatalytic (contaminated pages rank higher and attract further bad merges), and throwaway corpora cost nothing to discard.

## Selecting the 50–100 M3 files (this choice decides what M3 measures)

Aim for a *stress-representative* sample, not your cleanest notes:

- ~40% dense technical notes from ONE domain you know intimately — you must be able to judge synthesis quality at a glance, so pick the domain where your own expertise is the sharpest instrument available.
- ~20% messy/mixed files: meeting-style notes, logistics-contaminated content — exercises `discard` boundaries and multi-concept chunking (residual!).
- ~10% deliberately contradictory pairs: notes you *know* disagree (an old decision + its reversal) — exercises D12/D18 end-to-end with known ground truth.
- ~10% code-heavy notes: identifiers, config keys, snake_case — exercises H1's concern on real data.
- ~10% old/stale material referencing superseded facts — exercises supersession-vs-dispute (the F01/F05 boundary) on real prose.
- ~10% whatever remains most typical of your vault.

If the vault is bilingual, mirror the language ratio in the sample — an English-only M3 pass proves nothing about Polish retrieval.

## Pre-flight (before any batch, mechanical, ~1 hour)

1. **Snapshot:** copy the selected files into the bundle's `raw/` — never point the compiler at the live vault. Record the copy in `source-manifest.json` terms (the harness does this, but verify counts).
2. **Secret scan the raw set** — before ingestion, not just at promotion. A secret that enters a page is a secret in git history.
3. **Dialect normalization** if (and only if) Q-001 said Logseq/outliner content exists.
4. **Dedupe check:** exact-duplicate files in raw waste compile cycles and create merge noise; hash-dedupe first.
5. **Set the staging order:** the harness sorts deterministically, but *you* choose which files enter the queue for Stage 3 (priority pages) — pick the domain-core files.
6. Confirm `part0.yaml` tolerance values are committed BEFORE the run (kill-criteria discipline).
7. **API mode:** verify no `private`/`credential`-tagged sources entered the snapshot (they queue as held_private, not compile); confirm `source_origin` set for any third-party material; confirm cost caps in part0.

## Running a batch

- Overnight/weekend runs; the machine must not sleep; watch thermals on the first long batch — sustained local-model inference is a different load profile than bursts.
- Prefer the provider batch API for Stage 1 (parallel-sanctioned, ~50% cost); Stages 2–4 stay sequential via the standard endpoint. Watch cost-per-unit from unit one — it replaces wall-clock as the scarce resource.
- Stage 1 (inventory summaries) runs parallel; Stages 2–4 serialized. Wall-clock per compile unit is logged from unit one — this is the throughput unknown being measured.
- Do not touch the bundle mid-batch (D2c will requeue on collision, but why generate noise). The vault itself stays yours — only the snapshot is off-limits.
- If quarantine rate spikes early (>~20% of units in the first hour), stop the batch: something systematic is wrong (endpoint, grammar, prompt regression), and burning the queue teaches nothing.

## Reviewing (where the human time goes; budget it honestly)

1. Work from `log.md` digest-delta lines + the M3 metric dump, not by rereading every page.
2. Sample pages per the V2 protocol: entity checks are mechanical; YOUR sampling targets the digest's blind spot — qualitative-claim drift — and summary usefulness.
3. **Every correction becomes a fixture.** The correction workflow is: fix the page → write the one-line reason → the reason becomes a fixture candidate (batch B+ IDs). This loop is the project's compounding asset; skipping it wastes the review.
4. Time-box: log correction time per page honestly (a timer, not vibes) — it's the M3 gate metric.
5. Contradiction pairs you planted: verify each was caught, marked, and NOT silently resolved. A planted contradiction that got blended is an automatic M3 fail regardless of other metrics.

## Tips learned from the design rounds (so you don't rediscover them)

- **Expect create-heavy output in bootstrap.** Duplicate-ish pages are the *intended* failure direction; merge them by hand and don't panic — false merges would be the alarming direction.
- **Hub taxonomy will look wrong after Stage 2.** Adjust the hub config, regenerate (hubs are derived), rerun Stage 3. Cheap.
- **Retune prompts between runs, not mid-run** — mid-run prompt changes destroy the run's evidentiary value (pack hash changes, metrics stop being comparable).
- **Two failed M3 rounds → stop coding** (roadmap kill criterion). The deficit is editorial; the fix is `schema.md`, not machinery.
- **After M3 passes:** commit the bundle, tag it (`wiki-v1`), back it up off-machine, and only then open the long tail.
