# Portable MaleCNS runtime data

This directory contains the small, attributed subset needed to run CHRONOS without committing the official multi-gigabyte Feather tables.

| File | Purpose |
|---|---|
| `raw-files.json` | Canonical official raw-file URLs, exact byte sizes, and published MD5 identifiers used by the downloader |
| `portable-circuits.json` | Precomputed odor and compass circuit summaries derived from MaleCNS v1.0 annotations and aggregate connection weights |
| `verified-odor-motor-path.json` | Selected 12-cell, 11-edge ORN_DM1-to-i1-motor route with evidence metadata |
| `verified-path-validation.json` | Reproducible structural and bounded-propagation validation results |
| `verified-synapse-evidence.json` | Selected partner rows, primary ROI evidence, coordinate samples, and presynaptic transmitter evidence |

The raw official files are intentionally ignored. To obtain and verify them on any supported operating system, run `python scripts/prepare_malecns_data.py` from the repository root after installing `requirements-data.txt`. The PowerShell wrapper `scripts/prepare_malecns_synapse_data.ps1` runs the same versioned pipeline.

Exact direct links, checksums, manual-download instructions, expected outputs, and comparison commands are documented in [`REPRODUCIBILITY.md`](../../REPRODUCIBILITY.md).

MaleCNS attribution and reuse terms are recorded in `THIRD_PARTY_NOTICES.md`.
