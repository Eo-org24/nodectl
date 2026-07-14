# Current Objective

> **M-c note:** this file originally described the repo's very first build-out ("wire the htmx
> frontend to the FastAPI backend", phases 1–4). Phases 1–3 are long complete and the repo has
> since grown well beyond this scope (auth, transfers, git deploy keys, host-key trust, terminal
> WS stub, `ucc-contracts` ports, event envelopes, idempotency, diagnostics — see
> `COMPONENT-MAP.md` for the full picture). Rewritten below rather than deleted, since the phase
> list read as still-open work when it wasn't. **The current mission is UCC Stage-1 conformance,
> driven by `AGENTS.md` and the shared roadmap (`docs/roadmap/UCC-Shared-Roadmap-To-Fork.md`), not
> this file.**

## Original phases 1–3: done

Dynamic node rendering, action wiring (`hx-post` to `/api/nodes/{node_name}/action/{action}`),
and hypervisor ground-truth (`get_virsh_list()` / the virsh dashboard tab) are all implemented and
covered by the test suite. `backend/main.py` is now just the ASGI entrypoint
(`from .app import create_app; app = create_app()`) — routes live in `backend/routers/*.py`, not
`main.py`, contrary to what this file and the old `AGENTS.md` used to say.

## Original phase 4 ("Create Worker Form" / `/api/nodes/create`): superseded, not just deferred

This was deferred pending phases 1–3 when first written. It was never built, and under the now-
locked fork scope (`AGENTS.md` §1.1 / roadmap D1: **no real cross-module adapters, no node
provisioning that would require a canonical record store**), a real "create a worker node" flow is
Stage-2 scope, not something to pick up next in this repo as a standalone feature. If this
resurfaces, check it against the roadmap first rather than treating this file as still-live
authorization to build it.

## Where to actually look for current, open work

- `AGENTS.md` §3 "Pending" — this repo's actual outstanding items.
- `COMPONENT-MAP.md` — what every component is and how it's classified.
- The shared roadmap's gate table (§3) and repo lane (§4A) — the source of truth for what's done
  and what's next across all three repos, not a repo-local phase list.
