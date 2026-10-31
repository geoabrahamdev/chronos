# Architecture

## System boundary

CHRONOS has three separable layers:

1. **MaleCNS evidence:** selected identifiers, directed partner relationships, aggregate synapse counts, ROI evidence, sampled coordinates, and transmitter predictions.
2. **CHRONOS model:** bounded rate propagation, odor fields, internal needs, action selection, movement, interaction timing, obstacles, and counterfactual scenarios.
3. **Observer projections:** WORLD, FLY, BLOCK, and the 3D pathway viewer.

Only layer 1 is derived from the connectome. Layers 2 and 3 are software models and visualizations.

## Runtime components

```text
Browser (dist/)
  ├─ polls JSON state every 120 ms
  ├─ sends explicit local actions
  ├─ owns camera, orbit, zoom, frame, and scrubber state
  └─ draws world and pathway on Canvas 2D
                    │ HTTP on 127.0.0.1:4173
Python server (server.py)
  ├─ owns the one persistent OpenWorld instance
  ├─ advances modeled needs, traffic, senses, rates, and body state
  ├─ records the worldline and pivots
  └─ serves dist/ and JSON endpoints
                    │ startup/load
Portable JSON (data/malecns/)
  └─ attributed subset generated from optional official Feather tables
```

There is no Node.js runtime, database, WebSocket service, cloud backend, or ChatGPT integration.

## State ownership

| State | Owner | Reason |
|---|---|---|
| Fly position, heading, needs, interaction, goals | Server | One authoritative simulation |
| Sources, cars, traffic timers, lesions, rates | Server | Deterministic snapshots and branches |
| Worldline and intervention pivots | Server | Observer frames share the same history |
| Camera, zoom, observer frame, time cursor | Browser | Projection only; cannot change model state |
| Raw tables | Local filesystem only | Too large and unnecessary for the runtime |

## Data pipeline

`scripts/prepare_malecns_data.py` reads `data/malecns/raw-files.json`, downloads and verifies six official files, then runs:

1. `extract_verified_odor_motor_path.py` — revalidates the selected directed route against annotations, weights, and per-neuron transmitter predictions.
2. `export_portable_runtime.py` — writes bounded odor and compass circuit summaries.
3. `enrich_verified_pathway_synapses.py` — scans partner, point, and t-bar tables for selected pathway evidence only.
4. `validate_verified_pathway.py` — validates stages, weights, evidence, and bounded propagation.

Only compact JSON outputs are committed. No runtime request reads the multi-gigabyte Feather files.

## Pathway and dynamics

The displayed route has 12 selected cells and 11 verified directed edges. `server.py` runs a small non-spiking rate model over that route. Edge widths can represent real aggregate synapse counts; live lime activity represents CHRONOS rate values. The two must never be described as the same measurement.

Coordinates are computed from retained pathway synapse samples. They locate where the selected pathway touches each cell and are not full-neuron morphology or absolute anatomical centroids.

## Counterfactual isolation

Branches snapshot the authoritative world state, run bounded seeded scenarios on isolated state, and restore the live state. A test asserts identical inputs produce identical branches and that branch calculation does not mutate the live world.

## Safety and performance

- Server bind: `127.0.0.1` only.
- Browser assets: local files only.
- Raw processing: CPU-side PyArrow batches.
- GPU allocation: none; preserve the documented 2 GB ceiling if GPU work is added.
- Downloader: exact byte and MD5 verification before a raw file is accepted.

## Extension points

- Add a world action in `OpenWorld`, expose it through the `/api/world` action handler, then add a regression.
- Add circuit evidence through the extraction pipeline; do not hardcode unverified biology into the UI.
- Add an observer frame as a projection of existing state; do not create a hidden second simulation.
- Add empirical validation as a separate dataset and analysis layer; do not relabel structural checks as behavioral validation.
