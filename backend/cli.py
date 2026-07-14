from __future__ import annotations

import argparse
import json

from . import diagnostics
from .config import settings
from .services.ssh import SSHService


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="nodepanel")
    subparsers = parser.add_subparsers(dest="command", required=True)

    diagnose = subparsers.add_parser("ssh-diagnose", help="Perform a sanitized SSH authentication test.")
    diagnose.add_argument("--target", choices=["factory", "vm"], required=True)
    diagnose.add_argument("--node-id", default="vm-test")
    diagnose.add_argument("--host")
    diagnose.add_argument("--port", type=int, default=22)
    diagnose.add_argument("--user")

    config_parser = subparsers.add_parser("config", help="Configuration diagnostics.")
    config_sub = config_parser.add_subparsers(dest="config_command", required=True)
    show = config_sub.add_parser("show", help="Print the effective, redacted configuration.")
    # Accepted for parity with the documented invocation; there is no
    # unredacted / non-effective mode, so these are no-op flags rather than
    # a real off switch — a config diagnostic must never be the thing that
    # leaks secret_key/admin_password/viewer_password.
    show.add_argument("--effective", action="store_true")
    show.add_argument("--redacted", action="store_true")

    subparsers.add_parser("module-health", help="Print this module's ucc.module-registration health record.")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    if args.command == "ssh-diagnose":
        ssh_service = SSHService(settings)
        if args.target == "factory":
            target = ssh_service.factory_target()
        else:
            if not args.host or not args.user:
                parser.error("--host and --user are required for VM diagnostics.")
            target = ssh_service.vm_target(node_id=args.node_id, host=args.host, user=args.user, port=args.port)
        print(json.dumps(ssh_service.diagnose(target), indent=2, sort_keys=True))
        return 0
    if args.command == "config" and args.config_command == "show":
        print(json.dumps(diagnostics.effective_config(settings), indent=2, sort_keys=True, default=str))
        return 0
    if args.command == "module-health":
        print(json.dumps(diagnostics.module_health(settings), indent=2, sort_keys=True))
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
