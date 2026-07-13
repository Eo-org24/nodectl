# Current Objective: Wire the htmx Frontend to the FastAPI Backend

You are building the UI layer for an existing FastAPI backend. The backend is already capable of listing nodes and executing remote scripts via SSH. Your job is to connect the provided HTML template to these API endpoints.

## Phase 1: Dynamic Node Rendering (In Scope)
- Convert `templates/index.html` into a proper Jinja2 template.
- Update `backend/main.py`'s `/` route to return a `TemplateResponse` passing the output of `get_node_manifests()` into the HTML template.
- Write a Jinja2 `{% for node in nodes %}` loop in the HTML to dynamically render a card for every active node.

## Phase 2: Action Wiring (In Scope)
- [cite_start]Ensure the buttons on the node cards (Assign, Snapshot, Destroy) use `hx-post` to hit the `/api/nodes/{node_name}/action/{action}` endpoints[cite: 52].
- [cite_start]Ensure the API returns HTML snippets (or plaintext wrapped in HTML) so `htmx` can swap the stdout/stderr logs directly into the `#terminal-output` div[cite: 53].

## Phase 3: Hypervisor Ground Truth (In Scope)
- [cite_start]Implement `get_virsh_list()` in `ssh_client.py` using Fabric to run `virsh list --all`[cite: 105].
- [cite_start]Expose an endpoint `/api/hypervisor/vms` returning an `HTMLResponse` with the formatted output[cite: 107].
- [cite_start]Add a "Run 'virsh list'" button to the dashboard using `hx-get` to fetch and display this hypervisor truth state[cite: 109, 110].

## Phase 4: Create Worker Form (Deferred / Out of Scope)
- Build a small form at the top of the dashboard to accept a `project_name`.
- Wire it via `hx-post` to the `/api/nodes/create` endpoint.
- *(Do not begin Phase 4 until Phase 1, 2, and 3 are fully tested and committed).*