from __future__ import annotations

import argparse
import json

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
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    ssh_service = SSHService(settings)
    if args.command == "ssh-diagnose":
        if args.target == "factory":
            target = ssh_service.factory_target()
        else:
            if not args.host or not args.user:
                parser.error("--host and --user are required for VM diagnostics.")
            target = ssh_service.vm_target(node_id=args.node_id, host=args.host, user=args.user, port=args.port)
        print(json.dumps(ssh_service.diagnose(target), indent=2, sort_keys=True))
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
