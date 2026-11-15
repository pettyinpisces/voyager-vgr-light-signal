#!/usr/bin/env python3
"""Narrow MCP surface for a single fixed VGR actor identity."""

from __future__ import annotations

import json
import os

try:
    from mcp.server.fastmcp import FastMCP
except ImportError:  # MCP 2.x compatibility
    from mcp.server.mcpserver import MCPServer as FastMCP

from vgr_cli import coordinator


ACTOR = os.environ.get("VGR_ACTOR", "").strip().lower()
if not ACTOR:
    raise RuntimeError("VGR_ACTOR must name one fixed actor from config.json")

BRIDGE = coordinator()
if ACTOR not in BRIDGE.allowed_actors:
    raise RuntimeError("VGR_ACTOR is not present in config.json allowed_actors")

mcp = FastMCP(f"VGR Bridge ({ACTOR})")


@mcp.tool()
def vgr_status() -> str:
    """Read the VGR plan, arming window, and this identity's remaining run count."""
    payload = BRIDGE.status()
    remaining = (payload.get("arm") or {}).get("remaining", {}).get(ACTOR, 0)
    return json.dumps(
        {
            "actor": ACTOR,
            "armed": payload["armed"],
            "remaining_for_actor": remaining,
            "message": payload["plan"]["message"],
            "morse": payload["plan"]["morse"],
            "duration_seconds": payload["plan"]["duration_seconds"],
        },
        indent=2,
    )


@mcp.tool()
def transmit_vgr() -> str:
    """Send one complete, physically armed VGR Morse transmission as this fixed identity."""
    return json.dumps(BRIDGE.transmit(ACTOR), indent=2)


@mcp.tool()
def stop_vgr() -> str:
    """Request an immediate stop; this is always available, even when VGR is disarmed."""
    BRIDGE.request_stop()
    return "Immediate VGR stop requested; the signal light was commanded off."


if __name__ == "__main__":
    mcp.run()

