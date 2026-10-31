# Contributing to CHRONOS

Thank you for improving CHRONOS. Contributions should preserve its strongest property: the UI clearly separates connectome evidence from authored simulation behavior.

## Before opening a pull request

1. Fork or branch from current `main`.
2. Keep each change focused and add a regression for behavior changes.
3. Run the full commands in [TESTING.md](TESTING.md).
4. Update documentation when commands, APIs, controls, data, or claims change.
5. Review `git status` and ensure no raw Feather file, `.part` download, secret, cache, or generated media is staged.

Suggested branch names: `feature/...`, `fix/...`, or `docs/...`.

## Scientific-claim rules

- Say **MaleCNS-derived** only for values traceable to the portable evidence or official raw tables.
- Say **CHRONOS model** for rates, behaviors, needs, steering, physics, timings, and counterfactuals.
- Call current positions **sampled pathway-synapse centroids**, not anatomical or whole-cell centroids.
- Do not describe structural/computational validation as empirical behavioral validation.
- Cite the source and add provenance metadata for any new biological fact.
- Do not imply endorsement by HHMI Janelia, Google Research, or other data contributors.

## Data policy

Do not commit the six raw Feather files. They total about 24 GB, and several exceed GitHub limits. Modify `data/malecns/raw-files.json` only when the official release changes, and include evidence for new sizes/checksums.

Portable derived data may be updated when the pipeline is reproducible, attribution remains intact, and the pull request explains why the derivative changed.

## Pull requests

The pull-request body should state:

- what changed and why;
- which layer changed: evidence, model, or projection;
- validation commands and results;
- any scientific limitation or claim change;
- screenshots for visible UI changes.

Maintainers may ask for a smaller change if evidence extraction, model dynamics, and visual redesign are mixed together.

## Reporting bugs and proposing features

Use the issue templates. Include OS, Python/browser versions, reproduction steps, expected/actual behavior, and whether raw tables were installed. Do not post credentials or private system information.

## License and attribution

Code contributions are accepted under the repository's MIT license. MaleCNS-derived content remains subject to the source dataset's CC-BY terms and [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).
