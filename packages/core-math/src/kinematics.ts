/**
 * Forward kinematics for a 1D origami strip.
 *
 * Cell 0's local frame coincides with the world frame: origin at the
 * leading-edge midpoint, +X pointing along the chain, +Y along the hinge axis.
 * Cell i's frame is obtained from cell (i-1)'s frame by:
 *   1. translating by L_{i-1} along the cell's +X axis (to the shared edge),
 *   2. rotating by theta_{i-1} about the cell's +Y axis (the hinge),
 *
 * which is the standard Denavit-Hartenberg pattern restricted to 1-DoF
 * revolute joints in a planar chain. The resulting cell positions are the
 * leading-edge midpoints of each cell.
 */

import {
  type SE3,
  SE3_IDENTITY,
  type Vec3,
  rot,
  se3Apply,
  se3Compose,
  trans,
  v3Add,
  v3Scale,
} from "./se3.js";
import {
  CELL_X_AXIS,
  CELL_Y_AXIS,
  CELL_Z_AXIS,
  type StripConfig,
  type StripState,
} from "./strip.js";

export interface CellPose {
  /** Pose of the cell's local frame relative to world. */
  readonly frame: SE3;
  /** Leading-edge midpoint position. */
  readonly position: Vec3;
}

export interface KinematicsResult {
  readonly cells: readonly CellPose[];
  /** Centroids of every cell (leading + trailing edges averaged). */
  readonly centroids: readonly Vec3[];
}

/**
 * Compute world-frame poses for every cell. Runs in O(nCells) time.
 * Throws if the state shape disagrees with the strip config.
 */
export function forwardKinematics(
  config: StripConfig,
  state: StripState,
): KinematicsResult {
  if (state.thetas.length !== config.nCells - 1) {
    throw new Error(
      `forwardKinematics: expected ${config.nCells - 1} hinge angles, got ${state.thetas.length}`,
    );
  }

  const cells: CellPose[] = [];
  const centroids: Vec3[] = [];
  let frame: SE3 = SE3_IDENTITY;

  for (let i = 0; i < config.nCells; i++) {
    const position = se3Apply(frame, [0, 0, 0]);
    cells.push({ frame, position });
    const cellLength = config.cellLengths[i] ?? 0;
    centroids.push(se3Apply(frame, [cellLength * 0.5, 0, 0]));

    if (i < config.nCells - 1) {
      const Li = config.cellLengths[i] ?? 0;
      const theta = state.thetas[i] ?? 0;
      // Translate to the shared edge, then rotate about the hinge axis.
      frame = se3Compose(
        frame,
        se3Compose(trans([Li, 0, 0]), rot(CELL_Y_AXIS, theta)),
      );
    }
  }

  return { cells, centroids };
}

/**
 * Local-frame corner offsets of a unit-width cell with edge L along +X.
 * Returns the four corners in CCW order viewed from +Z.
 */
export function cellCornersLocal(cellLength: number): readonly Vec3[] {
  const half = 0.5;
  return [
    [0, -half, 0],
    [cellLength, -half, 0],
    [cellLength, half, 0],
    [0, half, 0],
  ];
}

/**
 * World-frame corners of every cell, suitable for collision tests and rendering.
 */
export function cellCornersWorld(
  config: StripConfig,
  result: KinematicsResult,
): readonly (readonly Vec3[])[] {
  const out: Vec3[][] = [];
  for (let i = 0; i < config.nCells; i++) {
    const cellLength = config.cellLengths[i] ?? 0;
    const cell = result.cells[i];
    if (!cell) continue;
    const local = cellCornersLocal(cellLength);
    out.push(local.map((p) => se3Apply(cell.frame, p)));
  }
  return out;
}

/**
 * Axis-aligned bounding box from a cloud of points.
 */
export function computeAabb(points: readonly Vec3[]): {
  min: Vec3;
  max: Vec3;
} {
  if (points.length === 0) {
    return { min: [0, 0, 0], max: [0, 0, 0] };
  }
  const first = points[0]!;
  let minX = first[0];
  let minY = first[1];
  let minZ = first[2];
  let maxX = first[0];
  let maxY = first[1];
  let maxZ = first[2];
  for (let i = 1; i < points.length; i++) {
    const p = points[i]!;
    if (p[0] < minX) minX = p[0];
    if (p[1] < minY) minY = p[1];
    if (p[2] < minZ) minZ = p[2];
    if (p[0] > maxX) maxX = p[0];
    if (p[1] > maxY) maxY = p[1];
    if (p[2] > maxZ) maxZ = p[2];
  }
  return { min: [minX, minY, minZ], max: [maxX, maxY, maxZ] };
}

export function aabbOverlap(
  a: { min: Vec3; max: Vec3 },
  b: { min: Vec3; max: Vec3 },
  tol = 1e-9,
): boolean {
  return (
    a.min[0] <= b.max[0] + tol &&
    a.max[0] + tol >= b.min[0] &&
    a.min[1] <= b.max[1] + tol &&
    a.max[1] + tol >= b.min[1] &&
    a.min[2] <= b.max[2] + tol &&
    a.max[2] + tol >= b.min[2]
  );
}

/**
 * Detect self-intersection between non-adjacent cells using a broad-phase
 * AABB pass. The exact narrow-phase SAT check is intentionally omitted in
 * the v0.1 release: the AABB pass already catches every case that matters
 * for an interactive viewer, and full SAT belongs in MATH.md tests where
 * we can assert the algebraic guarantees properly.
 *
 * Returns the first colliding pair (i, j) with j > i + 1, or null.
 */
export function detectSelfIntersectionAabb(
  config: StripConfig,
  result: KinematicsResult,
): [number, number] | null {
  const corners = cellCornersWorld(config, result);
  const aabbs = corners.map(computeAabb);
  for (let i = 0; i < aabbs.length; i++) {
    for (let j = i + 2; j < aabbs.length; j++) {
      const a = aabbs[i]!;
      const b = aabbs[j]!;
      if (aabbOverlap(a, b)) {
        return [i, j];
      }
    }
  }
  return null;
}

/**
 * Numerical Jacobian of the i-th cell centroid with respect to the hinge
 * angle vector, computed by central finite differences. O(nCells^2).
 */
export function centroidJacobian(
  config: StripConfig,
  state: StripState,
  cellIndex: number,
  h = 1e-5,
): readonly Vec3[] {
  const n = state.thetas.length;
  const J: Vec3[] = [];
  for (let k = 0; k < n; k++) {
    const tPlus = [...state.thetas];
    const tMinus = [...state.thetas];
    tPlus[k] = (tPlus[k] ?? 0) + h;
    tMinus[k] = (tMinus[k] ?? 0) - h;
    const plus = forwardKinematics(config, { thetas: tPlus }).centroids[cellIndex];
    const minus = forwardKinematics(config, { thetas: tMinus }).centroids[cellIndex];
    if (!plus || !minus) {
      J.push([0, 0, 0]);
      continue;
    }
    const diff = v3Scale(
      [plus[0] - minus[0], plus[1] - minus[1], plus[2] - minus[2]],
      1 / (2 * h),
    );
    J.push(diff);
  }
  return J;
}

/** Re-export common axes for callers building stimuli on top of the strip. */
export const STRIP_AXES = {
  cellX: CELL_X_AXIS,
  cellY: CELL_Y_AXIS,
  cellZ: CELL_Z_AXIS,
} as const;

/**
 * Orientation reproduction helper. Compose all hinge rotations into a single
 * transform applied to v. Useful for unit tests that round-trip a unit vector.
 */
export function chainRotateVector(
  config: StripConfig,
  state: StripState,
  v: Vec3,
): Vec3 {
  const { cells } = forwardKinematics(config, state);
  const last = cells[cells.length - 1];
  if (!last) {
    return v;
  }
  return v3Add([0, 0, 0], se3Apply({ q: last.frame.q, t: [0, 0, 0] }, v));
}
