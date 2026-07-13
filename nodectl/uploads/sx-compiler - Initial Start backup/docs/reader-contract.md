# Reader Contract

**Status:** STUB — outline only. Finalized in Phase 4.1.

This file is the consumption-side mirror of `schema.md`. It is injected into any agent or project that mounts the wiki.

## Outline

1. Routing: read `index.md`, follow one hub, open at most the configured number of pages.
2. Trust semantics: `status: stale` requires source verification; `deprecated` is historical; `has_contradictions: true` requires reading contradictions before citing.
3. Provenance: wiki pages are compiled claims; raw `sources:` win on doubt.
4. Never edit: wiki pages, hubs, index, log, and manifests are read-only to consumers.
5. Contribution path: parent-worthy insight becomes one OKF-frontmatter draft in `outbox/drafts/`, with `requires_human_review: true`.
6. Query efficiency: prefer hub navigation for known topics; use search for discovery; report unanswerable queries instead of guessing.