# Hard Constraints for `nodectl`

> **M-c note:** this file predates the UCC Stage-1 work and described the repo at its very
> first prototype stage (repo named `nodepanel`, one SSH path, no database). Two of the six
> original rules were flatly wrong by the time this was reviewed (M-c, 2026-07-15) — rewritten
> below rather than deleted, since a "hard constraints" doc that's actively false is worse than
> none. **`AGENTS.md` §1 is the current, authoritative rule set — the rules below are this
> repo's older, narrower constraints layered on top of it, kept because they're still true.**

1. **No new frontend framework without asking.** A Vue 3 + Vite frontend already exists and is
   an approved, in-progress exception (`frontend/`, conditionally mounted at `/app`; see
   `Document pack/NodePanel Vue Frontend Redesign.docx` and `COMPONENT-MAP.md`) — this isn't a
   violation of the original rule, it's the one exception the rule always allowed with explicit
   sign-off. Don't add a *second* frontend framework or build tool without asking again.
2. **The default UI stays server-rendered.** `templates/` + `static/` (Jinja2 + `htmx`, minimal
   vanilla JS) is still the UI that ships by default; the Vue frontend above is opt-in and not
   yet the default. Don't add client-side JS frameworks to `templates/`/`static/` itself.
3. **Decoupled execution, but there are now two SSH paths, not one.**
   - `backend/ssh_client.py` (`run_factory_script`, `get_virsh_list`, `get_node_manifests`) uses
     `fabric` and is the **fenced, standalone-only** path — see `AGENTS.md` §3. Never call it from
     a port adapter.
   - `backend/services/ssh.py` (git deploy keys, transfers, host-key probe/approve) uses
     `paramiko` directly and is a separate, newer service layer that didn't exist when this rule
     was first written. Don't route new work through `ssh_client.py`/`fabric` just because that
     was the only path when this file was first drafted — check `COMPONENT-MAP.md` for which
     surface a new feature actually belongs on.
   - Either way: no shell execution code in the frontend or written directly inline in an API
     route. Go through one of the two service layers above.
4. **This claim was false and is removed: "The dashboard does not possess a database."** It
   does — `backend/db.py`, SQLite (`nodepanel.db`), used for git credentials, host keys, and (M-b)
   idempotency records. The remote YAML manifests and the hypervisor are still the sources of
   truth for *node state*; the local database is real and load-bearing for nodectl's own request
   bookkeeping. Don't reintroduce a "no database" assumption anywhere.
5. **Path expansion:** `.env`'s `FACTORY_DIR` (e.g. `FACTORY_DIR=~/nodefactory`) uses `~/`
   deliberately. Don't parse or expand the tilde in Python — pass it through as-is; the remote
   shell expands it. (Unchanged, still accurate.)
6. **HTMX-consumed endpoints return HTML snippets, not JSON.** Endpoints designed to be swapped
   into the DOM by `htmx` (e.g. `virsh list` output, node action results) return `HTMLResponse`
   with pre-formatted HTML, not a JSON body. (Unchanged, still accurate — applies to the
   `templates/`/`static/` UI; the Vue frontend under `frontend/` is a separate presentation layer
   and may use JSON where that makes sense for it.)
