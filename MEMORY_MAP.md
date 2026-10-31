# CHRONOS memory map

## Mission

Build a local-only, open-world Drosophila behavior sandbox. One fly inhabits a persistent 10x10 isometric 3D terrain: forest edge, orchard, ridge, central clearing, pond, wetland, shelter grove, road verge, flower field, and garden. It senses 3D odor plumes, optic flow, altitude, and XYZ airflow; makes need-driven choices; maintains a 3D heading/home vector; and can lose that function when compass cells are digitally silenced. The interface must always distinguish real HHMI Janelia MaleCNS connectivity from CHRONOS model assumptions.

## Current state

`python server.py` serves the project at `http://127.0.0.1:4173`.

The browser is a perspective 3D canvas world plus a live brain/body map. Its stimulus tray supports native drag-and-drop of DM1 nectar, VA2 yeast, water, shelter, or threat directly onto the isometric ground plane at a selected `z` height (ground, low-flight, or canopy/high). `GRAB FLY` is also draggable and sends an X/Y/Z reposition action. A `PLACED BY YOU` strip exposes one-button removal for each user-created object and a `CLEAR ADDED` action. The camera has orbit, tilt, zoom, reset, and Follow-fly controls; dragging empty meadow space also orbits/tilts the view. The same camera transform is inverted for drag/drop placement. The world has a larger crossable Meadow Road and occasional larger passing cars; only a nearby active car provokes climb-and-evade behavior. The brain panel is deliberately a six-step functional schematic — SMELL, RELAY, CONTEXT, COMPASS, DESCEND, MOVE — rather than a claimed anatomical morphology; it shows the 12 extracted cells / 11 directed edges and separates real graph facts from CHRONOS model rates.

```text
world sources + wind + needs
             ↓
   antenna odor fields / optic flow
             ↓
real MaleCNS selected-edge activity
             ↓
CHRONOS rate/control assumptions
             ↓
casting, heading, home-vector, movement
             ↓
world state and active-edge rendering
```

## What is real versus modeled

| Layer | Status | Detail |
|---|---|---|
| MaleCNS body IDs, cell types, and connection weights | Real | Parsed from the HHMI Janelia MaleCNS v1.0 flat-connectome exports. |
| Odor circuit | Real bounded subgraph | `ORN_DM1` and `ORN_VA2` into their matching `DM1_lPN` and `VA2_adPN` partners. |
| Compass circuit | Real bounded subgraph | `EPG`, `PEN`, `PEG`, and `PFL` intra-circuit edges. |
| Plume physics, need system, rate activation, steering/body dynamics | CHRONOS model | Simple documented assumptions in `server.py`; not a validated whole-brain or spiking model. Resource contact uses a modeled low altitude; threats use a modeled climb-and-evade response. |

Never describe the current model as a complete MaleCNS brain simulation.

## Key files

| File | Role |
|---|---|
| `server.py` | Local HTTP server, MaleCNS Feather parser, bounded circuit extraction, persistent `OpenWorld` state and actions. |
| `dist/index.html` | Local-only open-world interface shell. |
| `dist/world.js` | Canvas rendering and 120 ms polling loop. Renders world, fly, body/brain activation map, controls, telemetry, and edge rows. |
| `dist/world.css` | Responsive world UI styles. |
| `data/malecns/body-annotations-male-cns-v1.0-minconf-0.5.feather` | Ignored MaleCNS v1.0 annotation table, 13 MB. |
| `data/malecns/connectome-weights-male-cns-v1.0-minconf-0.5.feather` | Ignored MaleCNS v1.0 full static connection graph, 1.05 GB. |
| `data/malecns/body-neurotransmitters-male-cns-v1.0.feather` | Ignored official per-neuron predicted-transmitter table, 42 MB. |
| `data/malecns/syn-partners-male-cns-v1.0-minconf-0.5.feather` | Ignored official 6.78 GB synaptic partner-pair table with primary post-synaptic ROI. |
| `data/malecns/syn-points-male-cns-v1.0-minconf-0.5.feather` | Ignored official 13.06 GB synapse-coordinate and hierarchical ROI table. |
| `data/malecns/tbar-neurotransmitters-male-cns-v1.0.feather` | Ignored official 2.65 GB per-presynapse transmitter-probability table. |
| `data/malecns/raw-files.json` | Versioned manifest of the six official downloads, exact sizes, and MD5 identifiers. |
| `data/malecns/verified-odor-motor-path.json` | Committed reproducibly extracted 12-cell / 11-edge MaleCNS pathway used by the bounded rate model. |
| `data/malecns/verified-synapse-evidence.json` | Committed compact derivative containing the 787 selected partner rows' summaries, ROI counts, transmitter means, and coordinate samples. |
| `scripts/extract_verified_odor_motor_path.py` | Revalidates each selected directed edge against the full local graph and joins transmitter predictions. |
| `scripts/enrich_verified_pathway_synapses.py` | Batch-scans the three large synapse tables and attaches only pathway-specific ROI, coordinate, and transmitter evidence. |
| `scripts/prepare_malecns_data.py` | Cross-platform resumable official downloader, exact-size/MD5 verification, enrichment, and validation pipeline. |
| `scripts/prepare_malecns_synapse_data.ps1` | Windows wrapper for the same versioned Python pipeline. |
| `scripts/validate_verified_pathway.py` | Structural and computational validation harness; explicitly does not claim empirical validation. |
| `.gitignore` | Keeps downloaded connectome files out of Git. |

## API contract

### `GET /api/world`

Ticks the persistent local simulation and returns:

- `fly`: normalized x/y/z, heading, continuous-flight speed, 3D trail
- `needs`: hunger, thirst, fatigue, fear on 0–1 scale
- `world`: `span: 10`, biome rectangles, trees, road geometry, intermittent passing cars, wind, home, default and user-created food, water, rest, and threat objects
- `senses`: DM1, VA2, optic flow, altitude, XYZ airflow, XYZ home vector
- `active_edges`: actual selected MaleCNS edge metadata plus current CHRONOS activation scalar
- `pathway`: verified 12-cell route, per-neuron and per-presynapse transmitter predictions, aggregate weights, partner-row counts, primary ROIs, coordinate samples, rate-model values, and validation report
- `compass_enabled`, `event`, `goal`, `behavior` (`flying`), and model disclaimer

Actions use `GET /api/world?action=<pause|lesion|reset|hunger|thirst|fatigue|fear|clear_stimuli>`. A stimulus drag sends `action=stimulus&kind=<dm1|va2|water|shelter|threat>&x=<0.08..9.92>&y=<0.08..9.92>&z=<0..0.72>`. `GRAB FLY` sends `action=move_fly&x=<...>&y=<...>&z=<0.035..0.72>`; an individual removal sends `action=remove&id=<user-source-id>`.

### `GET /api/connectome?circuit=odor|compass`

Returns the bounded real connection table used by the open world.

### `GET /api/health`

Reports exact readiness and byte sizes for the official partner, point, and t-bar transmitter tables; compact evidence status and selected-row count; overall data readiness; and process-owned GPU VRAM. CHRONOS currently uses 0 MB GPU VRAM. The response explicitly states that runtime uses a preprocessed pathway subset and does not send raw tables to the browser.

## Verified evidence

- Python compilation: `python -m py_compile server.py`
- Browser script syntax: `node --check dist/world.js`
- MaleCNS circuit extraction was verified: 161 olfactory-group cells and 160 compass-group cells. The selected odor circuit includes a real `ORN_DM1 → DM1_lPN` edge of weight 202.
- End-to-end extracted path: `ORN_DM1 (925639) → DM1_lPN (10176) → LHPV12a1 (10209) → LHAD1f2 (13435) → SLP101 (515769) → SMP188 (15316) → ExR6 (12506) → PEN_a(PEN1) (513283) → EPG (513284) → PFL2 (518375) → DNa03 (10975) → i1 MN (800637)`. All 11 directed links were revalidated in the local MaleCNS weight graph; weights span 6–211 synapses.
- All three official synapse tables passed their published Google Storage MD5/ETag values on 2026-10-30. The extractor scanned 311,833,243 partner rows, 357,489,383 point rows, and 45,656,140 t-bar transmitter rows without copying the full tables to GPU memory.
- The verified route has 787 selected partner rows. Every edge's partner-row count equals its aggregate graph weight; all 11 edges have a primary post-synaptic ROI and a per-presynapse transmitter prediction. Dominant ROIs progress through `AL(R) → LH(R) → LH(L) → SLP(L) → SIP(L) → CRE(L) → EB → EB → PB → LAL(R) → IntTct`.
- Synapse cleanup removed twelve failed-download range fragments (about 3.2 GB). No range fragments remain; the retained files are official inputs or reproducible pathway-search/validation derivatives.
- Path validation report passes structural stage coverage and bounded-model DM1-to-motor propagation. It is explicitly computational only; no empirical behavioral dataset has yet been compared.
- A local temporary DM1 probe at the fly position drove all 12 pathway-node model rates above the active threshold and produced motor drive `0.044`; the stimulus was then removed. This validates live UI/model coupling, not biological behavior.
- Vertical interaction check: a temporary water source made the fly descend to `z=0.069` before ground contact; a temporary colocated threat engaged `climb / evade` and reached `z=0.550`. Both stimuli were removed and the world reset afterward.
- Expanded-world validation: a raised user DM1 source stored `z=0.56`; relocating the fly onto a moving car triggered `climb / evade` and a peak `z=0.532`. The test source was removed and the world reset.
- 10x10 road validation: on an empty stretch of Meadow Road the fly remained in normal `low approach` behavior; relocating it to the active passing car triggered `climb / evade`. The initial traffic pass has one car so the behavior is visible after startup, then intermittent traffic uses a 14-24 second empty interval.
- Lesion reduced compass edge activity from its enabled level to 5%; restore reactivated real `PEN_a/PEN1 → EPG` edges (64 synapses in `EB`).
- Browser controls changed hunger from 72% to 98% and returned no console errors.
- Need-selection regression on 2026-10-30: the pre-fix deterministic 600-second scenario produced 3,365 water-seeking ticks, zero food contacts, and hunger fixed at 100%. After drive-scale scoring, satiety thresholds, and larger resource-bout gains, the same seeded scenario fed after 18.6 seconds, completed 13 food bouts versus 7 water bouts, and ended at hunger 23.9%, thirst 23.3%, fatigue 30.2%. Three focused regression tests pass.
- Visual regression: canvas telemetry moved from `H-18` to `H-55` and now reads `FLY ALT … • WIND XYZ …`; browser QA confirms it no longer collides with the HTML event bar.

## Exact local run command

```powershell
cd C:\Users\georg\Desktop\SideHustle\github\CHRONOS
python server.py
```

First response after a fresh start can take about 30 seconds: the server scans the compressed connectivity export once to cache both selected circuits. Later ticks are fast.

## GPU policy

User has an NVIDIA RTX 3050 Laptop GPU with 4 GB VRAM and authorized up to 2 GB for CHRONOS. Do not allocate more than 2 GB. The 1.05 GB MaleCNS Feather graph is memory-mapped and scanned CPU-side. If adding dynamics, use a bounded subgraph and an explicit memory budget, never the whole MaleCNS graph.

## Highest-value next steps

1. Replace unsigned rate gains with receptor-aware sign assumptions backed by neurotransmitter/receptor evidence, then test them.
2. Add a scenario-file editor for exact source parameters and removal/editing of user-placed stimuli.
3. Compare deterministic pathway scenarios against an external experimental dataset before any claim of biological behavioral validation.
4. Add a play/pause/replay event log, JSON export, and frame recording only after simulation behavior is deterministic.

## Data provenance

The local Feather files were downloaded from the official HHMI Janelia MaleCNS v1.0 static export bucket:

`https://storage.googleapis.com/flyem-male-cns/v1.0/connectome-data/flat-connectome/`

The public flat connection table gives body-to-body weights. The local 42 MB body-transmitter table supplies per-neuron prediction/confidence. The local partner, point, and t-bar tables now supply pathway-specific primary ROIs, exact 8 nm-voxel synapse coordinates, hierarchical ROI membership, and transmitter probabilities at selected presynaptic sites. These predictions still do not establish receptor-specific excitatory or inhibitory sign.

## Known limits and pitfalls

- Raw Feather files under `data/malecns/` are intentionally Git-ignored; the portable evidence and raw-file manifest are committed. A new machine needs no raw download to run the app, but must download all six official inputs before regenerating the evidence. The browser reads only compact derived JSON, never the multi-gigabyte synapse tables directly.
- The world uses normalized coordinates; UI drawing maps them into canvas pixels.
- The world is now 10x10 model units, not 1x1. Default sources are spatially distributed across ten biomes; user drops accept x/y values within approximately 0.08-9.92 and z values 0-0.72. Camera projection divides coordinates by `WORLD_SPAN` so the full terrain remains visible.
- The camera is browser-local view state, not part of the simulation state. Default is 45 degrees and 1.0x; `FOLLOW` changes camera focus to the moving fly.
- The current behavior layer intentionally has no stationary gate: the fly continuously flies and samples resources while moving. It uses a modeled Z altitude and 3D plume attenuation; these remain model assumptions, not direct temporal recordings from the connectome.
- Resource arrival is now genuinely 3D: food, water, and shelter require horizontal distance below `0.13` plus vertical gap below `0.025` from a modeled contact height (`source z + 0.045`). The visible `VERTICAL MODE` reports cruise, low approach, landing, departing, or climb / evade; these are CHRONOS behavior rules, not experimentally validated motor trajectories.
- Road traffic is a CHRONOS world model: a single larger passing car appears for 5-8 seconds, then traffic is absent for a randomized 14-24 seconds. Meadow Road is crossable, and only an active car within 0.55 model units becomes a 3D hazard. Cars are not represented by a MaleCNS sensory pathway yet; the response is an explicit modeled climb-and-evade rule.
- Resource choice compares hunger, thirst, and fatigue on a common 0-1 drive scale; odor/proximity only break ties. Water is suppressed below 20% thirst, shelter below 28% fatigue, and food below 16% hunger. Contact starts a persistent modeled interaction: feeding 3.5 seconds, drinking 2.5 seconds, or resting 10 seconds. The fly holds position and the need falls gradually; a progress ring, percentage, and remaining time are shown. Completion reduces food/water/rest drive by up to 62/85/60 percentage points, then applies an 8/12/12-second source cooldown and 1.8-second departure. A close threat interrupts the interaction.
- The static edge list has synapse counts but does not itself define biophysical membrane dynamics, receptor models, odor tuning, or motor biomechanics.
- Keep the local-only rule: no new deployment, no cloud API, no ChatGPT integration.
