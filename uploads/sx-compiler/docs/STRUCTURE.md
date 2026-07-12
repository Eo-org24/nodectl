# STRUCTURE — Repository and Bundle Layout

Two distinct things live in two distinct git repositories: the **compiler repo** (code, prompts, fixtures, docs — what Codex and Claude Code work on) and the **data bundles** (your vault and the sx bundles — what the compiler works on). Never merge them: the compiler is shareable/public-able; the bundles are your knowledge.

## 1. Compiler repo (`sx-compiler/`)

```
sx-compiler/
├── README.md                  # short; points to docs/
├── CLAUDE.md                  # Claude Code instructions (auditor default)
├── AGENTS.md                  # Codex instructions (builder default)
├── AUDIT.md                   # role protocol for whichever agent audits
├── PROGRESS.md                # inter-agent ledger (baton, work items, questions)
├── .gitignore
├── pyproject.toml
├── part0.yaml                 # ALL operating constants; the only place numbers live
├── sx/                        # the package
│   ├── cli.py                 # sx status | ingest | lint | review | rebuild | query
│   ├── config.py              # part0 loader; pinned-profile struct
│   ├── change_detect.py       # hashing, deletion/rename semantics (D5)
│   ├── chunker.py             # 400–800 token units; sentence-marker renderer
│   ├── retrieval/
│   │   ├── anchors.py         # exact anchor table build + live demotion (D24)
│   │   ├── fts.py             # FTS5 two-pass ladder (D6)
│   │   ├── vectors.py         # Phase 2: embeddings + brute-force cosine (D7)
│   │   ├── fuse.py            # Python RRF (D8)
│   │   └── pack.py            # budgeted pack assembly + trace writer (D5)
│   ├── control_plane.py       # grammar-constrained routing call (D3)
│   ├── data_plane.py          # synthesis calls incl. split-pair orchestration (D2e)
│   ├── residual.py            # span validation, slicing, lifecycle (D3/D5)
│   ├── digest.py              # entity-digest extractor + delta logger (D11/D18)
│   ├── linter/                # severity-classed checks (D20), one module per family
│   ├── staging.py             # staging dir, atomic rename, concurrency check (D2a–c)
│   ├── postpass.py            # frontmatter stamping per ownership matrix (D21)
│   ├── queue.py               # state machine incl. residual_pending (D19)
│   ├── artifacts.py           # hubs/index/log/manifest generation (D10)
│   ├── nominations.py         # triggers, dedup key, rejection ledger (D23)
│   └── cache/                 # SQLite schema + surgical refresh (D17)
├── prompts/
│   ├── control_plane.txt
│   ├── data_plane_system.txt
│   ├── directives/            # merge / create / split_child / split_parent / contradiction
│   └── grammars/              # GBNF for the decision object
├── fixtures/
│   ├── runner.py              # loads YAML, renders packs, scores; --repeat
│   ├── batch_a/               # 13 files, IDs stable forever
│   └── batch_b/
├── tests/                     # unit + property tests (see TESTING.md; distinct from fixtures)
├── audits/                    # NNN-report.md, append-only (see AUDIT.md)
└── docs/                      # every project document, canonical copies
    ├── BLUEPRINT_V2.md
    ├── ADR_v2.1.md
    ├── ADR_v2.2_API_Mode_Amendment.md
    ├── DOC_MAINTENANCE.md
    ├── implementation-roadmap.md
    ├── v0-golden-corpus-and-control-plane-prompt.md
    ├── data-plane-synthesis-prompt.md
    ├── fixture-batch-A.md
    ├── INGESTION.md
    ├── TESTING.md
    ├── PROJECT_PRIMER.md
    ├── FUTURE_RISKS.md
    └── reader-contract.md     # finalized Phase 4.1
```

`archive/  # superseded docs live here, outside the loading path`

Module boundaries mirror ADR decisions on purpose: an auditor can map any diff to the decision it implements, and "which decision does this code serve?" always has an answer. Code that serves no decision is scope creep by definition.

## 2. Data bundles

```
/vault/                        # human-canonical; agents read-only except drafts/
├── decisions/  glossary/  projects/  incidents/
└── drafts/                    # the only agent-writable return channel

/sx-parent/                    # a git repo of its own
├── raw/                       # exported canonical source snapshots
├── schema/
│   ├── schema.md              # compiler contract + editorial policy; version-pinned
│   └── reader-contract.md
├── wiki/
│   ├── index.md               # generated
│   ├── log.md                 # generated, append-only (digest deltas live here)
│   ├── hubs/                  # generated
│   └── pages/                 # the only LLM-mutable directory (ALLOWED_TARGETS)
├── manifests/
│   ├── source-manifest.json
│   ├── page-manifest.json     # includes derived link graph (replaces related:)
│   ├── nominations.jsonl
│   ├── rejection-ledger.jsonl
│   └── needs-review.json
└── .sx/                       # gitignored, disposable, rebuildable
    ├── cache/index.db         # FTS + chunks + links + aliases (+ embeddings later)
    ├── cache/traces/
    ├── staging/
    ├── quarantine/
    └── fts-misses.log

/sx-child/<project-slug>/      # compiler child: mirrors sx-parent + outbox/ + projection-manifest.json
/projects/<slug>/              # consumer child: just a project dir containing
    ├── .sx-projection/        # read-only projected pages or a mount reference
    ├── reader-contract.md     # copied, version-pinned
    └── outbox/drafts/
```

## 3. Wiki-internal structure (what a page looks like)

- **Pages:** frontmatter per the D21 ownership matrix; lead paragraph defining the concept standalone; `##` sections with stable names; wikilinks; optional `## Contradictions`; ≤ cap tokens.
- **Hubs:** generated topical page tables — one line per member page (title + summary), DO-NOT-EDIT header. The reader's routing layer and the control plane's `hub_hint` targets.
- **Index:** generated catalog of hubs, not of pages (a page-level index recreates the monolithic-index scaling failure).
- **Log:** append-only operations + digest-delta lines — the human's "what changed semantically" review surface.
- **Naming:** kebab-case slugs = filenames; slug uniqueness enforced; titles admission-gated (D24).

## 4. Git topology

- `sx-compiler`: GitHub-hosted; agents push here. Single `main`; sequential agent turns via the PROGRESS.md baton (no concurrent pushes).
- `sx-parent` and `/vault`: local repos (private by default); optional private remote as backup. Agents never push these during Phases 0–2; the compiler commits to `sx-parent` mechanically per batch (one commit per promoted batch, message = batch ID + digest-delta summary).
- Bundles never submodule into the compiler repo.
