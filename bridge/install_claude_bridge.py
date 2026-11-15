#!/usr/bin/env python3
"""Add one local VGR MCP server without replacing existing Claude servers."""

from __future__ import annotations

import argparse
import json
import os
import shutil
from datetime import datetime
from pathlib import Path


DEFAULT_CONFIG = Path.home() / "Library/Application Support/Claude/claude_desktop_config.json"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Add one fixed-identity VGR launcher to Claude Desktop"
    )
    parser.add_argument(
        "--command",
        required=True,
        help="absolute path to the fixed-identity launcher",
    )
    parser.add_argument("--server-name", default="vgr-companion-a")
    parser.add_argument(
        "--config",
        type=Path,
        default=Path(os.environ.get("CLAUDE_CONFIG_PATH", DEFAULT_CONFIG)),
    )
    return parser


def install(config: Path, server_name: str, command: str) -> Path | None:
    command_path = Path(command).expanduser()
    if not command_path.is_absolute():
        raise ValueError("--command must be an absolute path")

    payload = json.loads(config.read_text(encoding="utf-8")) if config.exists() else {}
    servers = payload.setdefault("mcpServers", {})
    if not isinstance(servers, dict):
        raise ValueError("mcpServers must be a JSON object")

    desired = {"command": str(command_path), "args": []}
    if servers.get(server_name) == desired:
        return None

    backup = None
    if config.exists():
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        backup = config.with_name(f"claude_desktop_config.pre-vgr-{timestamp}.json")
        shutil.copy2(config, backup)

    servers[server_name] = desired
    config.parent.mkdir(parents=True, exist_ok=True)
    temporary = config.with_suffix(config.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    os.chmod(temporary, 0o600)
    os.replace(temporary, config)
    return backup


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    backup = install(args.config, args.server_name, args.command)
    if backup:
        print(f"Backup created: {backup.name}")
    print(f"Installed {args.server_name}. Fully quit and reopen Claude Desktop.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
