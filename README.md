# CHRONOS: MaleCNS Open World

CHRONOS is a local, interactive research prototype that places a virtual fruit fly in a three-dimensional world and propagates modeled activity through a small, verified pathway from the **HHMI Janelia MaleCNS v1.0 connectome**.

> **Scientific boundary:** MaleCNS supplies selected neuron identifiers, directed connections, aggregate synapse counts, ROI evidence, coordinate samples, and transmitter predictions. CHRONOS supplies the rate dynamics, sensory fields, needs, decisions, body control, world physics, and behavioral timing. This is not a whole-brain emulation or evidence of consciousness or biologically validated whole-animal behavior.

The application binds to `127.0.0.1`, needs no account or cloud service, and runs without a GPU.

## Try it locally

Requirements: Python 3.10+ and a modern browser. Node.js 22+ is needed only for the JavaScript syntax check used by contributors.

```bash
git clone https://github.com/geoabrahamdev/chronos.git
cd chronos
python server.py
```

Open [http://127.0.0.1:4173/](http://127.0.0.1:4173/). The checked-in portable evidence is sufficient; you do **not** need to download the 24 GB raw dataset to run the app.

## What is included

- A 10 × 10 modeled world with ground and elevated resources, trees, biomes, a crossable road, intermittent vehicles, and 3D stimulus placement.
- Hunger, thirst, fatigue, fear, time-based resource use, landing, flight, collision avoidance, and threat evasion.
- WORLD, FLY, and BLOCK observer frames over the same server-owned simulation.
- A rotatable 3D view of a 12-cell, 11-edge `ORN_DM1 → … → i1 MN` route.
- Real MaleCNS aggregate edge weights and sampled pathway-synapse coordinates, shown separately from CHRONOS model rates.
- Lesion/restore controls, recorded worldlines, time scrubbing, and four reproducible counterfactual scenarios.

The portable dataset summarizes 787 selected partner rows and retains 176 sampled coordinate pairs supporting the displayed pathway. Its coordinate positions are **sampled pathway-synapse centroids**, not whole-cell anatomical centroids.

## Documentation map

| Document | Use it for |
|---|---|
| [DEVELOPMENT.md](DEVELOPMENT.md) | Local setup, server operation, APIs, common changes, and troubleshooting |
| [ARCHITECTURE.md](ARCHITECTURE.md) | Components, data flow, ownership boundaries, and scientific boundaries |
| [REPRODUCIBILITY.md](REPRODUCIBILITY.md) | Exact six raw files, official links, checksums, rebuild, and output comparison |
| [TESTING.md](TESTING.md) | Validation commands, test intent, and CI environment |
| [CONTRIBUTING.md](CONTRIBUTING.md) | Branch, pull-request, data, and scientific-claim rules |
| [MEMORY_MAP.md](MEMORY_MAP.md) | Detailed engineering handoff and current model behavior |
| [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) | MaleCNS attribution and data licensing |
| [SECURITY.md](SECURITY.md) | Private vulnerability reporting and local-server safety |

## Repository layout

```text
CHRONOS/
├── data/malecns/          portable evidence plus the raw-file manifest
├── dist/                  dependency-free browser UI and canvas renderers
├── scripts/               download, extraction, enrichment, validation, tests
├── server.py              local simulation and HTTP/JSON API
├── requirements-data.txt  optional PyArrow dependency for raw-data rebuilds
└── VERSION                 four-part project version
```

## Architecture at a glance

```text
official MaleCNS v1.0 Feather tables (optional, local, ignored by Git)
                              │
                     extraction + validation
                              │
                  portable attributed JSON evidence
                              │
       modeled world ──> Python simulation/API ──> browser projections
                              │
                 real graph facts + modeled rates
```

Simulation state belongs to the Python server. Camera and observer-frame state belong to the browser. Switching frames does not create another simulation. See [ARCHITECTURE.md](ARCHITECTURE.md).

## API summary

| Endpoint | Purpose |
|---|---|
| `GET /api/health` | Runtime and optional raw-table readiness |
| `GET /api/world` | Current world, fly, senses, needs, pathway, and interaction state |
| `GET /api/world?action=...` | Local experimental controls and stimulus input |
| `GET /api/connectome?circuit=odor\|compass\|pathway` | Portable circuit/pathway evidence |
| `GET /api/worldline` | Recorded trajectory and intervention pivots |
| `GET /api/branches?seeds=1,2,3,4&steps=120` | Four bounded counterfactual futures |

The complete action and response contract is in [DEVELOPMENT.md](DEVELOPMENT.md).

## Validate a checkout

```bash
python -m py_compile server.py
node --check dist/world.js
python -m unittest discover -s scripts -p "test_*.py" -v
python scripts/validate_verified_pathway.py
```

The pathway validator checks evidence structure and bounded computational propagation. It does not establish empirical behavioral validity. See [TESTING.md](TESTING.md).

## Rebuild from official MaleCNS files

Most users should skip this section. Reproduction requires about **24 GB of downloads** plus temporary working space.

```bash
python -m pip install -r requirements-data.txt
python scripts/prepare_malecns_data.py
```

Windows PowerShell users can run the equivalent wrapper:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/prepare_malecns_synapse_data.ps1
```

The versioned manifest at `data/malecns/raw-files.json` defines all six official URLs, byte sizes, and MD5 checksums. Downloads are resumable, verified, stored in `data/malecns/`, and excluded from Git. Use `--list`, `--verify-only`, `--download-only`, or `--build-only` for individual stages.

See [REPRODUCIBILITY.md](REPRODUCIBILITY.md) for direct file links, disk requirements, manual download instructions, expected outputs, and comparison commands.

## Known limitations

- The virtual body and environment are engineered approximations, not a biomechanical Drosophila model.
- Connectome structure does not provide membrane, receptor, neuromodulatory, developmental, or physiological parameters.
- The displayed route is one selected pathway, not the full 166,700-neuron MaleCNS.
- Transmitter predictions do not establish receptor-specific excitatory/inhibitory sign.
- World hazards and cars do not yet use verified MaleCNS sensory pathways.
- Behavioral outputs have not been validated against an empirical fly dataset.

Treat CHRONOS as a transparent hypothesis and visualization instrument, not proof that connectivity alone reproduces a real fly.

## Data, privacy, and resource use

- MaleCNS-derived portable files retain the attribution in [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) and are not relicensed under MIT.
- Raw Feather files are not committed because they total roughly 24 GB and individual files exceed GitHub's file-size limit.
- The server listens only on `127.0.0.1`; no credentials or telemetry are used.
- Raw tables are processed CPU-side and are never sent to the browser. Current GPU use is 0 MB.

## Contributing and license

Contributions are welcome; start with [CONTRIBUTING.md](CONTRIBUTING.md). Code is licensed under [MIT](LICENSE). MaleCNS-derived data remains governed by its original CC-BY terms.
