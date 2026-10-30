"""Attach synapse-level MaleCNS evidence to the verified CHRONOS pathway.

The official Feather files are scanned as Arrow record batches so the large
inputs never need to be copied into RAM or GPU memory. The output contains only
the eleven selected edges and small coordinate samples.
"""
from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path

import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.ipc as ipc

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "malecns"
PATHWAY = DATA / "verified-odor-motor-path.json"
PARTNERS = DATA / "syn-partners-male-cns-v1.0-minconf-0.5.feather"
POINTS = DATA / "syn-points-male-cns-v1.0-minconf-0.5.feather"
TBAR_NT = DATA / "tbar-neurotransmitters-male-cns-v1.0.feather"
EVIDENCE = DATA / "verified-synapse-evidence.json"
SAMPLE_LIMIT = 18


def reader(path: Path):
    if not path.exists():
        raise SystemExit(f"Missing official MaleCNS file: {path}")
    return ipc.open_file(pa.memory_map(str(path), "r"))


def edge_mask(batch, wanted):
    mask = None
    pre_col, post_col = batch.column("body_pre"), batch.column("body_post")
    for pre, post in wanted:
        selected = pc.and_(pc.equal(pre_col, pre), pc.equal(post_col, post))
        mask = selected if mask is None else pc.or_(mask, selected)
    return mask


def coord(row, prefix=""):
    suffix = f"_{prefix}" if prefix else ""
    return (int(row[f"x{suffix}"]), int(row[f"y{suffix}"]), int(row[f"z{suffix}"]))


def point_rois(row):
    """Normalize the MaleCNS hierarchical ROI columns into readable labels."""
    rois = set()
    ignored = {"x", "y", "z", "body", "kind", "conf", "sv", "segment_id"}
    hierarchy = {
        "compartment", "major", "primary", "superprimary", "subprimary",
        "medulla_r_column", "lobula_r_column", "lobula_plate_r_column",
        "medulla_r_layer", "lobula_r_layer", "lobula_plate_r_layer",
        "medulla_l_column", "lobula_l_column", "lobula_plate_l_column",
        "medulla_l_layer", "lobula_l_layer", "lobula_plate_l_layer",
    }
    for name, value in row.items():
        if name in ignored or value is None:
            continue
        if isinstance(value, (list, tuple)):
            if "roi" in name.lower():
                rois.update(str(item) for item in value if item)
        elif isinstance(value, str) and ("roi" in name.lower() or name in hierarchy) and value:
            rois.add(f"{name}:{value}")
        elif isinstance(value, bool) and value:
            rois.add(name)
    return sorted(rois)


def tbar_probability_columns(schema):
    names = {name.lower(): name for name in schema.names}
    aliases = {
        "acetylcholine": ("nt_acetylcholine_prob", "acetylcholine", "ach"),
        "gaba": ("nt_gaba_prob", "gaba"),
        "glutamate": ("nt_glutamate_prob", "glutamate", "glut"),
        "octopamine": ("nt_octopamine_prob", "octopamine", "oct"),
        "serotonin": ("nt_serotonin_prob", "serotonin", "ser"),
        "dopamine": ("nt_dopamine_prob", "dopamine", "da"),
        "histamine": ("nt_histamine_prob", "histamine", "his"),
        "unknown": ("unknown", "nt_unknown"),
    }
    found = {}
    for canonical, candidates in aliases.items():
        for candidate in candidates:
            if candidate in names:
                found[canonical] = names[candidate]
                break
    if not found:
        raise SystemExit(f"No neurotransmitter probability columns found in {schema.names}")
    return found


def main():
    pathway = json.loads(PATHWAY.read_text(encoding="utf-8"))
    wanted = [(edge["pre"], edge["post"]) for edge in pathway["edges"]]
    wanted_set = set(wanted)
    edge_rows = defaultdict(list)

    partner_reader = reader(PARTNERS)
    partner_scanned = 0
    for index in range(partner_reader.num_record_batches):
        batch = partner_reader.get_batch(index)
        partner_scanned += batch.num_rows
        for row in batch.filter(edge_mask(batch, wanted)).to_pylist():
            key = (int(row["body_pre"]), int(row["body_post"]))
            if key in wanted_set:
                edge_rows[key].append(row)

    missing = wanted_set - edge_rows.keys()
    if missing:
        raise SystemExit(f"No synapse-partner rows found for pathway edges: {sorted(missing)}")

    coordinate_roles = defaultdict(list)
    for key, rows in edge_rows.items():
        for row in rows:
            coordinate_roles[coord(row, "pre")].append((key, "pre"))
            coordinate_roles[coord(row, "post")].append((key, "post"))

    point_reader = reader(POINTS)
    point_scanned = 0
    point_hits = defaultdict(lambda: {"pre": set(), "post": set(), "rois": Counter()})
    bodies = pa.array(sorted({body for edge in wanted for body in edge}), type=pa.int64())
    for index in range(point_reader.num_record_batches):
        batch = point_reader.get_batch(index)
        point_scanned += batch.num_rows
        mask = pc.is_in(batch.column("body"), value_set=bodies)
        for row in batch.filter(mask).to_pylist():
            key_coord = coord(row)
            if key_coord not in coordinate_roles:
                continue
            rois = point_rois(row)
            for edge_key, role in coordinate_roles[key_coord]:
                point_hits[edge_key][role].add(key_coord)
                point_hits[edge_key]["rois"].update(rois)

    tbar_reader = reader(TBAR_NT)
    nt_columns = tbar_probability_columns(tbar_reader.schema)
    pre_coord_edges = defaultdict(set)
    for edge_key, rows in edge_rows.items():
        for row in rows:
            pre_coord_edges[coord(row, "pre")].add(edge_key)
    tbar_sums = defaultdict(Counter)
    tbar_counts = Counter()
    tbar_scanned = 0
    for index in range(tbar_reader.num_record_batches):
        batch = tbar_reader.get_batch(index)
        tbar_scanned += batch.num_rows
        if "body" in batch.schema.names:
            mask = pc.is_in(batch.column("body"), value_set=bodies)
        else:
            xs = pa.array(sorted({value[0] for value in pre_coord_edges}), type=batch.column("x").type)
            mask = pc.is_in(batch.column("x"), value_set=xs)
        for row in batch.filter(mask).to_pylist():
            key_coord = coord(row)
            for edge_key in pre_coord_edges.get(key_coord, ()):
                tbar_counts[edge_key] += 1
                for canonical, source_name in nt_columns.items():
                    value = row.get(source_name)
                    if value is not None:
                        tbar_sums[edge_key][canonical] += float(value)

    evidence_edges = []
    for edge in pathway["edges"]:
        key = (edge["pre"], edge["post"])
        rows = edge_rows[key]
        roi_counts = Counter(str(row.get("primary_post") or "unassigned") for row in rows)
        dominant_roi, dominant_count = roi_counts.most_common(1)[0]
        unique_pre = {coord(row, "pre") for row in rows}
        count = tbar_counts[key]
        nt_means = {name: round(total / count, 5) for name, total in tbar_sums[key].items()} if count else {}
        top_nt = max(nt_means, key=nt_means.get) if nt_means else "unavailable"
        samples = [
            {
                "pre": list(coord(row, "pre")),
                "post": list(coord(row, "post")),
                "primary_post_roi": row.get("primary_post"),
                "confidence": [round(float(row.get("conf_pre") or 0), 3), round(float(row.get("conf_post") or 0), 3)],
            }
            for row in rows[:SAMPLE_LIMIT]
        ]
        details = {
            "pre": key[0], "post": key[1], "partner_synapse_count": len(rows),
            "aggregate_weight": edge["synapses"],
            "aggregate_weight_matches_partner_count": len(rows) == edge["synapses"],
            "unique_presynaptic_sites": len(unique_pre),
            "primary_post_roi_counts": dict(roi_counts.most_common()),
            "dominant_primary_post_roi": dominant_roi,
            "point_table_pre_sites_matched": len(point_hits[key]["pre"]),
            "point_table_post_sites_matched": len(point_hits[key]["post"]),
            "point_table_roi_counts": dict(point_hits[key]["rois"].most_common()),
            "tbar_sites_matched": count,
            "tbar_mean_probabilities": nt_means,
            "tbar_dominant_prediction": top_nt,
            "coordinate_sample": samples,
        }
        evidence_edges.append(details)
        edge.update({
            "primary_post_roi": dominant_roi,
            "primary_post_roi_counts": details["primary_post_roi_counts"],
            "partner_synapse_count": len(rows),
            "aggregate_weight_matches_partner_count": details["aggregate_weight_matches_partner_count"],
            "unique_presynaptic_sites": len(unique_pre),
            "tbar_sites_matched": count,
            "tbar_dominant_prediction": top_nt,
            "tbar_mean_probabilities": nt_means,
            "synapse_coordinate_sample": samples,
            "roi_status": f"{dominant_roi} ({dominant_count}/{len(rows)} partner rows)",
        })

    files = {}
    for path, rows in ((PARTNERS, partner_scanned), (POINTS, point_scanned), (TBAR_NT, tbar_scanned)):
        files[path.name] = {"bytes": path.stat().st_size, "rows_scanned": rows}
    pathway["roi_status"] = (
        "Synapse-level MaleCNS partner, point-location, and presynaptic transmitter tables are local. "
        "Each displayed ROI and coordinate comes from those official tables; live rates remain a CHRONOS model."
    )
    pathway["synapse_evidence"] = {
        "status": "official MaleCNS synapse tables locally verified", "files": files,
        "selected_partner_rows": sum(len(rows) for rows in edge_rows.values()),
        "coordinate_samples_are_truncated_to": SAMPLE_LIMIT,
    }
    evidence = {
        "dataset": pathway["dataset"], "pathway": pathway["pathway"], "files": files,
        "edges": evidence_edges,
        "note": "Derived evidence only; the full raw MaleCNS tables remain local and Git-ignored.",
    }
    EVIDENCE.write_text(json.dumps(evidence, indent=2), encoding="utf-8")
    PATHWAY.write_text(json.dumps(pathway, indent=2), encoding="utf-8")
    print(json.dumps({
        "pathway": str(PATHWAY), "evidence": str(EVIDENCE),
        "selected_partner_rows": pathway["synapse_evidence"]["selected_partner_rows"],
        "all_weights_match": all(edge["aggregate_weight_matches_partner_count"] for edge in evidence_edges),
        "all_edges_have_roi": all(edge["dominant_primary_post_roi"] != "unassigned" for edge in evidence_edges),
        "all_edges_have_tbar_predictions": all(edge["tbar_sites_matched"] > 0 for edge in evidence_edges),
    }))


if __name__ == "__main__":
    main()
