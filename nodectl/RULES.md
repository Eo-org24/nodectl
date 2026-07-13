# Hard Constraints for `nodepanel`

1. [cite_start]**No Frontend Frameworks without user Asking:** Do not install, suggest, or configure React, Vue, npm, Webpack, or Vite without user asking[cite: 24].
2. [cite_start]**No JavaScript (Mostly):** Rely entirely on `htmx` attributes (`hx-get`, `hx-post`, `hx-target`, `hx-swap`) for interactivity[cite: 45]. Write vanilla JS only if strictly necessary for UI state that htmx cannot handle natively.
3. **Decoupled Execution:** Do not write shell execution code in the frontend or directly in the API routes. [cite_start]All system commands must be routed through the `run_factory_script` or `get_virsh_list` functions in `backend/ssh_client.py` using `fabric`[cite: 46, 105].
4. **Read-Only State:** The dashboard does not possess a database. [cite_start]The sources of truth are the remote YAML files and the remote hypervisor[cite: 34].
5. **Path Expansion:** The `.env` file uses `~/` for the factory directory path (e.g., `FACTORY_DIR=~/nodefactory`). Do not attempt to parse or expand this tilde in Python. [cite_start]Pass it directly to Fabric; the remote bash shell will handle the expansion natively[cite: 103].
6. [cite_start]**HTML Snippet Responses:** For endpoints designed to be consumed by `htmx` (like the `virsh list` output), return `HTMLResponse` containing pre-formatted HTML snippets, rather than JSON objects[cite: 107].