# Changelog

All notable changes to kinemind are documented here. The format is based
on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and this
project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.0] — 2026-04-27

Three-pillar major upgrade delivered by parallel architect / designer /
analyst executors.

### Added — Math / core
- Bayesian coupling estimation (`origami_lab.bayes`) with numpyro + jax,
  Schur-reduced parametrisation, simulation-based calibration (Talts 2018).
- SAT narrow-phase self-intersection (`@kinemind/core-math/collision`,
  `origami_lab.collision`); TS↔Python parity 1e-12.
- Bootstrap CI for coupling matrix (`estimate_coupling_with_ci`); 95%
  coverage tested on synthetic mirror data.
- `TreeStrip` generalisation (`@kinemind/core-math/tree`,
  `origami_lab.tree`); path graph backward-compat at atol = 1e-15.

### Added — Web app
- Bundle code-split (Three.js / R3F lazy-loaded). Initial JS bundle
  drops from 309 KB → **23.5 KB gzip** (−92.4 %).
- `NCellsControl` (range 4–32 cells).
- Spectral-mode visualizer with closed-form mirror eigenvalues.
- Keyboard shortcuts (1–9 to focus hinges, `?` for help).
- `ErrorBoundary` for WebGL crash recovery.
- `sessionStorage` trial-history persistence (Prolific-compatible).
- WAI-ARIA cleanup; axe-core Playwright a11y CI gate (WCAG 2 AA).

### Added — Cognitive infrastructure
- Pre-registration schema (zod + dataclass + YAML + OSF JSON-LD).
- `origami-lab power` CLI for H1 mixed-effects power simulation.
- IRB template set: PIS, consent, debrief, DMP, README.
- AQ-10 / MRT (Vandenberg–Kuse) / VVIQ-2 individual-difference schemas.
- `EXPERIMENT_PROTOCOL.md` expanded (2.4 KB → 10 KB) with H1-only scope,
  attention checks, OSF procedure, power curve, covariates.

### Fixed
- `solveLinearSystem` adaptive singular threshold (TS + Python).
- `reflectState` 0-indexed doc comment.
- Removed unused `groupAction` import in coupling.ts.

### Tests
- TypeScript: 45 → **65** (+20 across collision, tree, coupling, symmetry).
- Python: 96 → **183** (+87 across bayes, collision, tree, preregistration,
  power, individual differences). Numerical parity maintained.

## [0.1.0] — 2026-04-27

Initial public release.

### Added

* `@kinemind/core-math` — SE(3) kinematics, V₄ symmetry, mental coupling
  matrix, with 45 unit and property tests.
* `@kinemind/shared-types` — zod schemas for strips, trials, sessions,
  coupling matrices, subjects.
* `@kinemind/web-app` — React 19 + Three.js interactive viewer, hinge
  sliders, prediction panel, coupling heatmap, JSON export, Playwright
  e2e smoke test.
* `origami-lab` — Python 3.12 numerical mirror with 96 tests
  (≥ 90% coverage) and 1e-15 numerical parity to the TypeScript kernel.
* MIT license, CITATION.cff, CONTRIBUTING.md, CODE_OF_CONDUCT.md,
  SECURITY.md.
* GitHub Actions CI: lint, typecheck, TS tests, Python tests, build.
* CodeQL scanning, gitleaks pre-merge job.
