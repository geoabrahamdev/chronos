# Observer-Frames Reality Lab — Build Plan

## One-line pitch

A three-frame observer toggle on CHRONOS: god-view (existing), fly-view (first-person sensory), and block-view (4D worldline plus counterfactual branches), rendered on the same unchanged simulation core.

## Why this exists

CHRONOS currently shows a single third-person god view. The same simulation state is far richer: it has an *interior* (what the fly senses) and an *extensive* (its full trajectory plus counterfactual alternatives). Observer-frames expose both without inventing new biology or physics. The addition is credential-building and honestly defensible — not a consciousness, quantum, or Gateway-adjacent claim.

## Architecture principles

- Simulation state owned by the server; view state owned by the client.
- Each frame is a projection of the same tick, never a parallel simulation.
- Deterministic replay: given (seed, snapshot, inputs) any branch is reproducible.
- Real-vs-modeled distinction preserved in every frame; no frame may obscure which data is HHMI Janelia and which is a CHRONOS assumption.
- Zero biophysical additions. The verified pathway rate model is untouched.
- CPU-side only. The 2 GB VRAM budget remains at 0 MB used.

## Deliverable 1 — Block-frame (worldline renderer)

### Server
- `trail_history` ring buffer on `OpenWorld`, independent of `fly["trail"]`.
  - Entries: `{tick, wall, x, y, z, heading, speed, compass, mode, interaction}`.
  - Capacity: 500 entries (~60 s at 120 ms tick).
  - Reset by `reset()`; preserved across `move_fly` so the reposition is recorded as a tracked event.
- `pivots` list tracking user-triggered events: lesion toggle, stimulus drop, fly reposition, stimulus removal, clear.
  - Entries: `{tick, wall, kind, detail}`. Capacity 100.
- Endpoint `GET /api/worldline` returning `{history, pivots, tick, world_span}`.

### Client
- Frame-toggle buttons `WORLD / FLY / BLOCK` in the world-card header.
- Block-frame rendering:
  - Extrude recorded worldline as a tube in the existing isometric canvas.
  - Color gradient by time (dim-old to bright-new).
  - Thickness by speed.
  - Hue shift on lesioned segments so compass-off runs read visually.
  - Markers at pivot events.
- Time-slice slider scrubs a cursor along the worldline and shows the fly ghost at that tick.
- Optional overlay: classical max-speed reach cone from the cursor, honestly labeled.

## Deliverable 2 — Fly-frame (first-person observer)

### Server
No changes.

### Client
- Blacken the canvas outside a sensory horizon radius (a single documented model constant).
- Within the horizon render only: ground tiles, odor plumes sized by DM1 / VA2 scalars from `senses`, airflow arrows from `senses.airflow`, nearest hazard glow when `fear > 0.3`.
- Keep the brain panel visible — it *is* the fly's sight in this frame.
- Permanent caption: "first-person projection; CHRONOS sensory model".
- Pure view switch: no simulation pause and no state change.

## Deliverable 3 — Counterfactual branches

### Server
- `self.snapshot_state()` returning full deterministic state (fly, needs, world sources including user-created, cooldowns, interaction, flight, pathway_rates, waypoints, depart, traffic timers, tick, compass).
- `self.restore_state(snapshot)` reinstating exactly.
- Endpoint `GET /api/branches?from_tick=N&seeds=S1,S2,...&steps=K`.
- Instance-local `random.Random(seed)` so branches are reproducible. This is the only touch to the simulation core.

### Client
- Branch controls inside block-frame.
- "Branch here" button active when the time cursor sits at a pivot event.
- Select 2–4 counterfactual seeds or toggle "lesion inverted".
- Branched worldlines rendered as dimmed overlay tubes with a legend distinguishing realized from counterfactual.

## Shared UI / architecture pieces

- A `FrameController` module in the client owning current frame and dispatching render calls.
- Each draw function receives `(data, frame)` and renders accordingly.
- Camera remains browser-local view state; the frame does not alter it.

## Validation requirements

- `python -m py_compile server.py` after every server change.
- `node --check dist/world.js` after every client change.
- Existing 600-s deterministic resource-selection regression must still pass unchanged.
- Existing lesion regression: compass-off reduces compass edge activity to the same proportion as before.
- Block-frame visually reproduces the recorded worldline from `/api/worldline`.
- Fly-frame renders no world content outside the sensory horizon radius.
- Counterfactual replay: identical seed from an identical snapshot produces an identical trajectory.
- Visual regression: existing telemetry line (`FLY ALT … • WIND XYZ …`) stays readable and uncollided.

## Content strategy

One ship produces two threads per feature: a pop thread (visual, broad audience) and an architecture thread (narrow, credential-building).

| Feature | Pop angle | Architecture angle |
|---|---|---|
| Block-frame | "A fly's life as a 4D worldline on a real connectome." | "Separating sim-state from view-state: tracking the worldline server-side." |
| Fly-frame | "Same fly, same tick, two observers." | "First-person rendering as a projection, not a rewrite." |
| Counterfactual branches | "What a lesion changes vs. what it only reveals." | "Deterministic branching replay from an MD5-verified connectome pipeline." |

Capstone post links all three with a short write-up.

## Out of scope (explicit)

- IIT / Φ computation.
- Causal emergence metrics.
- Markov blanket overlays.
- Any Gateway Process, consciousness, quantum, or Bentov framing in copy or UI.
- GPU usage. Stays at 0 MB.
- Scenario file editor, event-log export, frame recording.
- Any change to the HHMI Janelia data pipeline.
- Any claim of empirical behavioral validation.

## Known risks and mitigations

- UI clutter from frame toggle, time slider, branch controls. *Three top-level buttons in the world-card head; everything else revealed per-frame.*
- Scope creep from counterfactuals into a scenario editor. *Branches are read-only from the client, driven by seed plus lesion flip only.*
- Replay drift from `time.monotonic()` dependencies in step(). *Snapshot captures the wall offset; replays use a virtual clock seeded from the snapshot.*
- Frame-toggle confusing the real-vs-modeled discipline. *Every frame renders the existing REAL DATA badge and model disclaimer.*

## First concrete step

Server: `trail_history` ring buffer, `pivots` list, and `GET /api/worldline` endpoint. This unblocks the block-frame renderer without touching rendering yet.
