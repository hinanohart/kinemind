# @kinemind/core-math

SE(3) kinematics, V₄ symmetry group action, and mental coupling matrix
primitives for 1D origami strips. Pure TypeScript, dependency-free at
runtime, audited line-by-line against `MATH.md`.

## Install

```bash
pnpm add @kinemind/core-math
```

## Usage

```ts
import {
  forwardKinematics,
  makeUniformStrip,
  mirrorCouplingMatrix,
  applyCoupling,
} from "@kinemind/core-math";

const strip = makeUniformStrip(8); // 8 cells, 7 hinges
const intent = [Math.PI / 4, 0, 0, 0, 0, 0, 0]; // user wants to fold hinge 0
const C = mirrorCouplingMatrix(7, 0.6); // β = 0.6 mirror coupling
const mental = applyCoupling(C, intent); // what the brain pictures

const { cells, centroids } = forwardKinematics(strip, { thetas: [...mental] });
```

## API

* `se3` — quaternion algebra, SE(3) compose/inverse/apply, mat4 ⇄ SE(3)
* `strip` — `StripConfig`, `StripState`, V₄ helpers (`reflectState`, `flipState`)
* `kinematics` — `forwardKinematics`, AABB self-intersection, centroid Jacobians
* `symmetry` — V₄ group action, Reynolds projection, equivariance residual
* `coupling` — `mirrorCouplingMatrix`, `estimateCoupling` (LSQ + Tikhonov + group constraint), `spectralRadius`, `effectiveRank`

## License

MIT
