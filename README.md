# kinemind

> A research platform for **Kinematic Mental Mirroring (KMM)** — the
> phenomenon where folding one hinge of an articulated object in your head
> involuntarily folds another.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![CI](https://github.com/hinanohart/kinemind/actions/workflows/ci.yml/badge.svg)](https://github.com/hinanohart/kinemind/actions/workflows/ci.yml)
[![Tests](https://img.shields.io/badge/tests-141%20passing-brightgreen)](#testing)

---

## The phenomenon

Imagine an 8-cell paper strip. Pick one hinge and try to fold it in your
head. Most people report that the *symmetric* hinge bends along with it,
even though no one asked it to. The same thing happens for chairs,
robotic arms, umbrellas — any articulated object you fold in imagery.

We call this **Kinematic Mental Mirroring (KMM)**. It is not the same as
mental rotation, mental folding (PFT), or kinaesthetic motor imagery: the
target hinge moves *because you tried*, the other one moves *because the
mind cannot help it*. kinemind's job is to make this measurable.

## What lives here

| Package | Stack | Purpose |
|---|---|---|
| [`@kinemind/core-math`](packages/core-math) | TypeScript | SE(3) kinematics, V₄ symmetry group, mental coupling matrix |
| [`@kinemind/shared-types`](packages/shared-types) | TypeScript + zod | Single source of truth for trial / strip / coupling / subject schemas |
| [`@kinemind/web-app`](packages/web-app) | React 19 + Three.js + Zustand | Interactive 3D strip viewer, prediction panel, coupling heatmap |
| [`origami-lab`](python/origami_lab) | Python 3.12 + NumPy/SciPy | Numerically identical Python implementation, statistical analysis CLI |

The TypeScript and Python implementations are **bit-compatible to 1e-15
absolute tolerance** (`tests/test_parity_with_ts.py`), so a coupling matrix
fit in the browser is reproducible from a Jupyter notebook and vice versa.

## Quick start

### Web app (interactive viewer)

```bash
git clone https://github.com/hinanohart/kinemind.git
cd kinemind
pnpm install
pnpm dev
# → http://localhost:5173/kinemind/
```

Drag the seven sliders, watch the 3D strip fold, and see the **mental
prediction** layer (blue) drift away from the **physical truth** layer
(red) when β > 0.

### Python analysis

```bash
cd python/origami_lab
uv venv --python 3.12
uv pip install -e ".[test]"
uv run pytest
uv run origami-lab --help
```

## Citing

If kinemind contributes to a publication, please cite it via the metadata
in [`CITATION.cff`](CITATION.cff). A Zenodo DOI is minted on every
tagged release.

```bibtex
@software{kinemind2026,
  author  = {hinanohart and kinemind contributors},
  title   = {kinemind: A research platform for Kinematic Mental Mirroring},
  year    = {2026},
  url     = {https://github.com/hinanohart/kinemind},
  license = {MIT}
}
```

## Documentation

* [`MATH.md`](MATH.md) — SE(3) kinematics, Schur-lemma reduction of the coupling matrix to the V₄-equivariant subspace
* [`ARCHITECTURE.md`](ARCHITECTURE.md) — monorepo layout, dual-source-of-truth strategy, parity tests
* [`EXPERIMENT_PROTOCOL.md`](EXPERIMENT_PROTOCOL.md) — IRB-ready protocol, sample-size calculations, jsPsych template
* [`CONTRIBUTING.md`](CONTRIBUTING.md)
* [`SECURITY.md`](SECURITY.md)
* [`CODE_OF_CONDUCT.md`](CODE_OF_CONDUCT.md)

## Testing

```bash
# All TypeScript tests (45 in core-math + e2e in web-app)
pnpm -r --parallel test

# All Python tests (96 unit + property + parity)
cd python/origami_lab && uv run pytest
```

## License

[MIT](LICENSE)
