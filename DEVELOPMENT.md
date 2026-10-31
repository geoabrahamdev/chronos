# Development guide

## Portable setup

```bash
git clone https://github.com/geoabrahamdev/chronos.git
cd chronos
python server.py
```

Open `http://127.0.0.1:4173/`. No package installation is needed for normal runtime work.

Optional isolated environment:

```bash
python -m venv .venv
# PowerShell: .venv\Scripts\Activate.ps1
# bash/zsh: source .venv/bin/activate
python server.py
```

## Development loop

The server serves `dist/` directly, so browser code does not require a build step.

1. Run `python server.py`.
2. Edit `server.py`, `dist/world.js`, `dist/world.css`, or `dist/index.html`.
3. Restart the server after Python changes; hard-refresh after browser changes.
4. Run the checks in [TESTING.md](TESTING.md).

## API and actions

`GET /api/world` advances and returns the authoritative state. Supported `action` values include:

- `pause`, `lesion`, `reset`, `hunger`, `thirst`, `fatigue`, `fear`, `clear_stimuli`
- `stimulus&kind=<dm1|va2|water|shelter|threat>&x=<...>&y=<...>&z=<...>`
- `move_fly&x=<...>&y=<...>&z=<...>`
- `remove&id=<user-source-id>`

Read-only endpoints:

```text
/api/health
/api/connectome?circuit=odor
/api/connectome?circuit=compass
/api/connectome?circuit=pathway
/api/worldline
/api/branches?seeds=1,2,3,4&steps=120
```

Keep actions bounded and local. If an endpoint changes, update README, tests, and this file in the same pull request.

## Working with raw data

The normal app uses committed portable JSON. For full evidence regeneration:

```bash
python -m pip install -r requirements-data.txt
python scripts/prepare_malecns_data.py --list
python scripts/prepare_malecns_data.py
```

Raw Feather inputs and `.part` files are ignored. Never force-add them. See [REPRODUCIBILITY.md](REPRODUCIBILITY.md).

## Coding conventions

- Keep the portable runtime dependency-free.
- Prefer Python standard library and plain browser JavaScript.
- Preserve deterministic seeded behavior in tests.
- Bound UI searches and simulation loops.
- Label connectome-derived fields and CHRONOS-modeled fields separately.
- Add focused regression tests for every bug.
- Do not silently change pathway identities, weights, coordinate semantics, or scientific claims.

## Troubleshooting

### Port 4173 is already in use

Stop the old `python server.py` process, or locate it with `Get-NetTCPConnection -LocalPort 4173` on PowerShell / `lsof -i :4173` on macOS/Linux.

### Browser shows old JavaScript

Hard-refresh (`Ctrl+Shift+R` or `Cmd+Shift+R`). Verify `node --check dist/world.js` and confirm the server was started from the intended checkout.

### BLOCK says it is recording

Return to WORLD for 10–20 seconds so the server accumulates history, then reopen BLOCK. Check `/api/worldline` for a non-empty `history` array.

### Raw rebuild reports a missing file

Run `python scripts/prepare_malecns_data.py --verify-only`. A `FAIL` line identifies the missing, truncated, or checksum-mismatched file. Re-run the downloader; it resumes `.part` files.

### `ModuleNotFoundError: pyarrow`

PyArrow is needed only for raw-data rebuilds. Install `requirements-data.txt`; it is not needed to run `server.py` with the committed portable data.

### First request is slow with local raw tables

The server may scan compressed connectivity data once to cache bounded circuits. Portable-only startup is faster.
