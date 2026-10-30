"""Extract and validate one real MaleCNS odor-to-motor chain.

The selected node IDs were discovered by constrained searches through the local
v1.0 flat graph. This script re-verifies every directed edge against that graph
and joins the official per-neuron neurotransmitter predictions.
"""
from __future__ import annotations

import json
from pathlib import Path

import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.feather as feather
import pyarrow.ipc as ipc

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "malecns"
ANNOTATIONS = DATA / "body-annotations-male-cns-v1.0-minconf-0.5.feather"
TRANSMITTERS = DATA / "body-neurotransmitters-male-cns-v1.0.feather"
WEIGHTS = DATA / "connectome-weights-male-cns-v1.0-minconf-0.5.feather"
OUT = DATA / "verified-odor-motor-path.json"

# ORN -> PN -> lateral-horn/higher-order relay -> central-complex -> DN -> VNC motor.
CHAIN = [925639, 10176, 10209, 13435, 515769, 15316, 12506, 513283, 513284, 518375, 10975, 800637]
STAGES = ["olfactory receptor", "projection neuron", "higher-order", "higher-order", "higher-order", "higher-order", "higher-order", "central complex", "central complex", "central complex", "descending neuron", "VNC motor neuron"]


def main():
    annotations = feather.read_table(ANNOTATIONS, columns=["bodyId", "type"]).to_pylist()
    cell_types = {row["bodyId"]: row["type"] or "untyped" for row in annotations}
    nt_rows = feather.read_table(TRANSMITTERS, columns=["body", "predicted_nt", "predicted_nt_confidence", "consensus_nt"]).to_pylist()
    transmitters = {row["body"]: row for row in nt_rows}
    wanted = {(pre, post) for pre, post in zip(CHAIN, CHAIN[1:])}
    reader = ipc.open_file(pa.memory_map(str(WEIGHTS), "r"))
    body_values = pa.array(CHAIN, type=pa.int64())
    found = {}
    for index in range(reader.num_record_batches):
        batch = reader.get_batch(index)
        mask = pc.and_(pc.is_in(batch.column("body_pre"), value_set=body_values), pc.is_in(batch.column("body_post"), value_set=body_values))
        picked = batch.filter(mask).to_pydict()
        for pre, post, weight in zip(picked["body_pre"], picked["body_post"], picked["weight"]):
            if (pre, post) in wanted:
                found[(pre, post)] = found.get((pre, post), 0) + weight
    missing = wanted - found.keys()
    if missing:
        raise SystemExit(f"Validated pathway edges missing from local graph: {sorted(missing)}")
    nodes = []
    for body, stage in zip(CHAIN, STAGES):
        nt = transmitters.get(body, {})
        nodes.append({"body": body, "type": cell_types[body], "stage": stage, "predicted_nt": nt.get("predicted_nt", "unknown"), "nt_confidence": round(nt.get("predicted_nt_confidence") or 0, 3), "consensus_nt": nt.get("consensus_nt", "unknown")})
    edges = []
    for index, (pre, post) in enumerate(zip(CHAIN, CHAIN[1:])):
        edges.append({"pre": pre, "post": post, "pre_type": cell_types[pre], "post_type": cell_types[post], "stage": f"{STAGES[index]} → {STAGES[index + 1]}", "synapses": found[(pre, post)], "primary_post_roi": None, "roi_status": "not locally loaded; official syn-partners table is required"})
    payload = {"dataset": "HHMI Janelia MaleCNS v1.0", "pathway": "verified ORN_DM1 to i1 MN chain", "nodes": nodes, "edges": edges, "roi_status": "Per-neuron transmitter predictions and aggregate edge synapse weights are local. Per-synapse primary ROI requires the optional 6.8 GB syn-partners table or an authenticated neuPrint query.", "dynamics_note": "Rates are a bounded CHRONOS model over these real nodes and weights; transmitter/receptor signs are not inferred from this table."}
    OUT.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps({"out": str(OUT), "nodes": len(nodes), "edges": len(edges), "min_weight": min(edge["synapses"] for edge in edges), "max_weight": max(edge["synapses"] for edge in edges)}))


if __name__ == "__main__":
    main()
