# Git Deploy Keys

NodePanel defaults to per-repository SSH deploy keys. It does not store the private key in SQLite, the ledger, HTML, or API responses.

## Provisioning Flow

1. Generate one deploy key per repository and per managed environment.
2. Upload the private key only for the provisioning request.
3. NodePanel writes the key to `~/.ssh/nodepanel/<credential-id>.tmp` through SFTP, `chmod 0600`, and renames it atomically.
4. NodePanel writes a dedicated GitHub `known_hosts` file on the VM.
5. NodePanel configures repository-local `core.sshCommand` with:
   - the exact deploy key path
   - `IdentitiesOnly=yes`
   - `StrictHostKeyChecking=yes`
   - the exact `UserKnownHostsFile`
6. NodePanel runs `git ls-remote origin HEAD`.
7. The credential is marked `live` only if `ls-remote` succeeds.

## Revocation / Scrub

1. Delete the remote private key.
2. Remove the repository-local `core.sshCommand`.
3. Re-run `git ls-remote origin HEAD`.
4. Mark the credential `scrubbed` only if authentication now fails.

Deleting NodePanel metadata alone does not revoke a deploy key at GitHub. Remove or revoke the key in GitHub as part of the same change window.
