# Changelog

All notable changes to kinemind are documented here. The format is based
on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and this
project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
