# TESTING — the five layers, who writes them, when they run

The project has five distinct test layers. Conflating them is how test suites rot; each layer answers a different question and has a different owner and cadence.

## Layer 1 — Unit & property tests (`tests/`)
**Question:** does each deterministic function behave? **Owner:** builder writes with each work item; auditor adds adversarial cases. **Cadence:** every commit (fast, no model).
Priority targets: path validation (traversal corpus), span slicing (property-based via `hypothesis`: for random chunks+spans, slice+remainder reconstructs the chunk; proper-subset enforcement), chunker boundaries (never mid-sentence-marker; unicode; Polish diacritics if bilingual), dedup key stability, tokenizer counting vs known strings, digest extraction on crafted paragraphs, sentinel parser (strict trailing-prose rejection), frontmatter stamping (model-emitted junk fields discarded), queue transitions incl. residual lifecycle.

## Layer 2 — Fixtures (`fixtures/`)
**Question:** do the model contracts and harness behaviors match the spec? **Owner:** human-approved specs; agents may ADD (new IDs), never modify expectations. **Cadence:** harness fixtures every commit; model fixtures at gates + after any prompt/grammar/pack change (`--repeat 2` for data-plane). In API mode, model fixtures are cheap enough to run on every prompt/grammar-touching commit (respect api.max_cost caps); harness-only remains the per-commit default.
Batch A (13) gates M0/M1; batch B completes ~25–30 at M2. Four kinds: control-plane (exact-match decisions), data-plane (property assertions — generative output is never exact-matched), harness (retrieval/linter/admission/ledger), fault-injection (canned bad outputs; zero-canonical-change assertions).
**Accumulation rule:** every human correction during V2+ becomes a fixture. **Hold-out rule:** from batch B onward, reserve ~20% of new fixtures in `fixtures/holdout/` — run at gates only, never during prompt tuning. This is the guard against prompt-overfitting to the golden corpus; if visible fixtures pass and holdouts fail, the prompts memorized the test.

## Layer 3 — Integration (end-to-end, tiny corpus)
**Question:** does the whole pipeline compose? **Owner:** builder (W-014 era); auditor extends. **Cadence:** every commit if no model needed (canned decisions injected), nightly with a live model.
The canonical integration test: 5-file micro-corpus → full compile → assert page count range, all hard lints clean, index/hubs regenerate byte-identically on rebuild, cache delete + rebuild converges (V8-lite), second identical run changes nothing (idempotence).

## Layer 4 — Gate evaluations (M0–M4 / V0–V8)
**Question:** is the system good enough to advance? **Owner:** human runs, agents assist. **Cadence:** at phase exits only. These are *measurements with pass thresholds pre-committed in part0.yaml*, not tests — the procedures live in the roadmap; results get logged in PROGRESS.md §5. Never let an agent "fix" a gate result; a failed gate is information, and the response is the roadmap's kill/pivot table.

## Layer 5 — Post-MVP functional & drift tests (the wiki itself, after M3)
**Question:** is the *living wiki* staying healthy? **Owner:** human + scheduled jobs. **Cadence:** periodic.
- **Consumer-seat probes:** a standing 10-query subset of V1, rerun monthly from the reader's seat; watch tokens-per-answer and unanswerable count (retrieval rot detector).
- **Full relint sweep:** weekly `sx lint --all`; trend the warning counts — rising orphan/junk-edge/summary warnings are the garden telling you it needs weeding.
- **Digest drift audit:** quarterly sample of high-traffic pages against their sources (qualitative-claim drift, the digest's blind spot).
- **Planted-canary check:** keep 2–3 known contradiction pairs and 2–3 known-stale sources permanently in the corpus; each sweep verifies they're still correctly marked. Canaries detect silent regression in the machinery that metrics can't see.
- **Recovery drill:** quarterly V8 rerun on a bundle copy (delete cache, rebuild, hash-compare) — backup discipline is only real if restoration is rehearsed.

## Division of labor (one line each)

Builder: layer 1 with every chunk, layer 3 scaffolding. Auditor: adversarial layer-1 additions, layer-2 additions, the anti-gaming sweep. Human: layer-2 expectation approval, all of layer 4, layer-5 scheduling and judgment. Fixtures and gates are the two places agents have zero authority over expectations — that's load-bearing, not bureaucracy.
