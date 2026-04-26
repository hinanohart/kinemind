# Architecture

kinemind is a pnpm + uv monorepo with two complementary stacks:

* **TypeScript packages** drive the interactive web app (`packages/`).
* **Python package** drives statistical analysis and reproducible
  notebooks (`python/origami_lab/`).

Both implementations share the same mathematical contract. Their parity
is enforced by `python/origami_lab/tests/test_parity_with_ts.py`, which
loads a golden strip configuration from
`tests/data/golden_strip_8.json`, reproduces forward kinematics in
NumPy, and asserts agreement to 1e-15.

## Dependency graph

```
shared-types (zod)             core-math (TS)
        \                       /     \
         \                     /       \
        web-app (React + R3F)  ------>  origami-lab (Python, mirrored)
```

## Single-source-of-truth strategy

* Trial / strip / coupling / subject **types** live in
  `packages/shared-types/src/*.ts` as zod schemas.
* The Python pipeline parses the same JSON via
  `origami_lab.io.load_session_data`, raising on schema drift.
* On every commit, CI runs both test suites and the parity test as a
  gate.

## Build & release

* `pnpm build` compiles the TypeScript packages to `dist/`.
* `pnpm test` runs Vitest across packages.
* `uv run pytest` runs Python suite.
* Release flow uses [Changesets](https://github.com/changesets/changesets);
  GitHub Pages serves the web app from `packages/web-app/dist/` on tag.

## Why no `gl-matrix`?

The SE(3) kernel is small (~250 lines) and audited line-by-line against
[`MATH.md`](MATH.md). Owning it removes a black-box dependency from the
critical path of every claim made in the paper.
