# CHRONOS: MaleCNS Open World

CHRONOS is a local, interactive research prototype that places a virtual fruit fly in a three-dimensional open world and drives selected neural signals through verified connections from the **HHMI Janelia MaleCNS v1.0 connectome**.

The project is intentionally honest about its boundary:

- **Real data:** selected MaleCNS neuron IDs, directed connections, aggregate synapse weights, primary ROI evidence, and transmitter predictions.
- **Modeled by CHRONOS:** neural-rate dynamics, odor fields, needs, decisions, body control, flight physics, cars, threats, memory, and all behavioral timing.
- **Not claimed:** a complete brain emulation, measured neural firing, consciousness, or experimentally validated whole-animal behavior.

Everything runs on `127.0.0.1`. No ChatGPT account, cloud backend, or GPU is required.

## What you can explore

### A living open world

- A 10 × 10 three-dimensional meadow with trees, elevated resources, roads, and intermittent traffic.
- Drag-and-drop nectar, yeast, water, shelter, and threat stimuli at configurable heights.
- Reposition the fly in X/Y/Z and orbit, tilt, zoom, reset, or follow the camera.
- Internal drives for hunger, thirst, fatigue, and fear.
- Time-based feeding, drinking, and resting instead of instantaneous resource use.
- Ground and elevated approaches, landing, departure, collision avoidance, and threat evasion.

### Three observer frames

- **WORLD:** the baseline third-person environment.
- **FLY:** a first-person projection limited to the modeled sensory horizon.
- **BLOCK:** a recorded worldline with altitude shadows, time scrubbing, lesion markers, and experimental counterfactual branches.

### Connectome evidence

The main displayed route is a 12-cell, 11-edge chain:

```text
ORN_DM1 → DM1_lPN → higher-order relays → PEN_a → EPG → PFL2 → DNa03 → i1 motor neuron
```

Every displayed directed edge is backed by the MaleCNS v1.0 flat-connectome data. The checked-in portable evidence contains 787 selected synaptic-partner rows for this route. Live “model rates” are CHRONOS calculations, not recorded biological voltages or spikes.

## Quick start

Requirements:

- Python 3.10 or newer
- A modern browser

Run the portable version:

```powershell
git clone https://github.com/geoabrahamdev/chronos.git
cd chronos
python server.py
```

Then open:

```text
http://127.0.0.1:4173/
```

The portable runtime uses only Python’s standard library. The included data subset is approximately 300 KB rather than the full multi-gigabyte connectome export.

## Repository layout

```text
CHRONOS/
├── data/malecns/                 Attributed portable pathway and circuit evidence
├── dist/                         Browser UI, canvas renderers, and styles
├── scripts/                      Extraction, enrichment, validation, and tests
├── server.py                     Local simulation and JSON API
├── MEMORY_MAP.md                 Engineering handoff and current project state
├── PLAN_OBSERVER_FRAMES.md       Observer-frame design and scientific boundaries
├── THIRD_PARTY_NOTICES.md        MaleCNS attribution and licensing notice
└── requirements-data.txt         Optional dependency for rebuilding from raw data
```

## Architecture

```text
Official MaleCNS v1.0 tables
          │
          ├── extraction and validation scripts
          │          │
          │          └── portable attributed JSON subset
          │                         │
          └─────────────────────────┤
                                    ▼
                         Python local simulation
                       /api/world and evidence APIs
                                    │
                                    ▼
                      Browser canvas and controls
                    WORLD / FLY / BLOCK projections
```

Simulation state belongs to the Python server. Camera and observer-frame state remain in the browser. Switching frames does not create a second simulation.

## Local API

| Endpoint | Purpose |
|---|---|
| `GET /api/health` | Portable-data and optional raw-table readiness |
| `GET /api/world` | Current fly, world, senses, needs, pathway, and interaction state |
| `GET /api/world?action=...` | Local experiment controls and stimulus input |
| `GET /api/connectome?circuit=odor` | Selected odor circuit summary |
| `GET /api/connectome?circuit=compass` | Selected compass circuit summary |
| `GET /api/connectome?circuit=pathway` | Verified odor-to-motor pathway |
| `GET /api/worldline` | Recorded trajectory and user intervention pivots |
| `GET /api/branches?seeds=1,2,3&steps=120` | Experimental deterministic futures |

## Validation

Run the checks used before publication:

```powershell
python -m py_compile server.py
node --check dist/world.js
python -m unittest discover -s scripts -p "test_*.py" -q
python scripts/validate_verified_pathway.py
```

The structural validator checks positive edge weights, required pathway stages, synaptic-partner evidence, ROI evidence, transmitter evidence, and bounded propagation to the motor endpoint. It does **not** establish biological behavioral validity.

## Rebuilding from the official raw MaleCNS files

Normal users do not need the raw tables. Researchers who want to reproduce the portable subset can install Arrow and download the official inputs:

```powershell
python -m pip install -r requirements-data.txt
powershell -ExecutionPolicy Bypass -File scripts/prepare_malecns_synapse_data.ps1
```

This downloads and checksum-verifies the official annotation, neurotransmitter, connection-weight, synaptic-partner, synapse-point, and presynaptic-transmitter tables. Allow roughly **24 GB for downloads** plus working space. The script then rebuilds and validates the portable artifacts.

Raw Feather files are deliberately excluded from Git because individual files reach 12.7 GB and GitHub rejects ordinary files above 100 MB. Download them from the [official MaleCNS data page](https://male-cns.janelia.org/download/).

## Scientific status and known limitations

CHRONOS is an exploratory visualization and bounded dynamical model. It currently has important limitations:

- The virtual body and environment are engineered approximations, not a biomechanical Drosophila model.
- The connectome supplies structure, not missing membrane, receptor, neuromodulatory, developmental, or physiological parameters.
- The displayed odor-to-motor route is a selected verified pathway, not the entire 166,700-neuron MaleCNS.
- Counterfactual branch seeds can currently produce nearly overlapping paths when deterministic drives dominate random steering.
- The FLY observer-frame plume visualization still needs alignment with the server’s non-zero odor signal.
- Behavioral claims have not yet been validated against published or newly measured fly experiments.

Treat the simulation as a transparent research instrument for testing hypotheses, not as evidence that the connectome alone reproduces a real fly.

## Data provenance and attribution

MaleCNS v1.0 was produced by the FlyEM Project at HHMI Janelia with the University of Cambridge, the MRC Laboratory of Molecular Biology, and Google Research. The official project states that the MaleCNS dataset is licensed under **CC-BY**.

The small files in `data/malecns/` are derived from that dataset and retain the attribution described in [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md). They are not relicensed under the repository’s MIT code license.

- [MaleCNS project](https://male-cns.janelia.org/)
- [MaleCNS downloads](https://male-cns.janelia.org/download/)
- [MaleCNS v1.0 release notes](https://male-cns.janelia.org/release/)

## Privacy and resource use

- The server binds only to `127.0.0.1`.
- No credentials or telemetry are required.
- The browser never loads the raw multi-gigabyte tables.
- The current model uses CPU memory mapping when rebuilding raw data and reports 0 MB GPU VRAM use.

## License

CHRONOS source code is available under the [MIT License](LICENSE). MaleCNS-derived data remains governed by its original CC-BY terms; see [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).
