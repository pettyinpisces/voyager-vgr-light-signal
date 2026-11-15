#!/usr/bin/env python3
"""Command-line setup, arming, testing, and transmission for the VGR bridge."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from hue_v1 import HueV1Controller
from vgr_core import DEFAULT_ACTORS, VGRCoordinator, plan_payload


ROOT = Path(__file__).resolve().parent
CONFIG_PATH = ROOT / "config.json"
RUNTIME_DIR = ROOT / "runtime"


def load_config() -> dict:
    try:
        return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise RuntimeError("config.json does not exist; run the pair command first") from exc


def save_config(config: dict) -> None:
    temporary = CONFIG_PATH.with_suffix(".tmp")
    temporary.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")
    os.chmod(temporary, 0o600)
    os.replace(temporary, CONFIG_PATH)


def coordinator() -> VGRCoordinator:
    config = load_config()
    controller = HueV1Controller(
        config["bridge_ip"],
        config["application_key"],
        config.get("light_name", "VGR"),
    )
    return VGRCoordinator(
        controller,
        RUNTIME_DIR,
        float(config.get("unit_seconds", 0.5)),
        int(config.get("brightness", 254)),
        config.get("allowed_actors", DEFAULT_ACTORS),
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Transmit VGR in Morse code through one Hue light")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("plan", help="print the inert VGR timing plan")
    pair = sub.add_parser("pair", help="pair after pressing the Hue Bridge link button")
    pair.add_argument("bridge_ip")
    pair.add_argument("--light-name", default="VGR")

    sub.add_parser("check", help="find exactly one configured Hue light without changing it")
    arm = sub.add_parser("arm", help="physically authorize a small number of transmissions")
    arm.add_argument("--actors", nargs="+", default=["companion-a", "companion-b"])
    arm.add_argument("--minutes", type=int, default=30)
    arm.add_argument("--runs-each", type=int, default=1)
    sub.add_parser("disarm", help="disarm and request stop")
    sub.add_parser("status", help="show arming and timing status")
    transmit = sub.add_parser("transmit", help="send one complete VGR sequence")
    transmit.add_argument("actor")
    sub.add_parser("stop", help="request an immediate stop and turn the signal light off")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "plan":
            print(json.dumps(plan_payload(), indent=2))
            return 0
        if args.command == "pair":
            application_key = HueV1Controller.pair(args.bridge_ip)
            config = {
                "bridge_ip": args.bridge_ip,
                "application_key": application_key,
                "light_name": args.light_name,
                "unit_seconds": 0.5,
                "brightness": 254,
                "allowed_actors": list(DEFAULT_ACTORS),
            }
            save_config(config)
            details = coordinator().controller.describe()
            print(json.dumps({"paired": True, "light": details}, indent=2))
            return 0

        bridge = coordinator()
        if args.command == "check":
            print(json.dumps(bridge.controller.describe(), indent=2))
        elif args.command == "arm":
            print(json.dumps(bridge.arm(args.actors, args.minutes, args.runs_each), indent=2))
        elif args.command == "disarm":
            bridge.disarm()
            print("VGR disarmed and stop requested.")
        elif args.command == "status":
            print(json.dumps(bridge.status(), indent=2))
        elif args.command == "transmit":
            print(json.dumps(bridge.transmit(args.actor), indent=2))
        elif args.command == "stop":
            bridge.request_stop()
            print("Immediate VGR stop requested; the signal light was commanded off.")
        return 0
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

