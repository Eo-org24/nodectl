# Agent Operating Manual — Node Factory Control Plane

## Where you are
You are working on the `nodepanel` repository. This is a lightweight web dashboard that serves as a control plane for a homelab VM factory.

## The Architecture
- **Backend:** FastAPI (Python). [cite_start]It executes bash scripts and system commands on a remote host via SSH using the `fabric` library[cite: 21, 29, 64].
- [cite_start]**Frontend:** HTML templates using `htmx` and Tailwind CSS[cite: 23].
- **Rule of Thumb:** The UI knows nothing. [cite_start]It is purely a dumb viewer for the FastAPI backend[cite: 33, 40].

## The Two Sources of Truth
[cite_start]You will be interacting with two distinct states on the remote host[cite: 98]:
1. [cite_start]**The Factory State:** Parsed from `node.yaml` manifests (what the factory *thinks* exists)[cite: 40].
2. [cite_start]**The Hypervisor State:** Queried directly via `virsh list --all` (the actual ground truth)[cite: 105]. [cite_start]Cross-referencing these is how the admin spots drifted nodes[cite: 99].

## Ground truth files (read in this order)
1. `MISSION.md`   — Your current objective and phase.
2. `RULES.md`     — Hard system constraints. Do not violate these.

## Workflow
- Read the FastAPI backend code in `backend/main.py` to understand the available API routes.
- Ensure you are working on a dedicated branch off `main`.
- Make small, testable commits. [cite_start]You can run the backend locally using `uvicorn backend.main:app --reload` to test your HTML/htmx changes[cite: 81].