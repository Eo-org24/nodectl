# Fixture Batch A — M0/M1 Gate Set

**Status:** DRAFT — implements the roadmap's batch A manifest.
**Relationship to the V0 corpus doc:** F01–F09 remain canonical there; this file specifies their skeleton-context **amendments** plus the **full text of the five new fixtures** (H1, H2, FI-01, FI-02, DP-01). Together: 13 fixtures, the M0 model-admission and M1 skeleton gates.

## Batch manifest

| ID | Name | Kind | Source |
|---|---|---|---|
| F01 | exact_anchor_merge | control-plane | corpus doc + amendments below |
| F03 | r2_merge_calibrated | control-plane | corpus doc + amendments |
| F03b | r2_suppressed_in_bootstrap | control-plane | corpus doc + amendments |
| F04 | r3_sibling_branch | control-plane | corpus doc + amendments |
| F05 | contradiction_precedence | control-plane | corpus doc + amendments |
| F06 | discard_noise | control-plane | corpus doc + amendments |
| F07 | size_cap_split | control-plane | corpus doc + amendments |
| F09 | stale_reingest_routing | control-plane | corpus doc + amendments |
| H1 | code_identifier_retrieval | harness (retrieval) | this file |
| H2 | generated_hub_drift | harness (linter) | this file |
| FI-01 | malformed_sentinels | harness (fault-injection) | this file |
| FI-02 | illegal_paths | harness (fault-injection) | this file |
| DP-01 | merge_synthesis_properties | data-plane (property) | this file |

Deferred to batch B (Phase 2 entry): F02 and F08 (require the alias table), all F10/residual fixtures, H3–H5, title-admission ladder, bootstrap variants F04b/F05b, second contradiction type, DP-02 (create-page properties — first item of batch B, since bootstrap-heavy skeleton runs will exercise `create_page` constantly).

## Skeleton-context rules (apply to all batch A runs)

**Band mapping under BM25-only retrieval.** The bands-not-numbers design pays off here: fixtures present candidates with symbolic bands, and the *model's* view is identical regardless of how the harness computed them. In the skeleton, the runner maps `anchor/high/sibling/low` to BM25 score tiers per Part 0; Phase 2 remaps to cosine thresholds. **No fixture text changes at recalibration** — that was the point.

Runner targets the pinned API model via structured outputs; `--repeat 2` records decision-stability rather than asserting byte-identity (amendment §11).

**Residual field handling.** The skeleton grammar includes `residual` (forward-compatibility); the harness discards non-null residuals with a logged warning. Scoring: every batch A model fixture adds `expected.residual: null`, scored **warning-tier** (like `reason_code`/`uncertainty`), not hard-fail — the dedicated abuse fixture lands in batch B. A batch-wide non-null residual pattern on these single-concept fixtures is an M0 red flag even though no single instance fails the gate.

**Determinism repeat rule.** The runner supports `--repeat N`. The M1 gate runs the model-fixture set twice at the pinned execution profile and requires identical decision objects across runs (Tier 1). Per-fixture pass is necessary but not sufficient for the gate.

## Amendments to F01–F09 (uniform unless noted)

1. Add `expected.residual: null` (warning-tier) to every control-plane fixture.
2. F05: `digest_claims` rows now note they are produced by skeleton digest *extraction* (enforcement is warning-only in Phase 1; the fixture tests routing, not enforcement).
3. F07: `target_state` token counts computed by the reference tokenizer named in Part 0 — the fixture file states the tokenizer ID so the fixture is invalid without it (deliberate: forces the counting-authority pin before M0).
4. F03/F03b: unchanged in text; note that in skeleton corpora `mode: bootstrap` will dominate real runs, so F03b is the higher-signal fixture of the pair for M0.

---

## H1 — code_identifier_retrieval (harness: retrieval stage)

**Owns:** D6 tokenizer adequacy; the pack-contents guarantee that precedes every model call.

**Mini-corpus (4 seeded pages):**

```yaml
pages:
  - path: pages/rank-fusion.md
    body_contains: "rrf_fuse() combines the FTS and vector rankings"
  - path: pages/service-a.md
    body_contains: "svc_a.upstream_timeout_ms = 9000"
  - path: pages/tenancy-model.md
    body_contains: "the x-tenant header identifies the tenant"
  - path: pages/wiki-linter.md
    body_contains: "slugs use kebab-case-slug normalization"
```

**Probes (4 chunks, one per identifier, each mentioning it verbatim in otherwise unrelated prose):**

```yaml
assertions:
  for_each_probe:
    - stage_2_fts_results_contain: <the seeded page>
    - within_top_k: true          # k from Part 0 candidate budget
    - asserted_before_model_call: true
  on_failure:
    - append_to: .sx/fts-misses.log
    - record: {probe_id, identifier, tokenizer_config}
```

**Pass:** 4/4 probes. **Fail consequence:** this is the trigger for the D6 trigram-tokenizer contingency — the fixture failing is *useful*, it fires the fallback decision with evidence attached.

## H2 — generated_hub_drift (harness: linter + regeneration)

**Owns:** D10 (machine-generated routing artifacts) and the D20 severity contract.

**Setup:** compile a small corpus so `hubs/services.md` exists with its DO-NOT-EDIT header. Then inject one human-authored line into the hub body:

```
- [[pages/my-manual-note.md]] — added by hand
```

**Assertions:**

```yaml
lint_result:
  severity: needs_review          # never hard_fail — a human edit is a signal, not corruption
  report_quotes_injected_line: true
regeneration:
  hub_restored_to_generated_form: true
  injected_line_absent: true
canonical_pages:
  files_changed: 0                # hub is derived state; page files untouched
log:
  drift_event_recorded: true
```

**Pass:** all four blocks. The fixture encodes the philosophy: derived state is overwritten, but the human's intent is surfaced loudly rather than silently erased.

## FI-01 — malformed_sentinels (harness: fault-injection, data-plane parse path)

**Owns:** V5 corruption resistance. The "model" is replaced by canned outputs; no real model call.

**Injected variants:**

```yaml
variants:
  a_missing_end:      "<<<WIKI_PAGE_BEGIN>>>\n---\ntitle: X\n---\nbody"
  b_double_begin:     "<<<WIKI_PAGE_BEGIN>>>\n<<<WIKI_PAGE_BEGIN>>>\n...\n<<<WIKI_PAGE_END>>>"
  c_trailing_prose:   "<<<WIKI_PAGE_BEGIN>>>\n...\n<<<WIKI_PAGE_END>>>\nHope this helps!"
  d_empty_body:       "<<<WIKI_PAGE_BEGIN>>>\n---\ntitle: X\nsummary: y\ntags: []\n---\n<<<WIKI_PAGE_END>>>"
```

**Assertions (per variant):**

```yaml
unit_status: quarantined                   # skeleton has no retry ladder; quarantine-only
failure_record:
  contains: {variant_class, raw_output_ref, compile_unit_id}
filesystem:
  canonical_tree_hash_before == canonical_tree_hash_after: true   # the V5 zero-change invariant
  staging_dir_empty_after: true
log:
  quarantine_event_appended: true
```

Variant `c` is the one that catches lazy parsers: the page between sentinels is valid, and the temptation is to accept it. The contract is *nothing outside sentinels* — accept-with-trailing-prose is a fail.

## FI-02 — illegal_paths (harness: fault-injection, decision-validation path)

**Owns:** path safety and `ALLOWED_TARGETS` enforcement — the corruption channel the two-plane design exists to close.

**Injected control-plane decisions:**

```yaml
variants:
  a_unlisted_target:   {action: merge_into, target_path: "pages/nonexistent.md"}    # not in pack
  b_path_traversal:    {action: merge_into, target_path: "../vault/decisions/routing-architecture.md"}
  c_slug_traversal:    {action: create_page, new_page: {title: "Evil", slug: "../../evil", hub: hubs/services.md}}
  d_null_target_merge: {action: merge_into, target_path: null}
```

**Assertions (per variant):**

```yaml
rejected_at: decision_validation
data_plane_calls_made: 0            # trace-asserted; the bad decision must die BEFORE synthesis spends tokens
unit_status: quarantined
failure_record:
  contains: {violation_class, offending_path_or_slug}
filesystem:
  canonical_tree_hash_unchanged: true
```

The `data_plane_calls_made: 0` assertion is the teeth: it distinguishes validation-before-synthesis from validation-after, which matters both for safety ordering and for wasted local-model wall-clock.

## DP-01 — merge_synthesis_properties (data-plane: property fixture, real model call)

**Owns:** the §7 checklist of the synthesis-prompt doc. Reuses F01's pack (merge into `pages/service-a.md`, timeout 3000 → 9000 with explicit change language, retry budget 2 unchanged) plus the MERGE_INTO directive. Generative output is property-asserted, never exact-matched.

**Input additions to F01's pack:**

```yaml
current_page:
  frontmatter_summary: "Primary edge routing service; owns upstream timeout and retry policy."
  headings: ["## Role", "## Configuration", "## Incidents"]
  body_claims_include: ["upstream timeout 3s (svc_a.upstream_timeout_ms = 3000)", "retry budget of 2"]
```

**Hard assertions:**

```yaml
output:
  sentinels: {begin_count: 1, end_count: 1, nothing_outside: true}
  frontmatter:
    fields_exactly: [title, summary, tags]        # proposed_aliases optional; any other field = fail
    summary_byte_equal_to_existing: true          # sticky rule — scope did not change
  body:
    token_count_lte: 1200                          # reference tokenizer
    headings_present_exactly: ["## Role", "## Configuration", "## Incidents"]
    contains_verbatim: ["svc_a.upstream_timeout_ms = 9000", "2026-06-28"]   # new value + change date
    preserves_claim: "retry budget"                # the unchanged claim survives regeneration
    superseded_value_handled: "3000 absent OR present only within change-note phrasing"
  links:
    all_wikilinks_within: [pages/edge-router.md, pages/deployment-patterns.md]   # pack set; no invented links
```

**Warning-tier:** lead paragraph present; no meta-commentary strings ("This page describes", "Hope this"); heading order preserved.

**Not asserted (V2 sampling):** register, no-external-knowledge, qualitative-claim nuance.

**Repeat rule:** DP-01 runs under `--repeat 2`; hard assertions must pass on both runs (property stability, the Tier 2 analogue — outputs may differ textually, properties may not).

---

## Runner notes

- Harness fixtures (H*, FI-*) require no model and should run in CI on every commit; model fixtures (F*, DP-01) run on demand and at gates.
- Every fixture failure emits the structured failure record — the same schema the compiler uses — so the fixture harness exercises the failure-record path for free.
- Batch B stub: this file's manifest table is the insertion point; new fixtures append, existing ones never renumber.
