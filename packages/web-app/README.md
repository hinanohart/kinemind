# @kinemind/web-app

Vite + React 19 + Three.js interactive lab for the **Kinematic Mental Mirroring (KMM)** experiment platform.

## Quick start

```bash
# From monorepo root
pnpm install
pnpm -F @kinemind/web-app dev
# → http://localhost:5173
```

## Build

```bash
pnpm -F @kinemind/web-app build   # outputs to dist/
pnpm -F @kinemind/web-app preview # serve dist locally
```

## Type check

```bash
pnpm -F @kinemind/web-app typecheck
```

## Stack

| Layer | Library |
|---|---|
| Bundler | Vite 6 |
| UI framework | React 19 |
| 3D | Three.js 0.170 + @react-three/fiber + @react-three/drei |
| State | Zustand 5 |
| Styling | Tailwind CSS 3 |
| Schema | Zod + @kinemind/shared-types |
| Math | @kinemind/core-math (SE3, coupling matrix) |
| E2E tests | Playwright |

## UX Flow

1. App starts with 8 flat cells (7 hinges).
2. Drag hinge sliders to set physical fold angles.
3. The 3D viewer updates in real time — blue = mental (coupling-derived), red = intent.
4. The coupling heatmap shows the 7×7 matrix for the selected coupling type.
5. In the Mental Prediction panel, enter your subjective predicted angles and mark co-activating hinges.
6. The Diff panel shows per-hinge error and RMSE.
7. Click **Export Trial JSON** to download a `TrialResponse`-schema-validated JSON file.

## Deployment

Deployed to GitHub Pages at `https://hinanohart.github.io/kinemind/`.
Vite `base="/kinemind/"` is set in `vite.config.ts`.
