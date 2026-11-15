from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from vgr_core import MORSE, VGRCoordinator, build_vgr_plan, total_units
from install_claude_bridge import install
from hue_v1 import HueV1Controller


class FakeLight:
    def __init__(self) -> None:
        self.original = {"on": True, "bri": 57}
        self.events: list[tuple] = []

    def snapshot(self) -> dict:
        self.events.append(("snapshot",))
        return dict(self.original)

    def set_signal(self, on: bool, brightness: int = 254) -> None:
        self.events.append(("signal", on, brightness))

    def restore(self, snapshot: dict) -> None:
        self.events.append(("restore", snapshot))


class FakeClock:
    def __init__(self) -> None:
        self.now = 0.0

    def monotonic(self) -> float:
        return self.now

    def sleep(self, duration: float) -> None:
        self.now += duration


class VGRTests(unittest.TestCase):
    def test_hue_bridge_address_defaults_to_local_https(self) -> None:
        self.assertEqual(HueV1Controller._bridge_url("192.0.2.10"), "https://192.0.2.10")
        self.assertEqual(
            HueV1Controller._bridge_url("https://192.0.2.10:443/"),
            "https://192.0.2.10:443",
        )

    def test_morse_and_timing_are_exact(self) -> None:
        self.assertEqual(MORSE, {"V": "...-", "G": "--.", "R": ".-."})
        self.assertEqual(total_units(), 31)
        plan = build_vgr_plan()
        self.assertTrue(plan[0].light_on)
        self.assertEqual(plan[0].units, 1)
        self.assertEqual(plan[-1].label, "R .")
        self.assertEqual(plan[-1].units, 1)

    def test_complete_run_restores_state_and_consumes_only_actor_run(self) -> None:
        fake = FakeLight()
        clock = FakeClock()
        with tempfile.TemporaryDirectory() as temporary:
            coordinator = VGRCoordinator(
                fake,
                Path(temporary),
                unit_seconds=0.5,
                sleeper=clock.sleep,
                monotonic=clock.monotonic,
            )
            coordinator.arm(["companion-a", "companion-b"], runs_each=1)
            result = coordinator.transmit("companion-a")
            self.assertEqual(result["duration_seconds"], 15.5)
            self.assertEqual(
                result["remaining"], {"companion-a": 0, "companion-b": 1}
            )
            self.assertEqual(fake.events[0], ("snapshot",))
            self.assertEqual(fake.events[-2], ("signal", False, 254))
            self.assertEqual(fake.events[-1], ("restore", fake.original))
            records = [json.loads(line) for line in coordinator.log_path.read_text().splitlines()]
            self.assertEqual(records[0]["actor"], "companion-a")
            self.assertEqual(records[0]["result"], "completed")

    def test_unarmed_and_duplicate_runs_are_rejected(self) -> None:
        fake = FakeLight()
        clock = FakeClock()
        with tempfile.TemporaryDirectory() as temporary:
            coordinator = VGRCoordinator(
                fake,
                Path(temporary),
                unit_seconds=0.5,
                sleeper=clock.sleep,
                monotonic=clock.monotonic,
            )
            with self.assertRaisesRegex(RuntimeError, "not physically armed"):
                coordinator.transmit("companion-b")
            coordinator.arm(["companion-b"], runs_each=1)
            coordinator.transmit("companion-b")
            with self.assertRaisesRegex(RuntimeError, "No armed VGR transmission remains"):
                coordinator.transmit("companion-b")

    def test_stop_is_available_while_disarmed(self) -> None:
        fake = FakeLight()
        with tempfile.TemporaryDirectory() as temporary:
            coordinator = VGRCoordinator(fake, Path(temporary))
            coordinator.request_stop()
            self.assertTrue(coordinator.stop_path.exists())
            self.assertEqual(fake.events[-1], ("signal", False, 254))

    def test_claude_installer_preserves_existing_bridges(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            config = Path(temporary) / "claude_desktop_config.json"
            launcher = Path(temporary) / "run-vgr-companion-a.command"
            launcher.touch()
            config.write_text(
                json.dumps(
                    {
                        "mcpServers": {
                            "existing-server": {"command": "/existing/launcher"},
                        }
                    }
                ),
                encoding="utf-8",
            )
            install(config, "vgr-companion-a", str(launcher))
            payload = json.loads(config.read_text(encoding="utf-8"))
            self.assertEqual(
                payload["mcpServers"]["existing-server"]["command"],
                "/existing/launcher",
            )
            self.assertEqual(
                payload["mcpServers"]["vgr-companion-a"]["command"],
                str(launcher),
            )


if __name__ == "__main__":
    unittest.main()

