# Git Deploy Keys

NodePanel defaults to per-repository SSH deploy keys. It does not store the private key in SQLite, the ledger, HTML, or API responses.

## Provisioning Flow

1. Generate one deploy key per repository and per managed environment.
2. Upload the private key only for the provisioning request.
3. NodePanel writes the key to `~/.ssh/nodectl/<credential-id>.tmp` through SFTP, `chmod 0600`, and renames it atomically.
4. NodePanel writes a dedicated GitHub `known_hosts` file on the VM.
5. NodePanel configures repository-local `core.sshCommand` with:
   - the exact deploy key path
   - `IdentitiesOnly=yes`
   - `StrictHostKeyChecking=yes`
   - the exact `UserKnownHostsFile`
6. NodePanel runs `git ls-remote origin HEAD`.
7. The credential is marked `live` only if `ls-remote` succeeds.

## Revocation / Scrub

1. Delete the remote private key — both at the current `~/.ssh/nodectl/` path and the legacy `~/.ssh/nodepanel/` path, since a credential provisioned before the D5 rename still has its key under the old path (`rm -f` is a no-op if a given path doesn't exist).
2. Remove the repository-local `core.sshCommand`.
3. Re-run `git ls-remote origin HEAD`.
4. Mark the credential `scrubbed` only if authentication now fails.

Deleting NodePanel metadata alone does not revoke a deploy key at GitHub. Remove or revoke the key in GitHub as part of the same change window.
