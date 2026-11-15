#!/usr/bin/env python3
"""Small Philips Hue local API v1 client for one exact light name."""

from __future__ import annotations

import json
import ssl
import urllib.error
import urllib.request
from typing import Any


class HueAPIError(RuntimeError):
    pass


class HueV1Controller:
    def __init__(self, bridge_ip: str, application_key: str, light_name: str = "VGR") -> None:
        self.bridge_ip = bridge_ip.strip()
        self.application_key = application_key.strip()
        self.light_name = light_name.strip()
        if not self.bridge_ip or not self.application_key or not self.light_name:
            raise ValueError("bridge_ip, application_key, and light_name are required")
        self.bridge_url = self._bridge_url(self.bridge_ip)
        self.base_url = f"{self.bridge_url}/api/{self.application_key}"
        self._light_id: str | None = None

    @classmethod
    def pair(
        cls,
        bridge_ip: str,
        device_type: str = "vgr_light_signal#local_controller",
    ) -> str:
        """Create an application key after the Hue Bridge link button is pressed."""
        response = cls._request_absolute(
            f"{cls._bridge_url(bridge_ip)}/api",
            "POST",
            {"devicetype": device_type},
        )
        if not isinstance(response, list) or not response:
            raise HueAPIError(f"Unexpected pairing response: {response!r}")
        first = response[0]
        if "error" in first:
            raise HueAPIError(first["error"].get("description", "Hue pairing failed"))
        try:
            return str(first["success"]["username"])
        except (KeyError, TypeError) as exc:
            raise HueAPIError(f"Pairing did not return an application key: {response!r}") from exc

    def find_light(self) -> tuple[str, dict[str, Any]]:
        lights = self._request("/lights", "GET")
        matches = [
            (str(light_id), payload)
            for light_id, payload in lights.items()
            if str(payload.get("name", "")).casefold() == self.light_name.casefold()
        ]
        if len(matches) != 1:
            names = sorted(str(payload.get("name", light_id)) for light_id, payload in lights.items())
            raise HueAPIError(
                f"Expected exactly one Hue light named {self.light_name!r}; found {len(matches)}. "
                f"Bridge lights: {', '.join(names)}"
            )
        self._light_id = matches[0][0]
        return matches[0]

    def snapshot(self) -> dict:
        light_id, light = self.find_light()
        return {"light_id": light_id, "state": dict(light.get("state", {}))}

    def set_signal(self, on: bool, brightness: int = 254) -> None:
        light_id = self._light_id or self.find_light()[0]
        payload: dict[str, Any] = {"on": bool(on), "transitiontime": 0}
        if on:
            payload["bri"] = int(brightness)
        self._set_state(light_id, payload)

    def restore(self, snapshot: dict) -> None:
        light_id = str(snapshot["light_id"])
        state = dict(snapshot.get("state", {}))
        payload: dict[str, Any] = {
            "on": bool(state.get("on", False)),
            "transitiontime": 0,
        }
        if payload["on"] and "bri" in state:
            payload["bri"] = int(state["bri"])
        colormode = state.get("colormode")
        if payload["on"] and colormode == "xy" and "xy" in state:
            payload["xy"] = state["xy"]
        elif payload["on"] and colormode == "ct" and "ct" in state:
            payload["ct"] = int(state["ct"])
        elif payload["on"] and colormode == "hs":
            if "hue" in state:
                payload["hue"] = int(state["hue"])
            if "sat" in state:
                payload["sat"] = int(state["sat"])
        self._set_state(light_id, payload)

    def describe(self) -> dict:
        light_id, light = self.find_light()
        return {
            "bridge_ip": self.bridge_ip,
            "light_id": light_id,
            "name": light.get("name"),
            "modelid": light.get("modelid"),
            "reachable": light.get("state", {}).get("reachable"),
            "on": light.get("state", {}).get("on"),
            "brightness": light.get("state", {}).get("bri"),
        }

    def _set_state(self, light_id: str, payload: dict) -> None:
        response = self._request(f"/lights/{light_id}/state", "PUT", payload)
        if isinstance(response, list):
            errors = [entry["error"] for entry in response if isinstance(entry, dict) and "error" in entry]
            if errors:
                raise HueAPIError("; ".join(str(error.get("description", error)) for error in errors))

    def _request(self, path: str, method: str, payload: dict | None = None) -> Any:
        return self._request_absolute(self.base_url + path, method, payload)

    @staticmethod
    def _request_absolute(url: str, method: str, payload: dict | None = None) -> Any:
        data = None if payload is None else json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(
            url,
            data=data,
            method=method,
            headers={"Content-Type": "application/json"},
        )
        try:
            # Hue Bridge discovery currently advertises local HTTPS on port 443.
            # The bridge certificate is device-local and is not rooted in the
            # operating system trust store, so this narrowly scoped client does
            # not perform public-CA validation for the configured LAN address.
            context = ssl._create_unverified_context() if url.startswith("https://") else None
            with urllib.request.urlopen(request, timeout=5, context=context) as response:
                return json.loads(response.read().decode("utf-8"))
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            raise HueAPIError(f"Hue Bridge request failed: {exc}") from exc

    @staticmethod
    def _bridge_url(value: str) -> str:
        bridge = value.strip().rstrip("/")
        if bridge.startswith(("http://", "https://")):
            return bridge
        return f"https://{bridge}"

