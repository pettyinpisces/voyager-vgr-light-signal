#!/usr/bin/env python3
"""Deterministic Morse planning and guarded execution for the VGR light message."""

from __future__ import annotations

import json
import os
import time
from contextlib import contextmanager
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Iterable, Iterator, Protocol

if os.name == "nt":
    import msvcrt
else:
    import fcntl


MESSAGE = "VGR"
MORSE = {"V": "...-", "G": "--.", "R": ".-."}
DEFAULT_UNIT_SECONDS = 0.5
DEFAULT_ACTORS = ("companion-a", "companion-b", "human")


@dataclass(frozen=True)
class MorseStep:
    light_on: bool
    units: int
    label: str


class LightController(Protocol):
    def snapshot(self) -> dict:
        ...

    def set_signal(self, on: bool, brightness: int = 254) -> None:
        ...

    def restore(self, snapshot: dict) -> None:
        ...


def build_vgr_plan() -> list[MorseStep]:
    """Build ITU Morse timing: dot 1, dash 3, element gap 1, letter gap 3."""
    plan: list[MorseStep] = []
    for letter_index, letter in enumerate(MESSAGE):
        symbols = MORSE[letter]
        for symbol_index, symbol in enumerate(symbols):
            units = 1 if symbol == "." else 3
            plan.append(MorseStep(True, units, f"{letter} {symbol}"))
            if symbol_index < len(symbols) - 1:
                plan.append(MorseStep(False, 1, f"{letter} element gap"))
        if letter_index < len(MESSAGE) - 1:
            plan.append(MorseStep(False, 3, f"after {letter}"))
    return plan


def total_units(plan: Iterable[MorseStep] | None = None) -> int:
    return sum(step.units for step in (plan or build_vgr_plan()))


def plan_payload(unit_seconds: float = DEFAULT_UNIT_SECONDS) -> dict:
    plan = build_vgr_plan()
    return {
        "message": MESSAGE,
        "morse": " ".join(MORSE[letter] for letter in MESSAGE),
        "unit_seconds": unit_seconds,
        "total_units": total_units(plan),
        "duration_seconds": total_units(plan) * unit_seconds,
        "steps": [asdict(step) for step in plan],
    }


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class VGRCoordinator:
    """One-at-a-time, physically armed VGR transmitter with run accounting."""

    def __init__(
        self,
        controller: LightController,
        runtime_dir: Path,
        unit_seconds: float = DEFAULT_UNIT_SECONDS,
        brightness: int = 254,
        allowed_actors: Iterable[str] = DEFAULT_ACTORS,
        sleeper: Callable[[float], None] = time.sleep,
        monotonic: Callable[[], float] = time.monotonic,
    ) -> None:
        if not 0.2 <= unit_seconds <= 2.0:
            raise ValueError("unit_seconds must be between 0.2 and 2.0")
        if not 1 <= brightness <= 254:
            raise ValueError("brightness must be between 1 and 254")
        self.controller = controller
        self.runtime_dir = runtime_dir
        self.runtime_dir.mkdir(parents=True, exist_ok=True)
        self.unit_seconds = unit_seconds
        self.brightness = brightness
        self.allowed_actors = frozenset(
            actor.strip().lower() for actor in allowed_actors if actor.strip()
        )
        if not self.allowed_actors:
            raise ValueError("allowed_actors must contain at least one actor")
        self.sleeper = sleeper
        self.monotonic = monotonic
        self.arm_path = runtime_dir / "armed.json"
        self.lock_path = runtime_dir / "transmission.lock"
        self.stop_path = runtime_dir / "STOP"
        self.log_path = runtime_dir / "transmissions.jsonl"

    def arm(self, actors: Iterable[str], minutes: int = 30, runs_each: int = 1) -> dict:
        normalized = sorted({actor.strip().lower() for actor in actors if actor.strip()})
        if not normalized or any(actor not in self.allowed_actors for actor in normalized):
            raise ValueError(
                "actors must be a non-empty subset of the configured allowed_actors"
            )
        if not 1 <= minutes <= 180:
            raise ValueError("minutes must be between 1 and 180")
        if not 1 <= runs_each <= 5:
            raise ValueError("runs_each must be between 1 and 5")
        payload = {
            "armed_at": time.time(),
            "expires_at": time.time() + minutes * 60,
            "remaining": {actor: runs_each for actor in normalized},
        }
        self._atomic_json(self.arm_path, payload)
        self.stop_path.unlink(missing_ok=True)
        return payload

    def disarm(self) -> None:
        self.arm_path.unlink(missing_ok=True)
        self.stop_path.touch(mode=0o600, exist_ok=True)

    def request_stop(self) -> None:
        self.stop_path.touch(mode=0o600, exist_ok=True)
        try:
            self.controller.set_signal(False, self.brightness)
        except Exception:
            pass

    def status(self) -> dict:
        arm = self._read_arm()
        return {
            "armed": bool(arm),
            "arm": arm,
            "stop_requested": self.stop_path.exists(),
            "plan": plan_payload(self.unit_seconds),
        }

    def transmit(self, actor: str) -> dict:
        actor = actor.strip().lower()
        if actor not in self.allowed_actors:
            raise ValueError("actor is not present in the configured allowed_actors")

        self.lock_path.touch(mode=0o600, exist_ok=True)
        with self.lock_path.open("r+", encoding="utf-8") as lock_file:
            with self._exclusive_lock(lock_file):
                arm = self._read_arm()
                if not arm:
                    raise RuntimeError("VGR is not physically armed or the arming window expired")
                remaining = int(arm.get("remaining", {}).get(actor, 0))
                if remaining < 1:
                    raise RuntimeError(f"No armed VGR transmission remains for {actor}")

                self.stop_path.unlink(missing_ok=True)
                snapshot = self.controller.snapshot()
                started = utc_now()
                started_monotonic = self.monotonic()
                result = "completed"
                error = None
                try:
                    for step in build_vgr_plan():
                        self._check_stop()
                        self.controller.set_signal(step.light_on, self.brightness)
                        self._interruptible_sleep(step.units * self.unit_seconds)
                    self.controller.set_signal(False, self.brightness)
                except Exception as exc:
                    result = "stopped" if self.stop_path.exists() else "failed"
                    error = str(exc)
                    raise
                finally:
                    try:
                        self.controller.restore(snapshot)
                    finally:
                        elapsed = round(self.monotonic() - started_monotonic, 3)
                        record = {
                            "actor": actor,
                            "message": MESSAGE,
                            "morse": " ".join(MORSE[letter] for letter in MESSAGE),
                            "started": started,
                            "finished": utc_now(),
                            "elapsed_seconds": elapsed,
                            "result": result,
                            "error": error,
                        }
                        self._append_log(record)

                arm["remaining"][actor] = remaining - 1
                self._atomic_json(self.arm_path, arm)
                return {
                    "ok": True,
                    "actor": actor,
                    "message": MESSAGE,
                    "morse": " ".join(MORSE[letter] for letter in MESSAGE),
                    "duration_seconds": round(self.monotonic() - started_monotonic, 3),
                    "remaining": arm["remaining"],
                    "restored": True,
                }

    @staticmethod
    @contextmanager
    def _exclusive_lock(lock_file) -> Iterator[None]:
        """Acquire a nonblocking process lock on macOS, Linux, or Windows."""
        try:
            if os.name == "nt":
                lock_file.seek(0, os.SEEK_END)
                if lock_file.tell() == 0:
                    lock_file.write("0")
                    lock_file.flush()
                lock_file.seek(0)
                msvcrt.locking(lock_file.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                fcntl.flock(lock_file, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except (BlockingIOError, OSError) as exc:
            raise RuntimeError("A VGR transmission is already in progress") from exc
        try:
            yield
        finally:
            if os.name == "nt":
                lock_file.seek(0)
                msvcrt.locking(lock_file.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(lock_file, fcntl.LOCK_UN)

    def _interruptible_sleep(self, duration: float) -> None:
        deadline = self.monotonic() + duration
        while True:
            self._check_stop()
            remaining = deadline - self.monotonic()
            if remaining <= 0:
                return
            self.sleeper(min(0.05, remaining))

    def _check_stop(self) -> None:
        if self.stop_path.exists():
            raise RuntimeError("VGR transmission stopped")

    def _read_arm(self) -> dict | None:
        try:
            payload = json.loads(self.arm_path.read_text(encoding="utf-8"))
            if time.time() > float(payload["expires_at"]):
                self.arm_path.unlink(missing_ok=True)
                return None
            if not isinstance(payload.get("remaining"), dict):
                return None
            return payload
        except (FileNotFoundError, KeyError, TypeError, ValueError, json.JSONDecodeError):
            return None

    @staticmethod
    def _atomic_json(path: Path, payload: dict) -> None:
        temporary = path.with_suffix(path.suffix + ".tmp")
        temporary.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        os.chmod(temporary, 0o600)
        os.replace(temporary, path)

    def _append_log(self, record: dict) -> None:
        with self.log_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, sort_keys=True) + "\n")
        os.chmod(self.log_path, 0o600)

