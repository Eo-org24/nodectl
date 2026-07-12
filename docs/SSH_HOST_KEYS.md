# SSH Host-Key Enrollment

NodePanel uses Paramiko with `RejectPolicy` and a dedicated `known_hosts` file. Unknown or changed host keys are rejected until an administrator approves the fingerprint.

## Enrollment Procedure

1. Probe the host key:

```bash
curl -fsS -X POST http://127.0.0.1:8000/api/host-keys/probe \
  -H "Content-Type: application/json" \
  -H "X-CSRF-Token: <csrf-token>" \
  -b "nodepanel_session=<session-cookie>" \
  -d '{"host":"10.0.0.10","port":22}'
```

2. Compare the returned SHA-256 fingerprint with an out-of-band source.
3. Approve the fingerprint only after the comparison succeeds:

```bash
curl -fsS -X POST http://127.0.0.1:8000/api/host-keys/approve \
  -H "Content-Type: application/json" \
  -H "X-CSRF-Token: <csrf-token>" \
  -b "nodepanel_session=<session-cookie>" \
  -d '{"target_id":"vm-01","host":"10.0.0.10","port":22}'
```

Approval appends the exact host key to `SSH_KNOWN_HOSTS_PATH` and records the fingerprint change in SQLite.

## Diagnostics

```bash
python -m backend.cli ssh-diagnose --target factory
python -m backend.cli ssh-diagnose --target vm --node-id vm-01 --host 10.0.0.10 --user ubuntu
```

The CLI returns sanitized JSON status only; it does not print private keys, passphrases, or environment dumps.
