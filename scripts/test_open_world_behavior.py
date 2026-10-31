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

    def test_pathway_coordinates_keep_real_sample_counts_and_units(self):
        coords = server.pathway_cell_coords()
        pathway = server.verified_pathway()
        retained_pairs = sum(len(edge["synapse_coordinate_sample"]) for edge in pathway["edges"])
        self.assertEqual(len(coords), 12)
        self.assertEqual(retained_pairs, 176)
        self.assertEqual(pathway["synapse_evidence"]["selected_partner_rows"], 787)
        self.assertEqual(sum(item["sample_count"] for item in coords.values()), retained_pairs * 2)
        for item in coords.values():
            self.assertGreater(item["sample_count"], 0)
            self.assertTrue(all(-1.0 <= value <= 1.0 for value in item["norm"]))
            for voxel, nm in zip(item["voxel_8nm"], item["nm"]):
                self.assertLessEqual(abs(nm - voxel * 8), 4)

    def test_snapshot_exposes_coordinates_and_activity_for_verified_route(self):
        state = self.world.snapshot(dm1=0.5, va2=0.0, goal="test")
        self.assertEqual(len(state["pathway"]["nodes"]), 12)
        self.assertEqual(len(state["pathway"]["edges"]), 11)
        self.assertTrue(all(node["coord"] for node in state["pathway"]["nodes"]))
        self.assertTrue(all(isinstance(edge["activity"], (int, float)) for edge in state["pathway"]["edges"]))

    def test_four_counterfactual_branches_are_deterministic_and_isolated(self):
        before = self.world.snapshot_state()
        first = self.world.branches([1, 2, 3, 4], 8)
        second = self.world.branches([1, 2, 3, 4], 8)
        self.assertEqual(first, second)
        self.assertEqual(
            [branch["scenario"] for branch in first["branches"]],
            ["baseline", "sated", "exhausted", "scrambled_pathway"],
        )
        self.assertEqual(self.world.snapshot_state(), before)

    def test_static_branch_copy_matches_four_scenarios(self):
        source = (Path(__file__).resolve().parents[1] / "dist" / "index.html").read_text(encoding="utf-8")
        self.assertIn("BRANCH ×4", source)
        self.assertIn("Fork 4 counterfactual futures", source)
        self.assertNotIn("BRANCH ×3", source)


if __name__ == "__main__":
    unittest.main()
