"""Regression tests for CHRONOS need selection and world telemetry layout."""
from __future__ import annotations

import random
import unittest
from pathlib import Path

import server


class SimulatedClock:
    def __init__(self):
        self.now = 1000.0

    def advance(self, seconds=0.08):
        self.now += seconds


class OpenWorldBehaviorTests(unittest.TestCase):
    def setUp(self):
        self.real_monotonic = server.time.monotonic
        self.clock = SimulatedClock()
        server.time.monotonic = lambda: self.clock.now
        random.seed(7)
        self.world = server.OpenWorld()
        self.world.world["cars"] = []
        self.world.traffic_next = float("inf")

    def tearDown(self):
        server.time.monotonic = self.real_monotonic

    def step(self, seconds=0.08):
        self.clock.advance(seconds)
        return self.world.step()

    def test_severe_hunger_beats_satiated_thirst_and_low_fatigue(self):
        self.world.needs.update(hunger=1.0, thirst=0.01, fatigue=0.04, fear=0.0)
        state = self.step()
        self.assertTrue(state["goal"].startswith("follow "), state["goal"])

    def test_water_bout_takes_time_then_satisfies_thirst(self):
        water = next(source for source in self.world.world["sources"] if source["kind"] == "water")
        self.world.needs.update(hunger=0.30, thirst=1.0, fatigue=0.04, fear=0.0)
        self.world.fly.update(x=water["x"], y=water["y"], z=0.045, heading=0.0)
        state = self.step()
        self.assertEqual(state["interaction"]["mode"], "drinking")
        self.assertAlmostEqual(state["interaction"]["duration"], 2.5)
        self.assertGreater(self.world.needs["thirst"], 0.95)
        state = self.step(1.25)
        self.assertTrue(state["interaction"]["active"])
        self.assertGreater(state["interaction"]["progress"], 0.45)
        self.assertLess(self.world.needs["thirst"], 0.65)
        state = self.step(1.30)
        self.assertFalse(state["interaction"]["active"])
        self.assertLess(self.world.needs["thirst"], 0.2)
        self.world.needs["hunger"] = 1.0
        self.clock.now = self.world.cooldowns[water["id"]] + 0.01
        self.world.last = self.clock.now - 0.08
        self.world.depart_until = 0.0
        state = self.step()
        self.assertNotEqual(state["goal"], "seek water")
        self.assertTrue(state["goal"].startswith("follow "), state["goal"])

    def test_food_bout_takes_time_then_satisfies_hunger(self):
        food = next(
            source
            for source in self.world.world["sources"]
            if source["kind"] == "food" and source["z"] < 0.2
        )
        self.world.needs.update(hunger=1.0, thirst=0.01, fatigue=0.04, fear=0.0)
        self.world.fly.update(x=food["x"], y=food["y"], z=0.085, heading=0.0)
        state = self.step()
        self.assertEqual(state["interaction"]["mode"], "feeding")
        self.assertAlmostEqual(state["interaction"]["duration"], 3.5)
        self.assertGreater(self.world.needs["hunger"], 0.95)
        state = self.step(1.75)
        self.assertTrue(state["interaction"]["active"])
        self.assertGreater(state["interaction"]["progress"], 0.45)
        self.assertGreater(self.world.needs["hunger"], 0.60)
        self.assertLess(self.world.needs["hunger"], 0.75)
        state = self.step(1.80)
        self.assertFalse(state["interaction"]["active"])
        self.assertLess(self.world.needs["hunger"], 0.45)

    def test_rest_holds_position_for_ten_seconds_and_recovers_gradually(self):
        shelter = next(source for source in self.world.world["sources"] if source["kind"] == "rest")
        self.world.needs.update(hunger=0.01, thirst=0.01, fatigue=1.0, fear=0.0)
        self.world.fly.update(x=shelter["x"], y=shelter["y"], z=0.045, heading=0.0)
        state = self.step()
        self.assertEqual(state["interaction"]["mode"], "resting")
        self.assertAlmostEqual(state["interaction"]["duration"], 10.0)
        anchor = (state["fly"]["x"], state["fly"]["y"], state["fly"]["z"])
        state = self.step(5.0)
        self.assertTrue(state["interaction"]["active"])
        self.assertGreater(state["interaction"]["progress"], 0.45)
        self.assertEqual(anchor, (state["fly"]["x"], state["fly"]["y"], state["fly"]["z"]))
        self.assertGreater(self.world.needs["fatigue"], 0.35)
        self.assertLess(self.world.needs["fatigue"], 0.75)
        state = self.step(5.1)
        self.assertFalse(state["interaction"]["active"])
        self.assertLess(self.world.needs["fatigue"], 0.45)

    def test_canvas_telemetry_stays_above_html_event_bar(self):
        source = (Path(__file__).resolve().parents[1] / "dist" / "world.js").read_text(encoding="utf-8")
        self.assertIn("H-55", source)
        self.assertNotIn("H-18,9,'#d4f16b'", source)


if __name__ == "__main__":
    unittest.main()
