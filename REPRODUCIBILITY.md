# Reproducing the MaleCNS portable evidence

## Two reproduction levels

### Runtime reproduction

Clone the repository and run `python server.py`. The committed portable JSON is all the app needs.

### Evidence regeneration

To recreate the portable files from official MaleCNS v1.0 exports, reserve about 24 GB for downloads plus working space, install PyArrow, and obtain the six files below.

## Exact official inputs

Place every file in `data/malecns/`. The canonical machine-readable values live in `data/malecns/raw-files.json`.

| File | Bytes | MD5 | Official download |
|---|---:|---|---|
| `body-annotations-male-cns-v1.0-minconf-0.5.feather` | 14,483,314 | `50a7718770c57220f160ba4f431ab89e` | [download](https://storage.googleapis.com/flyem-male-cns/v1.0/connectome-data/flat-connectome/body-annotations-male-cns-v1.0-minconf-0.5.feather) |
| `body-neurotransmitters-male-cns-v1.0.feather` | 43,282,834 | `3d842b12fe5c49eefade528d7dd24a1f` | [download](https://storage.googleapis.com/flyem-male-cns/v1.0/connectome-data/flat-connectome/body-neurotransmitters-male-cns-v1.0.feather) |
| `connectome-weights-male-cns-v1.0-minconf-0.5.feather` | 1,051,241,946 | `f30e9dcca25cfd021bf1e7b3d975599e` | [download](https://storage.googleapis.com/flyem-male-cns/v1.0/connectome-data/flat-connectome/connectome-weights-male-cns-v1.0-minconf-0.5.feather) |
| `syn-partners-male-cns-v1.0-minconf-0.5.feather` | 6,777,179,098 | `58efcf712f8c4d4de5f2ad51e97def76` | [download](https://storage.googleapis.com/flyem-male-cns/v1.0/connectome-data/flat-connectome/syn-partners-male-cns-v1.0-minconf-0.5.feather) |
| `syn-points-male-cns-v1.0-minconf-0.5.feather` | 13,061,489,098 | `c69d08758de07582035cc8843574493a` | [download](https://storage.googleapis.com/flyem-male-cns/v1.0/connectome-data/flat-connectome/syn-points-male-cns-v1.0-minconf-0.5.feather) |
| `tbar-neurotransmitters-male-cns-v1.0.feather` | 2,651,680,218 | `51b02c11690662aedef28f86d394ff0d` | [download](https://storage.googleapis.com/flyem-male-cns/v1.0/connectome-data/flat-connectome/tbar-neurotransmitters-male-cns-v1.0.feather) |

Official index: [MaleCNS downloads](https://male-cns.janelia.org/download/).

## Automated download and rebuild

```bash
python -m venv .venv
# activate the environment for your shell
python -m pip install -r requirements-data.txt
python scripts/prepare_malecns_data.py
```

The script resumes partial downloads into `.feather.part`, verifies size and MD5, atomically accepts each file, rebuilds the portable artifacts, and runs the validator.

Useful stages:

```bash
python scripts/prepare_malecns_data.py --list
python scripts/prepare_malecns_data.py --download-only
python scripts/prepare_malecns_data.py --verify-only
python scripts/prepare_malecns_data.py --build-only
```

PowerShell wrapper:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/prepare_malecns_synapse_data.ps1 --verify-only
```

## Manual download

If browser or external download-manager downloads are more reliable on your connection:

1. Download the six direct links above.
2. Keep the filenames unchanged.
3. Move them into `data/malecns/`.
4. Run `python scripts/prepare_malecns_data.py --verify-only`.
5. Install `requirements-data.txt` and run `python scripts/prepare_malecns_data.py --build-only`.

Do not commit these files. `.gitignore` excludes them.

## Expected outputs

The pipeline updates:

- `portable-circuits.json`
- `verified-odor-motor-path.json`
- `verified-synapse-evidence.json`
- `verified-path-validation.json`

Current high-level invariants:

- 12 selected pathway cells and 11 directed edges;
- aggregate weights from 6 to 211;
- 787 selected synaptic-partner rows;
- 176 retained coordinate pairs in the checked-in sample;
- positive bounded propagation to the motor endpoint;
- every edge has partner, ROI, and transmitter evidence.

Compare regenerated outputs:

```bash
git diff --exit-code -- data/malecns/portable-circuits.json data/malecns/verified-odor-motor-path.json data/malecns/verified-synapse-evidence.json data/malecns/verified-path-validation.json
```

JSON formatting or upstream library ordering can create non-semantic diffs. If that occurs, inspect evidence fields and validator output rather than discarding the difference.

## Reproducibility limits

The pipeline reproduces a selected structural evidence subset and a bounded software model. It does not reproduce biological firing, receptor effects, biomechanics, learning, or experimentally measured behavior. PyArrow is constrained to versions `>=18,<21`; record the exact installed version (`python -m pip freeze`) when publishing a result.
