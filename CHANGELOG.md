# Changelog

All notable changes to CHRONOS are documented here.

## [1.0.0.0] - 2026-10-30

### Added

- Explore a local 10 × 10 three-dimensional fly world through WORLD, FLY, and BLOCK observer frames.
- Inspect one verified 12-cell, 11-edge MaleCNS pathway as a rotatable 3D wiring view with sampled pathway-synapse centroids, real aggregate weights, and modeled live activity.
- Compare four bounded futures from the current state: baseline, sated, exhausted, and a scrambled-pathway control.
- Open neuron evidence cards, use keyboard shortcuts, and start a guided demonstration from the first-run help screen.
- Validate pathway coordinates, runtime activity fields, counterfactual determinism, and live-state isolation with automated regressions.

### Changed

- Report sampled coordinate evidence as 176 retained partner pairs from 787 selected rows, without double-counting pre/post endpoints.
- Keep world goals, compass behavior, and hazard avoidance unchanged in the scrambled-pathway comparison so wiring effects are not confounded with a control-policy ablation.
- Label the brain viewer with native MaleCNS X/Y/Z voxel axes until an anatomical orientation transform is explicitly verified.

### Fixed

- Align all help text, tooltips, API examples, and controls with the four available counterfactual scenarios.
- Distinguish MaleCNS-derived values from CHRONOS-authored functional stages, live rates, behavior, and physics.
