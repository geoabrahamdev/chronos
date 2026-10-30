# Portable MaleCNS runtime data

This directory contains the small, attributed subset needed to run CHRONOS without committing the official multi-gigabyte Feather tables.

| File | Purpose |
|---|---|
| `portable-circuits.json` | Precomputed odor and compass circuit summaries derived from MaleCNS v1.0 annotations and aggregate connection weights |
| `verified-odor-motor-path.json` | Selected 12-cell, 11-edge ORN_DM1-to-i1-motor route with evidence metadata |
| `verified-path-validation.json` | Reproducible structural and bounded-propagation validation results |
| `verified-synapse-evidence.json` | Selected partner rows, primary ROI evidence, coordinate samples, and presynaptic transmitter evidence |

The raw official files are intentionally ignored. To obtain and verify them, run `scripts/prepare_malecns_synapse_data.ps1` from the repository root after installing `requirements-data.txt`.

MaleCNS attribution and reuse terms are recorded in `THIRD_PARTY_NOTICES.md`.
