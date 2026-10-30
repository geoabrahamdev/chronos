"""Build a bounded, reproducible pathway from the local MaleCNS flat graph.

Each invocation scans the memory-mapped connection-weight table once.  The
intermediate JSON is deliberately kept under data/ (ignored by Git), so the
analysis can be resumed without retaining the full 1.1 GB graph in RAM.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path

import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.feather as feather
import pyarrow.ipc as ipc

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "malecns"
ANNOTATIONS = DATA / "body-annotations-male-cns-v1.0-minconf-0.5.feather"
WEIGHTS = DATA / "connectome-weights-male-cns-v1.0-minconf-0.5.feather"
STATE = DATA / "pathway-search.json"


def annotation_types():
    rows = feather.read_table(ANNOTATIONS, columns=["bodyId", "type"]).to_pylist()
    return {row["bodyId"]: row["type"] or "untyped" for row in rows}


def group_ids(types, group):
    if group == "sensor":
        return {body for body, cell_type in types.items() if cell_type.startswith(("ORN_DM1", "ORN_VA2"))}
    if group == "projection":
        return {body for body, cell_type in types.items() if cell_type in {"DM1_lPN", "VA2_adPN"}}
    if group == "central":
        return {body for body, cell_type in types.items() if cell_type.startswith(("EPG", "PEN", "PEG", "PFL"))}
    if group == "descending":
        return {body for body, cell_type in types.items() if cell_type.startswith(("DNa", "DNb", "DNc", "DNd", "DNe", "DNf", "DNg", "DNp")) and not cell_type.startswith("DN1")}
    if group == "motor":
        return {body for body, cell_type in types.items() if cell_type.startswith("MN") or cell_type.endswith(" MN")}
    raise ValueError(group)


def scan(pre_ids, post_ids=None):
    reader = ipc.open_file(pa.memory_map(str(WEIGHTS), "r"))
    pre_values = pa.array(list(pre_ids), type=pa.int64())
    post_values = pa.array(list(post_ids), type=pa.int64()) if post_ids else None
    edges = Counter()
    for index in range(reader.num_record_batches):
        batch = reader.get_batch(index)
        mask = pc.is_in(batch.column("body_pre"), value_set=pre_values)
        if post_values is not None:
            mask = pc.and_(mask, pc.is_in(batch.column("body_post"), value_set=post_values))
        picked = batch.filter(mask).to_pydict()
        for pre, post, weight in zip(picked["body_pre"], picked["body_post"], picked["weight"]):
            edges[(pre, post)] += weight
    return edges


def write(payload):
    STATE.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def initial(types):
    sensors, projections = group_ids(types, "sensor"), group_ids(types, "projection")
    edges = scan(sensors, projections)
    parent = {str(post): {"pre": pre, "weight": weight} for (pre, post), weight in edges.items()}
    payload = {
        "stage": 0,
        "frontier": sorted(projections),
        "visited": sorted(sensors | projections),
        "parents": parent,
        "layers": [{"name": "sensor_to_projection", "edges": [[pre, post, weight] for (pre, post), weight in edges.most_common()]}],
    }
    write(payload)
    print(json.dumps({"stage": 0, "sensory_edges": len(edges), "frontier": len(projections)}))


def expand(types, fanout):
    payload = json.loads(STATE.read_text(encoding="utf-8"))
    frontier = {int(body) for body in payload["frontier"]}
    visited = {int(body) for body in payload["visited"]}
    edges = scan(frontier)
    by_pre = defaultdict(list)
    for (pre, post), weight in edges.items():
        if post not in visited:
            by_pre[pre].append((weight, post))
    selected, layer_edges = set(), []
    for pre, candidates in by_pre.items():
        for weight, post in sorted(candidates, reverse=True)[:fanout]:
            selected.add(post)
            payload["parents"].setdefault(str(post), {"pre": pre, "weight": weight})
            layer_edges.append([pre, post, weight])
    payload["stage"] += 1
    payload["frontier"] = sorted(selected)
    payload["visited"] = sorted(visited | selected)
    payload["layers"].append({"name": f"higher_order_{payload['stage']}", "edges": sorted(layer_edges, key=lambda edge: edge[2], reverse=True)})
    central = group_ids(types, "central")
    hits = sorted(selected & central)
    payload["central_hits"] = hits
    write(payload)
    print(json.dumps({"stage": payload["stage"], "frontier": len(selected), "edges": len(layer_edges), "central_hits": len(hits), "hit_types": [types[body] for body in hits[:10]]}))


def direct(types, source_group, target_group):
    source, target = group_ids(types, source_group), group_ids(types, target_group)
    edges = scan(source, target)
    output = DATA / f"{source_group}-to-{target_group}.json"
    output.write_text(json.dumps({"source_group": source_group, "target_group": target_group, "edges": [[pre, post, weight, types[pre], types[post]] for (pre, post), weight in edges.most_common(500)]}, indent=2), encoding="utf-8")
    print(json.dumps({"source_group": source_group, "target_group": target_group, "edges": len(edges), "top": [[types[pre], types[post], weight] for (pre, post), weight in edges.most_common(5)]}))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["initial", "expand", "direct", "hit-central"])
    parser.add_argument("--fanout", type=int, default=8)
    parser.add_argument("--source")
    parser.add_argument("--target")
    args = parser.parse_args()
    types = annotation_types()
    if args.command == "initial": initial(types)
    elif args.command == "expand": expand(types, args.fanout)
    elif args.command == "direct": direct(types, args.source, args.target)
    else:
        payload = json.loads(STATE.read_text(encoding="utf-8"))
        frontier = {int(body) for body in payload["frontier"]}
        central = group_ids(types, "central")
        edges = scan(frontier, central)
        output = DATA / "frontier-to-central.json"
        output.write_text(json.dumps({"stage": payload["stage"], "edges": [[pre, post, weight, types[pre], types[post]] for (pre, post), weight in edges.most_common(500)]}, indent=2), encoding="utf-8")
        print(json.dumps({"stage": payload["stage"], "frontier": len(frontier), "central_edges": len(edges), "top": [[types[pre], types[post], weight] for (pre, post), weight in edges.most_common(10)]}))


if __name__ == "__main__":
    main()
