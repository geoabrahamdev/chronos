# Testing and validation

## Full portable validation

Run from the repository root:

```bash
python -m py_compile server.py
node --check dist/world.js
python -m unittest discover -s scripts -p "test_*.py" -v
python scripts/validate_verified_pathway.py
```

## What the checks establish

| Check | Establishes | Does not establish |
|---|---|---|
| Python compile | Source parses | Runtime behavior is correct |
| JavaScript syntax | Browser script parses | Visual or accessibility correctness |
| Unit/regression suite | Documented deterministic model invariants | Biological validity |
| Pathway validator | Required stages, positive weights, evidence fields, bounded propagation | Measured neural firing or fly behavior |
| Raw-data `--verify-only` | Exact local file sizes and MD5 values | Scientific suitability of the source dataset |

## CI environment

GitHub Actions runs on Ubuntu with Python 3.12 and Node.js 22. The workflow is `.github/workflows/ci.yml` and runs on every push and pull request.

## Manual browser smoke test

1. Start `python server.py` and open `http://127.0.0.1:4173/`.
2. Confirm WORLD moves and needs update.
3. Drag a stimulus and the fly to distinct X/Y/Z positions; remove the stimulus.
4. Open FLY and verify the sensory-horizon explanation.
5. Open BLOCK after at least 15 seconds; scrub time and generate four branches.
6. Silence and restore compass; confirm the marker and segment colors change.
7. Rotate the pathway viewer and confirm the browser stays responsive.
8. Check the developer console for uncaught errors.

## Raw-data verification

Without downloading anything:

```bash
python scripts/prepare_malecns_data.py --list
```

With the six local inputs present:

```bash
python scripts/prepare_malecns_data.py --verify-only
python scripts/prepare_malecns_data.py --build-only
git diff -- data/malecns/portable-circuits.json data/malecns/verified-odor-motor-path.json data/malecns/verified-path-validation.json data/malecns/verified-synapse-evidence.json
```

A clean diff is the strongest current reproduction check for the portable evidence.
