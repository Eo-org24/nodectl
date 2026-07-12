# GETTING STARTED — exact order of operations

## Step 0 — Decisions you make before touching a keyboard (30 min)

1. Answer PROGRESS.md Q-001: vault dialect + language(s). Write the answer into PROGRESS.md §5.
2. Answer Q-002: API provider + exact model version + retention tier. Put the key in your environment (never the repo). Local model prep is deferred to re-entry (amendment §7).
3. Set the M3 correction-time tolerance in your head now; it goes into `part0.yaml` at W-001. (Pre-committed, per the roadmap.)

## Host environment preflight

Before starting an agent, the human provisions the host once:

```bash
sudo apt update
sudo apt install -y git python3-venv python3-pip
```

Create the repo-local virtual environment as the same OS user that will run the agent:

```bash
cd sx-compiler
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -U pip
python --version
python -m pip --version
```

After W-001 creates `pyproject.toml`, `tests/`, and `fixtures/runner.py`, run:

```bash
source .venv/bin/activate
python -m pip install -e ".[dev]"
python -m pytest
python fixtures/runner.py --harness-only
```

Agents must not use `sudo`, system package managers, or unrestricted Git/network access. Missing host tools are reported to the human, not installed by the agent.

## Step 1 — Create the compiler repo (15 min)

```bash
mkdir sx-compiler && cd sx-compiler && git init
mkdir -p docs audits fixtures/batch_a fixtures/batch_b prompts/directives prompts/grammars sx tests
# copy ALL project documents into docs/ (list: STRUCTURE.md §1)
# copy CLAUDE.md, AGENTS.md, AUDIT.md, PROGRESS.md, .gitignore to repo root
git add -A && git commit -m "docs: freeze spec at ADR v2.1"
gh repo create sx-compiler --private --source=. --push
```

Agents authenticate to GitHub via your environment (gh auth / SSH key) — never a token in the repo.

## Step 2 — First builder run (Codex, fire-and-forget)

Prompt: *"Read AGENTS.md, then PROGRESS.md. Take W-001. Fire-and-forget: complete it per protocol. Commit locally. Push only if repo-scoped Git auth is already configured and works without unrestricted access; otherwise stop and report that human push is required. Then hand the baton to auditor."*
That's the entire prompt — the files carry the rest. Repeat the same one-liner for each subsequent W-item.

## Step 3 — First audit run (Claude Code)

Prompt: *"Read CLAUDE.md, then AUDIT.md, then PROGRESS.md. Audit whatever awaits audit."*
Read the report in `audits/`. You skim; you don't re-review the diff yourself unless the report smells off.

## Step 4 — The loop

builder(W-next) → audit → you skim report + answer Questions → repeat. One agent at a time, baton enforced. Expect W-001→W-003 within the first days; then configure `part0.yaml → api.model + key env var` and run **M0**: `python fixtures/runner.py fixtures/batch_a --repeat 2`. M0's result is the first real information the project produces.

## Step 5 — Through M1

Continue W-004→W-014. At W-014 done: run the M1 gate procedures (roadmap Phase 1 exit): determinism repeat, fault-injection set, cache-rebuild recovery — on a **throwaway copy** of a small vault subset. Then Phase 2 items get written into PROGRESS.md (the human seeds them from the roadmap; agents never invent phases).

## When Claude usage runs out

Codex audits under AUDIT.md (see AGENTS.md §Role switch): *"Read AGENTS.md role-switch section and AUDIT.md. Act as auditor for whatever awaits audit."* Cross-model drift is handled by AUDIT.md's fixed template + the Disagreements field; skim those reports slightly more carefully.

## .gitignore (also provided as a file)

```gitignore
# --- derived / disposable (ADR: rebuildable from Markdown) ---
.sx/
*.db
*.db-journal
*.db-wal
embeddings*.jsonl
traces/
staging/
quarantine/
fts-misses.log

# --- python ---
__pycache__/
*.py[cod]
.venv/
venv/
.pytest_cache/
.hypothesis/
*.egg-info/
dist/
build/

# --- models & big binaries (never in git) ---
models/
*.gguf
*.safetensors
*.bin

# --- secrets & env ---
.env
.env.*
*.key
*.pem

# --- OS/editor noise ---
.DS_Store
Thumbs.db
.idea/
.vscode/

# --- explicitly KEPT (do not add): audits/, PROGRESS.md, manifests/*.json*, part0.yaml ---
```

Note for the **bundle** repos (sx-parent): same derived-state ignores apply; `manifests/` including `nominations.jsonl` and `rejection-ledger.jsonl` are tracked — they're portable state, not cache.