# VENDORED MODULE — source of truth lives in the soloctl repo.
# Do NOT edit in place. Change the source, then re-copy into each consumer
# (nodepanel, soloctl). Schema contract: LEDGER_SCHEMA.md v1.
#
# Zero third-party dependencies. Python 3.11+ (uses tomllib, datetime UTC).
"""
Append-only run-ledger writer.

One object per line, UTF-8, '\n'-terminated JSONL. SQLite is a separate,
rebuildable index (not this module's job). This module only appends.

Design invariants enforced here (see LEDGER_SCHEMA.md):
  - append-only: open O_APPEND, one atomic write() per entry
  - scrub-before-write: params + note + free text scrubbed automatically
  - metadata-not-content: serialized entry capped, oversize -> fallback entry
  - tolerant reader, strict writer: we emit exactly the v1 envelope
"""

from __future__ import annotations

import io
import json
import os
import re
import secrets
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

SCHEMA_VERSION = 1

# Per-entry serialized size ceiling. Entries at/under this are atomic on a
# single POSIX write(); over it we fall back to a minimal entry (never drop).
MAX_ENTRY_BYTES = 8 * 1024
# params must stay small (schema §2.3). Enforced pre-serialization.
MAX_PARAMS_BYTES = 4 * 1024
MAX_NOTE_CHARS = 1024

VALID_STATUS = frozenset({"ok", "fail", "denied", "error", "partial"})
VALID_TOOL = frozenset({"nodepanel", "soloctl"})  # readers accept more; writers use these


# --------------------------------------------------------------------------
# ULID  (Crockford base32, 48-bit millisecond time + 80-bit randomness)
# --------------------------------------------------------------------------
_CROCKFORD = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"  # no I L O U


def _encode_crockford(value: int, length: int) -> str:
    out = bytearray(length)
    for i in range(length - 1, -1, -1):
        out[i] = ord(_CROCKFORD[value & 0x1F])
        value >>= 5
    return out.decode("ascii")


def new_ulid(now_ms: int | None = None) -> str:
    """26-char lexicographically-sortable ULID. Monotonic within a process
    for entries sharing a millisecond, so ordering never ties."""
    ms = int(time.time() * 1000) if now_ms is None else now_ms
    global _last_ms, _last_rand
    if ms == _last_ms:
        _last_rand += 1  # monotonic bump within the same ms
        rand = _last_rand
    else:
        _last_ms = ms
        rand = secrets.randbits(80)
        _last_rand = rand
    return _encode_crockford(ms, 10) + _encode_crockford(rand & ((1 << 80) - 1), 16)


_last_ms = -1
_last_rand = 0


# --------------------------------------------------------------------------
# Scrubbing  (schema §10) — load-bearing, runs on every write
# --------------------------------------------------------------------------
# Built-in fallback patterns. In production, load the shared TOML instead
# (load_scrub_patterns) so a new pattern lands in every consumer at once.
_DEFAULT_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("private-key", re.compile(
        r"-----BEGIN [A-Z ]*PRIVATE KEY-----.*?-----END [A-Z ]*PRIVATE KEY-----",
        re.DOTALL)),
    ("gh-pat", re.compile(r"github_pat_[A-Za-z0-9_]{20,}")),
    ("gh-token", re.compile(r"gh[pousr]_[A-Za-z0-9]{36,}")),
    ("aws-key", re.compile(r"AKIA[0-9A-Z]{16}")),
    ("ts-key", re.compile(r"tskey-[a-z]+-[A-Za-z0-9-]{16,}")),
    ("bearer", re.compile(r"Bearer\s+[A-Za-z0-9._~+/=-]{16,}")),
    # value-only: keep the key name, redact the value after = or :
    ("kv-secret", re.compile(
        r"(?i)\b(password|passwd|pwd|token|secret|api[_-]?key)\b(\s*[=:]\s*)(\S+)")),
]


def load_scrub_patterns(toml_path: str | os.PathLike[str]
                        ) -> list[tuple[str, re.Pattern[str]]]:
    """Load [patterns] label = regex from the shared scrub-patterns.toml.
    Falls back to built-ins if the file is missing so logging never breaks."""
    try:
        import tomllib
        data = tomllib.loads(Path(toml_path).read_text(encoding="utf-8"))
    except (OSError, ValueError, ModuleNotFoundError):
        return list(_DEFAULT_PATTERNS)
    pats: list[tuple[str, re.Pattern[str]]] = []
    for label, rx in (data.get("patterns") or {}).items():
        try:
            pats.append((label, re.compile(rx, re.IGNORECASE | re.DOTALL)))
        except re.error:
            continue  # a bad pattern must not disable the whole logger
    return pats or list(_DEFAULT_PATTERNS)


def _last4(s: str) -> str:
    s = s.strip()
    return s[-4:] if len(s) >= 4 else "----"


def scrub_text(text: str,
               patterns: list[tuple[str, re.Pattern[str]]] | None = None) -> str:
    """Replace secrets with [REDACTED:<label>:<last4>]. Correlatable, useless
    to replay. kv-secret keeps the key name and redacts only the value."""
    pats = patterns if patterns is not None else _DEFAULT_PATTERNS
    for label, rx in pats:
        if label == "kv-secret":
            text = rx.sub(
                lambda m: f"{m.group(1)}{m.group(2)}"
                          f"[REDACTED:{label}:{_last4(m.group(3))}]",
                text)
        else:
            text = rx.sub(
                lambda m, _l=label: f"[REDACTED:{_l}:{_last4(m.group(0))}]", text)
    return text


def scrub_obj(obj: Any,
              patterns: list[tuple[str, re.Pattern[str]]] | None = None) -> Any:
    """Recursively scrub every string leaf in a JSON-serializable structure.
    Dict keys are left intact (they are field names, not values)."""
    if isinstance(obj, str):
        return scrub_text(obj, patterns)
    if isinstance(obj, dict):
        return {k: scrub_obj(v, patterns) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [scrub_obj(v, patterns) for v in obj]
    return obj


# --------------------------------------------------------------------------
# Writer
# --------------------------------------------------------------------------
def _now_rfc3339() -> str:
    # local time with numeric offset, ms precision (schema §4)
    dt = datetime.now().astimezone()
    return dt.isoformat(timespec="milliseconds")


class Ledger:
    """Append-only ledger writer for one tool. Instantiate once per process.

        led = Ledger(root="/var/lib/nodepanel", tool="nodepanel",
                     scrub_patterns_path="/var/lib/nodepanel/library/"
                                         ".soloctl/scrub-patterns.toml")
        led.write(actor="human:sarge", action="payload.fire",
                  target="node:ai-worker-03", status="ok", exit=0,
                  params={"script": "join.sh", "review": "approved"})

    root layout: <root>/ledger/YYYY-MM.jsonl  (monthly rotation).
    fsync defaults True for nodepanel (security log), pass fsync=False for
    soloctl if append latency matters.
    """

    def __init__(self, root: str | os.PathLike[str], tool: str,
                 scrub_patterns_path: str | os.PathLike[str] | None = None,
                 fsync: bool = True) -> None:
        self.ledger_dir = Path(root) / "ledger"
        self.ledger_dir.mkdir(parents=True, exist_ok=True)
        # 0750 dir per schema §3
        try:
            os.chmod(self.ledger_dir, 0o750)
        except OSError:
            pass
        self.tool = tool
        self.fsync = fsync
        self._patterns = (load_scrub_patterns(scrub_patterns_path)
                          if scrub_patterns_path else list(_DEFAULT_PATTERNS))

    # -- path -------------------------------------------------------------
    def _current_file(self, ts_iso: str) -> Path:
        # YYYY-MM from the entry timestamp, not import time — a process that
        # runs across a month boundary rotates correctly.
        return self.ledger_dir / f"{ts_iso[:7]}.jsonl"

    # -- public API -------------------------------------------------------
    def write(self, *, actor: str, action: str, target: str, status: str,
              params: dict[str, Any] | None = None,
              exit: int | None = None,          # noqa: A002 (schema field name)
              duration_s: float | None = None,
              artifacts: Iterable[str] | None = None,
              links: dict[str, Any] | None = None,
              note: str = "") -> str:
        """Append one entry. Returns the entry id. Never raises on a logging
        problem — falls back to a minimal error entry so events are not lost."""
        ts = _now_rfc3339()
        entry_id = new_ulid()
        try:
            entry = self._build(entry_id, ts, actor, action, target, status,
                                params, exit, duration_s, artifacts, links, note)
            line = json.dumps(entry, ensure_ascii=False,
                              separators=(",", ":")) + "\n"
            data = line.encode("utf-8")
            if len(data) > MAX_ENTRY_BYTES:
                data = self._fallback(entry_id, ts, action, target,
                                      reason="entry_too_large")
            self._append(self._current_file(ts), data)
            return entry_id
        except Exception as exc:  # logging must not take down the caller
            try:
                self._append(self._current_file(ts),
                             self._fallback(entry_id, ts, action, target,
                                            reason=type(exc).__name__))
            except Exception:
                pass  # give up silently rather than propagate
            return entry_id

    # -- internals --------------------------------------------------------
    def _build(self, entry_id, ts, actor, action, target, status,
               params, exit_, duration_s, artifacts, links, note) -> dict:
        if status not in VALID_STATUS:
            # don't reject — record the intent and flag it, strict-writer-lite
            note = (note + f" [invalid-status:{status}]").strip()
            status = "error"

        params = params or {}
        scrubbed_params = scrub_obj(params, self._patterns)
        # enforce the params size ceiling (schema §2.3) AFTER scrubbing
        pj = json.dumps(scrubbed_params, ensure_ascii=False,
                        separators=(",", ":"))
        if len(pj.encode("utf-8")) > MAX_PARAMS_BYTES:
            scrubbed_params = {"_truncated": True,
                               "_note": "params exceeded 4KB; see artifacts"}

        note = scrub_text(note, self._patterns)[:MAX_NOTE_CHARS]

        entry: dict[str, Any] = {
            "v": SCHEMA_VERSION,
            "id": entry_id,
            "ts": ts,
            "tool": self.tool,
            "actor": actor,
            "action": action,
            "target": target,
            "params": scrubbed_params,
            "status": status,
        }
        # optional fields: present only when meaningful (schema §4)
        if exit_ is not None:
            entry["exit"] = int(exit_)
        if duration_s is not None:
            entry["duration_s"] = round(float(duration_s), 3)
        if artifacts:
            entry["artifacts"] = list(artifacts)
        if links:
            entry["links"] = scrub_obj(dict(links), self._patterns)
        if note:
            entry["note"] = note
        return entry

    def _fallback(self, entry_id, ts, action, target, reason) -> bytes:
        """Minimal, always-serializable entry so an event is never silently
        dropped (schema §11.3)."""
        obj = {
            "v": SCHEMA_VERSION, "id": entry_id, "ts": ts, "tool": self.tool,
            "actor": "system", "action": "ledger.error", "target": target,
            "params": {"reason": str(reason)[:200], "for_action": action},
            "status": "error",
        }
        return (json.dumps(obj, ensure_ascii=False,
                           separators=(",", ":")) + "\n").encode("utf-8")

    def _append(self, path: Path, data: bytes) -> None:
        """Single atomic append. O_APPEND guarantees the write starts at EOF
        even with concurrent writers; one write() call keeps sub-page-size
        entries un-interleaved on local POSIX filesystems."""
        flags = os.O_WRONLY | os.O_APPEND | os.O_CREAT
        fd = os.open(path, flags, 0o640)
        try:
            os.write(fd, data)
            if self.fsync:
                os.fsync(fd)
        finally:
            os.close(fd)


# --------------------------------------------------------------------------
# Reader helper (tolerant) — for reindexers and quick tails.
# --------------------------------------------------------------------------
def read_entries(path: str | os.PathLike[str]) -> Iterable[dict]:
    """Yield entries from one .jsonl file. Tolerates a torn final line
    (partial write); surfaces mid-file parse errors as ledger.error stand-ins
    rather than aborting the whole file (schema §12)."""
    p = Path(path)
    opener: Any = io.open
    if p.suffix == ".gz":
        import gzip
        opener = gzip.open
    with opener(p, "rt", encoding="utf-8") as fh:
        lines = fh.readlines()
    last = len(lines) - 1
    for i, line in enumerate(lines):
        line = line.rstrip("\n")
        if not line:
            continue
        try:
            yield json.loads(line)
        except json.JSONDecodeError:
            if i == last:
                break  # torn final line: expected, skip quietly
            yield {"v": SCHEMA_VERSION, "id": f"UNPARSED-{i}", "tool": "?",
                   "actor": "system", "action": "ledger.error",
                   "target": "?", "status": "error",
                   "params": {"reason": "unparseable_line", "line_no": i}}
