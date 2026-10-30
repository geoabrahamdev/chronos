"""Reproducible checks for the bounded CHRONOS pathway model.

These are structural and computational checks, not evidence of a biological
behavioral prediction. Empirical validation remains explicitly external.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / "data" / "malecns" / "verified-odor-motor-path.json"
OUT = ROOT / "data" / "malecns" / "verified-path-validation.json"


def run(path, drive, steps=80):
    edges, nodes = path["edges"], path["nodes"]
    rates = {node["body"]: 0.0 for node in nodes}
    scale = max(edge["synapses"] for edge in edges)
    for _ in range(steps):
        updated = {nodes[0]["body"]: min(1.0, rates[nodes[0]["body"]] * .62 + drive * .70)}
        for edge in edges:
            gain = .18 + .82 * edge["synapses"] / scale
            updated[edge["post"]] = min(1.0, rates[edge["post"]] * .70 + updated[edge["pre"]] * gain * .58)
        rates = updated
    return rates


def main():
    path = json.loads(PATH.read_text(encoding="utf-8"))
    baseline, odor = run(path, 0.0), run(path, 0.9)
    motor = path["nodes"][-1]["body"]
    checks = {
        "all_edges_have_positive_aggregate_synapse_weight": all(edge["synapses"] > 0 for edge in path["edges"]),
        "all_required_stages_present": {node["stage"] for node in path["nodes"]} >= {"olfactory receptor", "projection neuron", "higher-order", "central complex", "descending neuron", "VNC motor neuron"},
        "odor_drive_reaches_motor_in_bounded_model": odor[motor] > baseline[motor] + .01,
        "all_edges_have_synapse_partner_evidence": all(edge.get("partner_synapse_count", 0) > 0 for edge in path["edges"]),
        "partner_counts_match_aggregate_weights": all(edge.get("aggregate_weight_matches_partner_count") is True for edge in path["edges"]),
        "all_edges_have_primary_post_roi": all(bool(edge.get("primary_post_roi")) and edge.get("primary_post_roi") != "unassigned" for edge in path["edges"]),
        "all_edges_have_presynaptic_transmitter_evidence": all(edge.get("tbar_sites_matched", 0) > 0 for edge in path["edges"]),
    }
    report = {"status": "computational structural validation only", "checks": checks, "motor_rate_baseline": round(baseline[motor], 5), "motor_rate_under_dm1_drive": round(odor[motor], 5), "empirical_validation": "Not performed. This model must be compared with published or newly measured neural/behavioral recordings before biological claims are made."}
    OUT.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report))


if __name__ == "__main__":
    main()
