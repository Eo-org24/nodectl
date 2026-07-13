# V0 Golden Corpus + Control-Plane Prompt (Draft 1)

**Status:** DRAFT — co-designed unit; the fixtures are the executable specification of the prompt.
**Implements:** ADR v2 Part IV, gate V0. Contracts referenced: D3 (decision schema), D4 (R1–R7 + error-cost asymmetry + bootstrap mode), D5 (pack SOP, anchor softening), D12 (contradiction precedence), D14 (escalation triggers).
**Scope note:** V0 in the ADR covers harness behavior as well as model behavior. Fixtures F01–F10 test the control-plane *model decision*. Appendix A specs the two harness-level fixtures from the ADR's V0 list (code-identifier retrieval, generated-hub drift) so the gate's coverage matches the ADR verbatim.

**Design principle — bands, not numbers.** Fixtures never reference raw cosine values. Candidates carry a symbolic band (`anchor`, `high` = R2 zone, `sibling` = R3 zone, `low`). This decouples V0 from V1: recalibrating thresholds or swapping the embedding model re-maps bands to numbers without invalidating a single fixture. The harness's fixture runner owns the band→number mapping, sourced from Part 0 config.

---

## 1. Pack Format (control-plane input contract)

The prompt template in §2 renders exactly this structure. Fixtures supply it directly.

```yaml
pack:
  mode: calibrated | bootstrap        # D4 bootstrap rule active when bootstrap
  source_chunk: <400–800 token Markdown chunk>
  source_ref: raw/<path>#<chunk-ordinal>
  keyphrases: [<harness-extracted>]
  exact_anchors:                      # Stage-1 hits; PREFERRED candidates, never automatic (D5)
    - {id, path, via: title|alias|slug, title, summary}
  candidates:                         # fused list, ≤6 + anchors (Part 0)
    - {id, path, title, summary, band: anchor|high|sibling|low}
  neighbor_stubs:                     # 1-hop, path + title + summary only (D9)
    - {path, title, summary}
  hub_hint: hubs/<name>.md
  target_state:                       # harness-computed, present when any candidate is a plausible merge target
    - {path, body_tokens, cap, headings: [<h2 paths>]}
  digest_claims:                      # entity-digest rows for anchor/high candidates (D11/D18)
    - {claim_id, path, heading_path, entity, value, source_ref}
  allowed_targets_note: "target_path must be one of the candidate/anchor paths above, or null"
```

Rationale for `target_state`: R5 (size-cap split) is undecidable by the model without token counts, and the model must never estimate tokens itself (D16 — counting authority is the pinned reference tokenizer). The harness computes and injects.

Rationale for `digest_claims`: the `contradiction` action requires `claim_ids`; the model can only cite IDs it was shown. This is also where D18's mechanical prefilter surfaces (same entity key, conflicting value → the harness may pre-mark a candidate pair).

---

## 2. Control-Plane Prompt Template

Two parts: a fixed system prompt (~550 tokens — budget matters, it rides inside the D5 pack budget) and a user-turn rendering of the pack. Grammar constraint (GBNF) guarantees the output *shape*; this prompt carries the *semantics*. Never rely on the prompt for shape or the grammar for judgment.

### 2.1 System prompt

```text
You are the routing stage of a wiki compiler. You receive one source chunk
plus retrieval context, and you output exactly one JSON decision object.
You never write wiki content. You never output anything except the JSON object.

ACTIONS
- merge_into: the chunk's subject matter belongs on an existing page shown
  in CANDIDATES. Choose this only when the chunk and the page describe the
  same concept at the same scope.
- create_page: the chunk introduces a concept no candidate page covers at
  the same scope. Fill new_page (title, slug, hub) and list at least two
  required_links to existing pages from CANDIDATES or NEIGHBOR STUBS.
- split_target: the correct target page is at or near its size cap
  (see TARGET STATE). Name the heading to split out in split_section.
- contradiction: the chunk conflicts with a claim shown in DIGEST CLAIMS
  (same entity, incompatible value; a status reversal; a date/version
  conflict). Cite the claim_ids. Contradiction OUTRANKS merge: if a
  conflict exists, you must not choose merge_into.
- discard: the chunk contains no durable knowledge (logistics, boilerplate,
  duplicated content, chatter).

DECISION PROCEDURE
1. If DIGEST CLAIMS conflict with the chunk → contradiction.
2. Else if an EXACT ANCHOR matches the chunk's subject at the same scope
   → merge_into it. Anchors are candidates, not commands: reject the
   anchor on scope, namespace, or page-type mismatch (acronyms and
   generic titles collide).
3. Else if a candidate in the HIGH band is the same concept at the same
   scope → merge_into it.
4. Else if candidates are related but the chunk is a distinct concept
   → create_page, linking the related candidates.
5. Else → create_page under the hub hint, or discard if nothing durable.
6. If your merge target is at/near cap per TARGET STATE → split_target.

BIAS RULE
A wrong create_page is cheap to repair; a wrong merge_into contaminates a
page. When uncertain between them, choose create_page and say
uncertainty: "medium" or "high".

BOOTSTRAP MODE (when MODE: bootstrap)
merge_into is allowed ONLY on an exact anchor, or on a HIGH-band candidate
with uncertainty: "low". Otherwise create_page.

CONSTRAINTS
- target_path must be a path shown in CANDIDATES/ANCHORS, or null.
- claim_ids and candidate_ids must be IDs shown in the pack.
- Never invent paths, IDs, or numeric confidence scores.
- uncertainty is exactly one of: low, medium, high.
- Set escalation_recommended: true only for conflicts touching
  architecture-decision pages, or when more than one candidate is an
  equally plausible merge target.
```

### 2.2 User-turn rendering

```text
MODE: {mode}
SOURCE CHUNK ({source_ref}):
{source_chunk}

KEYPHRASES: {keyphrases}

EXACT ANCHORS:
{for each: - [{id}] {path} (via {via}) — {title}: {summary}}

CANDIDATES:
{for each: - [{id}] {path} ({band}) — {title}: {summary}}

NEIGHBOR STUBS:
{for each: - {path} — {title}: {summary}}

HUB HINT: {hub_hint}

TARGET STATE:
{for each: - {path}: {body_tokens}/{cap} tokens; headings: {headings}}

DIGEST CLAIMS:
{for each: - [{claim_id}] {path} § {heading_path}: {entity} = {value} (per {source_ref})}

Output the JSON decision object now.
```

---

## 3. Fixture Format

```yaml
id: F--
name:
rule_under_test:      # R-rule / D-decision citations
mode: calibrated | bootstrap
pack: {…}             # per §1
expected: {…}         # canonical passing output (fields that must match)
accept_also: […]      # alternative outputs that also pass, if any
must_not: […]         # outputs that constitute the named failure mode
notes:
```

Pass criteria: `action`, `target_path`, and (where present) `claim_ids` / `split_section` must match `expected` or an `accept_also` entry; `reason_code` and `uncertainty` are scored but a mismatch is a *warning*, not a failure (they're diagnostic fields). Any `must_not` match is a hard failure. Wrong-action rate across the corpus is the V0/D15 admission metric for any model.

---

## 4. Fixtures

### F01 — Exact-anchor merge
```yaml
id: F01
name: exact_anchor_merge
rule_under_test: R1 (D4); anchor preference (D5)
mode: calibrated
pack:
  source_chunk: |
    Service A's upstream timeout was raised from 3s to 9s on 2026-06-28
    after the June routing incidents. The retry budget is unchanged at 2.
    Config key: svc_a.upstream_timeout_ms = 9000.
  source_ref: raw/ops/2026-06-config-changes.md#3
  keyphrases: [service a, upstream timeout, retry budget, svc_a.upstream_timeout_ms]
  exact_anchors:
    - {id: c-012, path: pages/service-a.md, via: title, title: "Service A",
       summary: "Primary edge routing service; owns upstream timeout and retry policy."}
  candidates:
    - {id: c-012, path: pages/service-a.md, title: "Service A", band: anchor,
       summary: "Primary edge routing service; owns upstream timeout and retry policy."}
    - {id: c-031, path: pages/deployment-patterns.md, title: "Deployment Patterns",
       band: low, summary: "Catalog of rollout and release patterns in use."}
  neighbor_stubs:
    - {path: pages/edge-router.md, title: "Edge Router", summary: "Fronts Service A; TLS termination."}
  hub_hint: hubs/services.md
  target_state:
    - {path: pages/service-a.md, body_tokens: 640, cap: 1200,
       headings: ["## Role", "## Configuration", "## Incidents"]}
  digest_claims:
    - {claim_id: e-svca-004, path: pages/service-a.md, heading_path: "## Configuration",
       entity: svc_a.upstream_timeout_ms, value: "3000", source_ref: raw/ops/2026-03-baseline.md#2}
expected:
  action: merge_into
  target_path: pages/service-a.md
  reason_code: exact_title
  uncertainty: low
accept_also: []
must_not:
  - {action: create_page}          # duplicate-page failure
  - {action: contradiction}        # see notes
notes: >
  Deliberate trap included: the digest shows the OLD timeout (3000) while the
  chunk states 9000 WITH an explicit change event ("was raised ... after").
  A dated config change is an update, not a contradiction — the chunk
  supersedes with provenance. This boundary (update-with-provenance vs.
  conflict) is the single most important semantic distinction in the corpus;
  F05 tests the other side of it.
```

### F02 — Alias merge
```yaml
id: F02
name: alias_anchor_merge
rule_under_test: R1 via aliases (D4, D21 alias table)
mode: calibrated
pack:
  source_chunk: |
    The SA gateway now rejects requests missing the x-tenant header. Rollout
    completed 2026-07-01; rejection rate stabilized at 0.4% after client fixes.
  source_ref: raw/ops/2026-07-tenant-header.md#1
  keyphrases: [sa gateway, x-tenant header, rejection rate]
  exact_anchors:
    - {id: c-012, path: pages/service-a.md, via: alias, title: "Service A",
       summary: "Primary edge routing service; owns upstream timeout and retry policy."}
  candidates:
    - {id: c-012, path: pages/service-a.md, title: "Service A", band: anchor,
       summary: "Primary edge routing service; owns upstream timeout and retry policy."}
    - {id: c-044, path: pages/tenancy-model.md, title: "Tenancy Model", band: sibling,
       summary: "How tenants are identified and isolated across services."}
  neighbor_stubs:
    - {path: pages/edge-router.md, title: "Edge Router", summary: "Fronts Service A; TLS termination."}
  hub_hint: hubs/services.md
  target_state:
    - {path: pages/service-a.md, body_tokens: 640, cap: 1200,
       headings: ["## Role", "## Configuration", "## Incidents"]}
  digest_claims: []
expected:
  action: merge_into
  target_path: pages/service-a.md
  reason_code: exact_title
  uncertainty: low
must_not:
  - {action: create_page, new_page: {slug: sa-gateway}}   # alias-blindness failure
notes: >
  "SA gateway" must resolve through the alias to service-a. The sibling
  candidate (tenancy-model) is a distractor: the chunk MENTIONS tenancy but
  is ABOUT Service A behavior. Tests subject-vs-mention discrimination.
```

### F03 — High-similarity merge (calibrated) / create (bootstrap)
```yaml
id: F03
name: r2_merge_calibrated
rule_under_test: R2 (D4)
mode: calibrated
pack:
  source_chunk: |
    Canary rollouts here hold 5% of traffic for 30 minutes before promotion.
    Promotion is blocked if error rate exceeds baseline by 0.5 percentage
    points. This applies to all stateless services.
  source_ref: raw/notes/rollout-practice.md#2
  keyphrases: [canary rollout, traffic percentage, promotion criteria]
  exact_anchors: []
  candidates:
    - {id: c-031, path: pages/deployment-patterns.md, title: "Deployment Patterns",
       band: high, summary: "Catalog of rollout and release patterns in use, with promotion criteria."}
    - {id: c-012, path: pages/service-a.md, title: "Service A", band: low,
       summary: "Primary edge routing service; owns upstream timeout and retry policy."}
  neighbor_stubs:
    - {path: pages/release-calendar.md, title: "Release Calendar", summary: "Cadence and freeze windows."}
  hub_hint: hubs/architecture.md
  target_state:
    - {path: pages/deployment-patterns.md, body_tokens: 720, cap: 1200,
       headings: ["## Canary", "## Blue-green", "## Rollback strategies"]}
  digest_claims: []
expected:
  action: merge_into
  target_path: pages/deployment-patterns.md
  reason_code: high_similarity
  uncertainty: low
must_not:
  - {action: create_page}
notes: Same concept, same scope, existing "## Canary" heading. Clean R2 merge.
```

```yaml
id: F03b
name: r2_suppressed_in_bootstrap
rule_under_test: D4 bootstrap mode
mode: bootstrap
pack: <identical to F03, except the summary of c-031 is weakened to
      "Catalog of release patterns." to induce non-low uncertainty>
expected:
  action: create_page
  new_page: {title: "Canary Rollout Practice", slug: canary-rollout-practice, hub: hubs/architecture.md}
  required_links: [pages/deployment-patterns.md, pages/release-calendar.md]
  uncertainty: medium
accept_also:
  - {action: merge_into, target_path: pages/deployment-patterns.md, uncertainty: low}
must_not:
  - {action: merge_into, uncertainty: medium}
  - {action: merge_into, uncertainty: high}
notes: >
  The bootstrap rule is what's under test: merge without exact anchor is
  permitted ONLY at uncertainty: low. A medium/high-uncertainty merge in
  bootstrap mode is the exact failure the rule exists to prevent.
```

### F04 — Sibling branch
```yaml
id: F04
name: r3_sibling_branch
rule_under_test: R3 (D4); ≥2-link quota on create
mode: calibrated
pack:
  source_chunk: |
    Service B is being stood up as the async ingestion counterpart to
    Service A. It consumes the same tenant headers but exposes no
    synchronous API; all input arrives via the queue. Owner: platform team.
  source_ref: raw/projects/service-b-kickoff.md#1
  keyphrases: [service b, async ingestion, queue, tenant headers]
  exact_anchors: []
  candidates:
    - {id: c-012, path: pages/service-a.md, title: "Service A", band: sibling,
       summary: "Primary edge routing service; owns upstream timeout and retry policy."}
    - {id: c-044, path: pages/tenancy-model.md, title: "Tenancy Model", band: sibling,
       summary: "How tenants are identified and isolated across services."}
  neighbor_stubs:
    - {path: pages/edge-router.md, title: "Edge Router", summary: "Fronts Service A; TLS termination."}
  hub_hint: hubs/services.md
  target_state: []
  digest_claims: []
expected:
  action: create_page
  new_page: {title: "Service B", slug: service-b, hub: hubs/services.md}
  reason_code: scope_mismatch
  required_links: [pages/service-a.md, pages/tenancy-model.md]
  uncertainty: low
must_not:
  - {action: merge_into, target_path: pages/service-a.md}   # sibling-collapse failure
notes: >
  Related-but-distinct at identical abstraction level: the canonical R3 case.
  Merging Service B into Service A's page is the provenance-contamination
  failure the asymmetry rule exists to prevent. Both sibling links required.
```

### F05 — Contradiction outranks merge
```yaml
id: F05
name: contradiction_precedence
rule_under_test: R7 (D4); D12; D14 escalation trigger
mode: calibrated
pack:
  source_chunk: |
    Note from architecture sync: Service A is deprecated effective
    2026-06-20. All new integrations must target the edge router directly.
    Existing consumers migrate by Q4.
  source_ref: raw/meetings/2026-06-20-arch-sync.md#4
  keyphrases: [service a, deprecated, edge router, migration]
  exact_anchors:
    - {id: c-012, path: pages/service-a.md, via: title, title: "Service A",
       summary: "Primary edge routing service; owns upstream timeout and retry policy."}
  candidates:
    - {id: c-012, path: pages/service-a.md, title: "Service A", band: anchor,
       summary: "Primary edge routing service; owns upstream timeout and retry policy."}
  neighbor_stubs:
    - {path: pages/edge-router.md, title: "Edge Router", summary: "Fronts Service A; TLS termination."}
  hub_hint: hubs/services.md
  target_state:
    - {path: pages/service-a.md, body_tokens: 640, cap: 1200,
       headings: ["## Role", "## Configuration", "## Incidents"]}
  digest_claims:
    - {claim_id: e-svca-001, path: pages/service-a.md, heading_path: "## Role",
       entity: "Service A status", value: "primary routing layer",
       source_ref: raw/decisions/2025-11-routing-architecture.md#1}
expected:
  action: contradiction
  target_path: pages/service-a.md
  claim_ids: [e-svca-001]
  reason_code: conflict
  uncertainty: low
  escalation_recommended: true
must_not:
  - {action: merge_into}           # silent-replacement failure (D12)
notes: >
  Contrast with F01: there, a dated value change with explicit change
  language = update. Here, a status reversal against a standing DECISION
  source = conflict requiring the Contradiction Protocol. The conflicting
  claim originates from a decisions/ source, which is what justifies
  escalation_recommended (D14: touches canonical architecture decisions).
```

### F06 — Discard
```yaml
id: F06
name: discard_noise
rule_under_test: action enum boundary; over-ingestion failure mode
mode: calibrated
pack:
  source_chunk: |
    Rescheduling: the deployment review moves from Tuesday to Thursday this
    week only. Same call link. Lena is out; Priya will take notes.
  source_ref: raw/meetings/2026-07-scheduling.md#2
  keyphrases: [deployment review, reschedule]
  exact_anchors: []
  candidates:
    - {id: c-031, path: pages/deployment-patterns.md, title: "Deployment Patterns",
       band: low, summary: "Catalog of rollout and release patterns in use."}
  neighbor_stubs: []
  hub_hint: hubs/architecture.md
  target_state: []
  digest_claims: []
expected:
  action: discard
  uncertainty: low
must_not:
  - {action: create_page}
  - {action: merge_into}
notes: >
  Lexical overlap trap: "deployment" appears, retrieval surfaces
  deployment-patterns, but the chunk holds zero durable knowledge.
  Discard ≠ "not parent-worthy" — parent-worthiness is a drafts-channel
  concern outside this enum (see OQ2).
```

### F07 — Split at size cap
```yaml
id: F07
name: size_cap_split
rule_under_test: R5 (D4); target_state contract (§1)
mode: calibrated
pack:
  source_chunk: |
    Rollback procedure addendum: for stateful services, snapshot the schema
    version before promotion; rollback restores the snapshot, replays the
    WAL to the promotion timestamp, and re-pins the previous image digest.
    Verified in the June restore drill.
  source_ref: raw/ops/rollback-addendum.md#1
  keyphrases: [rollback, stateful, snapshot, wal replay, image digest]
  exact_anchors: []
  candidates:
    - {id: c-031, path: pages/deployment-patterns.md, title: "Deployment Patterns",
       band: high, summary: "Catalog of rollout and release patterns in use, with promotion criteria."}
  neighbor_stubs:
    - {path: pages/backup-restore.md, title: "Backup & Restore", summary: "Snapshot and restore drills."}
  hub_hint: hubs/architecture.md
  target_state:
    - {path: pages/deployment-patterns.md, body_tokens: 1130, cap: 1200,
       headings: ["## Canary", "## Blue-green", "## Rollback strategies"]}
  digest_claims: []
expected:
  action: split_target
  target_path: pages/deployment-patterns.md
  split_section: "## Rollback strategies"
  reason_code: size_cap
  required_links: [pages/deployment-patterns.md, pages/backup-restore.md]
  uncertainty: low
must_not:
  - {action: merge_into}           # would breach cap → guaranteed hard_fail downstream (D20)
notes: >
  R2 semantics say merge; TARGET STATE says the merge cannot fit. The model
  must read the harness-computed numbers rather than estimate. A merge here
  isn't just suboptimal — it produces a deterministic lint hard-fail, so
  choosing it wastes a full compile cycle.
```

### F08 — Acronym collision (anchor softening)
```yaml
id: F08
name: anchor_scope_rejection
rule_under_test: D5 exact-anchor softening
mode: calibrated
pack:
  source_chunk: |
    The wiki linter builds a DAG of page links to run orphan detection in
    topological order; cycles are broken by recording back-edges rather
    than failing.
  source_ref: raw/projects/wiki-linter-design.md#5
  keyphrases: [dag, page links, orphan detection, topological order]
  exact_anchors:
    - {id: c-072, path: pages/dag-pipelines.md, via: alias, title: "DAG Pipelines",
       summary: "Airflow DAG conventions: scheduling, retries, task ownership."}
  candidates:
    - {id: c-072, path: pages/dag-pipelines.md, title: "DAG Pipelines", band: anchor,
       summary: "Airflow DAG conventions: scheduling, retries, task ownership."}
    - {id: c-090, path: pages/wiki-linter.md, title: "Wiki Linter", band: high,
       summary: "Deterministic checks over compiled wiki pages: links, orphans, staleness."}
  neighbor_stubs: []
  hub_hint: hubs/architecture.md
  target_state:
    - {path: pages/wiki-linter.md, body_tokens: 400, cap: 1200, headings: ["## Checks"]}
  digest_claims: []
expected:
  action: merge_into
  target_path: pages/wiki-linter.md
  reason_code: high_similarity
  uncertainty: low
must_not:
  - {action: merge_into, target_path: pages/dag-pipelines.md}   # anchor-obedience failure
notes: >
  The anchor is a homonym: "DAG" (Airflow) vs "DAG" (link graph). The
  correct target is the non-anchor HIGH candidate. This is the fixture that
  distinguishes "anchors are preferred candidates" from "anchors are
  commands" — the single behavior D5's softening amendment exists for.
```

### F09 — Stale-source re-ingest
```yaml
id: F09
name: stale_reingest_routing
rule_under_test: routing stability under status: stale (D5 change detection; D12 status semantics)
mode: calibrated
pack:
  source_chunk: |
    Service A's retry budget was raised from 2 to 3 on 2026-07-02 following
    the hedging experiment. Timeout unchanged at 9s.
  source_ref: raw/ops/2026-06-config-changes.md#3    # same source as F01, edited → page went stale
  keyphrases: [service a, retry budget, timeout]
  exact_anchors:
    - {id: c-012, path: pages/service-a.md, via: title, title: "Service A",
       summary: "Primary edge routing service; owns upstream timeout and retry policy. [status: stale]"}
  candidates:
    - {id: c-012, path: pages/service-a.md, title: "Service A", band: anchor,
       summary: "Primary edge routing service; owns upstream timeout and retry policy. [status: stale]"}
  neighbor_stubs: []
  hub_hint: hubs/services.md
  target_state:
    - {path: pages/service-a.md, body_tokens: 700, cap: 1200,
       headings: ["## Role", "## Configuration", "## Incidents"]}
  digest_claims:
    - {claim_id: e-svca-007, path: pages/service-a.md, heading_path: "## Configuration",
       entity: "retry budget", value: "2", source_ref: raw/ops/2026-06-config-changes.md#3}
expected:
  action: merge_into
  target_path: pages/service-a.md
  reason_code: exact_title
  uncertainty: low
must_not:
  - {action: create_page}          # stale-avoidance failure (duplicates the page)
  - {action: contradiction}        # same-source supersession is an update, not a dispute
notes: >
  Two things under test: (1) stale status must not scare routing away from
  the correct target — recompiling the stale page IS the repair;
  (2) the digest claim it conflicts with originates from the SAME source_ref
  that was edited — same-source supersession is definitionally an update,
  never a contradiction. This rule should be stated in schema.md.
```

### F10 — Multi-concept chunk (DECISION FORCER)
```yaml
id: F10
name: multi_concept_chunk
rule_under_test: D3 single-action contract — this fixture forces the amendment decision
mode: calibrated
pack:
  source_chunk: |
    Two changes from the hedging experiment. First, Service A's retry
    budget rises to 3 (see config change log). Second, we're adopting
    request hedging as a standing pattern: duplicate the request to a
    second replica after p95 latency elapses, cancel the loser. Hedging
    applies to idempotent reads only and needs its own documentation —
    budget interaction, cancellation semantics, and metrics.
  source_ref: raw/notes/hedging-outcome.md#1
  keyphrases: [service a, retry budget, request hedging, idempotent reads, cancellation]
  exact_anchors:
    - {id: c-012, path: pages/service-a.md, via: title, title: "Service A",
       summary: "Primary edge routing service; owns upstream timeout and retry policy."}
  candidates:
    - {id: c-012, path: pages/service-a.md, title: "Service A", band: anchor,
       summary: "Primary edge routing service; owns upstream timeout and retry policy."}
    - {id: c-031, path: pages/deployment-patterns.md, title: "Deployment Patterns",
       band: sibling, summary: "Catalog of rollout and release patterns in use."}
  neighbor_stubs: []
  hub_hint: hubs/architecture.md
  target_state:
    - {path: pages/service-a.md, body_tokens: 700, cap: 1200,
       headings: ["## Role", "## Configuration", "## Incidents"]}
  digest_claims: []

# --- Expectation under the LOCKED contract (single action) ---
expected_locked:
  accept_also:
    - {action: create_page, new_page: {title: "Request Hedging", slug: request-hedging,
       hub: hubs/architecture.md}, required_links: [pages/service-a.md, pages/deployment-patterns.md]}
    - {action: merge_into, target_path: pages/service-a.md}
  known_loss: >
    Whichever action passes, roughly half the chunk's durable content is
    misrouted or dropped. Under the locked contract this fixture cannot
    have a lossless passing output. V2 must measure this as
    "content-misplacement rate".

# --- Expectation under the PROPOSED amendment (ordered decision list, harness-capped at 3) ---
expected_amended:
  decisions:
    - {action: merge_into, target_path: pages/service-a.md}
    - {action: create_page, new_page: {title: "Request Hedging", slug: request-hedging,
       hub: hubs/architecture.md}, required_links: [pages/service-a.md, pages/deployment-patterns.md],
       reason_code: scope_mismatch}
must_not:
  - {action: discard}
notes: >
  This is not a model-quality fixture; it is a contract-adequacy fixture.
  If the ADR keeps the single-action lock, adopt expected_locked and add the
  misplacement metric to V2. If it amends D3 to an ordered decision list
  (each entry spawning its own data-plane call, harness cap 2–3),
  adopt expected_amended. The fixture is written so either resolution is a
  one-line switch in the runner — but the decision must be recorded in the
  ADR either way.
```

---

## Appendix A — Harness-level V0 fixtures (from the ADR's V0 list)

**H1 — Code-identifier retrieval (owns: D6 tokenizer behavior).** Corpus page containing `rrf_fuse()`, `svc_a.upstream_timeout_ms`, `x-tenant`, and `kebab-case-slug`. Assertion: for a chunk mentioning each identifier verbatim, the Stage-2 FTS pass returns the containing page inside top-k *before* any model is called. This is an assertion on pack contents, not on model output. Failures feed `fts-misses.log` and the trigram decision (D6).

**H2 — Generated-hub drift (owns: D10/D20 linter path).** Insert a human-authored line into a generated `hubs/services.md` beneath the DO-NOT-EDIT header. Assertion: linter emits `needs_review` (never hard_fail), regeneration restores the file, and the drift report quotes the overwritten line. Zero canonical page files change.

---

## Appendix B — Open contract questions this corpus forces

**OQ1 — Multi-action per chunk (F10).** Keep the single-action lock + measure misplacement in V2, or amend D3 to an ordered decision list capped by the harness. Recommendation: run V0/V2 under the locked contract first; amend only if the measured misplacement rate is material. Either way, record it — F10 currently has two expectation blocks and a runner can only load one.

**OQ2 — Draft-emission pathway in compiler-children.** The action enum has no `emit_draft`, yet the Blueprint requires compiler-children to detect parent-worthy insights. Options: (a) a post-pass classifier over newly created/merged pages that nominates outbox drafts (keeps the control plane skinny — consistent with D3's design philosophy); (b) a sixth enum action (widens the contract the grammar must cover). Note that for **consumer children** (read + drafts out, no compiler) this question doesn't arise — the working agent writes drafts directly, which is safe because the drafts channel is quarantined and human-gated by design.

**OQ3 — Alias authority.** `aliases:` feeds the exact-anchor table, meaning whoever writes aliases steers all future routing. If the data-plane model can author aliases during regeneration, the model influences its own future anchors — a slow self-reinforcement channel. Recommendation: aliases are harness/human-owned frontmatter (part of the D21 ownership matrix); the model may *propose* aliases only via a `needs_review` lint pathway.

---

## Appendix C — Reader-contract outline (companion artifact, one page)

The consumption-side mirror of `schema.md`, injected into any agent that mounts the wiki (including consumer children):

1. **Routing:** read `index.md` → follow one hub → open at most N pages; every page is ≤ cap tokens, so budget is predictable.
2. **Trust semantics:** `status: stale` → verify against listed `sources:` before relying on it; `deprecated` → historical context only; `has_contradictions: true` → read `## Contradictions` before citing the page.
3. **Provenance rule:** wiki pages are compiled claims; on any doubt, the `sources:` raw files win.
4. **Never edit:** wiki pages, hubs, index, log, manifests are read-only to consumers; generated files say so in their header.
5. **Contribution path:** parent-worthy insight → write one OKF-frontmatter draft per insight to `outbox/drafts/YYYY-MM-DD-slug.md` (`requires_human_review: true`); never more than a few per project — drafts are nominations, not a dumping ground.
6. **Query efficiency:** prefer hub navigation for known topics; use search (`sx query` / FTS) for discovery; report unanswerable queries rather than guessing — retrieval gaps are signal for the wiki, not failures to hide.
