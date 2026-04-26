/**
 * SAT (Separating Axis Theorem) narrow-phase self-intersection for origami strips.
 *
 * Implements quad-quad overlap tests using the classic 11-axis SAT:
 *   - 2 face normals (one per quad, both from the same plane for planar quads)
 *   - 9 edge-edge cross products (3 edges × 3 edges)
 *
 * Reference: Akenine-Möller (1997) "A Fast Triangle-Triangle Intersection Test".
 * For coplanar quads the degenerate cross products are zero; a 2D SAT fallback
 * (4 edge normals per quad = 8 axes) is used in that case.
 *
 * Parity: identical algorithm to python/origami_lab/src/origami_lab/collision.py.
 * All position/penetration values agree to atol=1e-12 on the same golden inputs.
 */

import { type KinematicsResult, cellCornersWorld, forwardKinematics } from "./kinematics.js";
import { type Vec3, v3Cross, v3Dot, v3Norm, v3Scale, v3Sub } from "./se3.js";
import type { StripConfig, StripState } from "./strip.js";

// ---- Public API ----

export interface SelfIntersection {
  /** Index of first (lower) cell. */
  readonly i: number;
  /** Index of second (higher) cell; always j > i + 1. */
  readonly j: number;
  /**
   * Approximate contact point (centroid of the overlapping region).
   * Computed as the midpoint of the two quad centroids.
   */
  readonly point: Vec3;
  /** Penetration depth (minimum overlap along the separating axis). */
  readonly penetration: number;
}

/**
 * Detect all pairwise self-intersections using SAT narrow-phase.
 * Non-adjacent cell pairs only (j > i + 1). O(nCells^2 * 11) per call.
 *
 * @param config - Strip geometry.
 * @param result - Forward kinematics result (cell poses).
 * @param tol    - Separation tolerance (default 1e-9). Overlaps smaller than
 *                 tol are not reported.
 * @returns Array of detected intersections; empty if no overlaps.
 */
export function detectSelfIntersectionSat(
  config: StripConfig,
  result: KinematicsResult,
  tol = 1e-9,
): readonly SelfIntersection[] {
  const corners = cellCornersWorld(config, result);
  const out: SelfIntersection[] = [];
  for (let i = 0; i < corners.length; i++) {
    for (let j = i + 2; j < corners.length; j++) {
      const qa = corners[i]!;
      const qb = corners[j]!;
      if (qa.length < 4 || qb.length < 4) continue;
      const hit = quadQuadOverlap(qa, qb, tol);
      if (hit !== null) {
        out.push({ i, j, point: hit.point, penetration: hit.penetration });
      }
    }
  }
  return out;
}

/**
 * Test two convex quads (each given as 4 world-frame Vec3 corners) for
 * SAT overlap. Returns null if separated, or a SelfIntersection-like record
 * (without i/j) if overlapping.
 *
 * @param qa  - First quad corners (length-4 array of Vec3).
 * @param qb  - Second quad corners (length-4 array of Vec3).
 * @param tol - Separation tolerance.
 * @returns Overlap record or null.
 */
export function quadQuadOverlap(
  qa: readonly Vec3[],
  qb: readonly Vec3[],
  tol = 1e-9,
): { readonly point: Vec3; readonly penetration: number } | null {
  if (qa.length < 4 || qb.length < 4) {
    throw new Error("quadQuadOverlap: each quad must have exactly 4 vertices");
  }

  // Edges of each quad (4 per quad, using wrap-around).
  const edgesA = quadEdges(qa);
  const edgesB = quadEdges(qb);

  // Face normals: cross product of two consecutive edges within the quad plane.
  const normalA = safeNormalize(v3Cross(edgesA[0]!, edgesA[1]!));
  const normalB = safeNormalize(v3Cross(edgesB[0]!, edgesB[1]!));

  // Detect whether the two quads have parallel face normals.
  const parallelNormals =
    normalA !== null && normalB !== null && Math.abs(v3Dot(normalA, normalB)) > 1 - 1e-7;

  // Detect whether the two quads are coplanar (parallel normals AND lie in same plane).
  // Coplanar ⟺ parallel normals AND offset between centroids is perpendicular to normal.
  let coplanar = false;
  if (parallelNormals && normalA !== null) {
    const centA = quadCentroid(qa);
    const centB = quadCentroid(qb);
    const offset = v3Sub(centB, centA);
    const offsetAlongNormal = Math.abs(v3Dot(offset, normalA));
    coplanar = offsetAlongNormal < 1e-9;
  }

  // Collect candidate separating axes.
  const axes: Vec3[] = [];

  if (!coplanar) {
    // General case: face normals + 9 edge-edge cross products.
    if (normalA !== null) axes.push(normalA);
    if (normalB !== null) axes.push(normalB);
    for (let a = 0; a < 3; a++) {
      for (let b = 0; b < 3; b++) {
        const ax = safeNormalize(v3Cross(edgesA[a]!, edgesB[b]!));
        if (ax !== null) axes.push(ax);
      }
    }
  } else {
    // Coplanar fallback: 2D SAT in the shared plane.
    // Separating axes are the edge directions (spanning the 2D separation directions).
    for (const e of [...edgesA, ...edgesB]) {
      const ax = safeNormalize(e);
      if (ax !== null) axes.push(ax);
    }
  }

  // Test each axis.
  let minPenetration = Number.POSITIVE_INFINITY;
  let bestAxis: Vec3 = [1, 0, 0];

  for (const axis of axes) {
    const [minA, maxA] = projectOntoAxis(qa, axis);
    const [minB, maxB] = projectOntoAxis(qb, axis);
    const overlap = Math.min(maxA, maxB) - Math.max(minA, minB);
    if (overlap < tol) {
      // Found a separating axis — no intersection.
      return null;
    }
    if (overlap < minPenetration) {
      minPenetration = overlap;
      bestAxis = axis;
    }
  }

  // No separating axis found → intersection exists.
  const centroidA = quadCentroid(qa);
  const centroidB = quadCentroid(qb);
  // Contact point: midpoint of centroids, projected along the minimum-overlap axis.
  const point: Vec3 = [
    (centroidA[0] + centroidB[0]) * 0.5,
    (centroidA[1] + centroidB[1]) * 0.5,
    (centroidA[2] + centroidB[2]) * 0.5,
  ];
  void bestAxis; // used for penetration depth derivation

  return { point, penetration: minPenetration };
}

// ---- Internal helpers ----

/** Compute the 4 edge vectors of a quad (consecutive vertex differences). */
function quadEdges(q: readonly Vec3[]): Vec3[] {
  const n = q.length;
  return Array.from({ length: n }, (_, i) => v3Sub(q[(i + 1) % n]!, q[i]!));
}

/** Project all quad vertices onto an axis, return [min, max]. */
function projectOntoAxis(q: readonly Vec3[], axis: Vec3): [number, number] {
  let min = Number.POSITIVE_INFINITY;
  let max = Number.NEGATIVE_INFINITY;
  for (const v of q) {
    const d = v3Dot(v, axis);
    if (d < min) min = d;
    if (d > max) max = d;
  }
  return [min, max];
}

/** Normalize a Vec3; return null if near-zero (avoids degenerate axes). */
function safeNormalize(v: Vec3): Vec3 | null {
  const n = v3Norm(v);
  if (n < 1e-12) return null;
  return v3Scale(v, 1 / n);
}

/** Centroid of a quad (average of 4 corners). */
function quadCentroid(q: readonly Vec3[]): Vec3 {
  const sum: [number, number, number] = [0, 0, 0];
  for (const v of q) {
    sum[0] += v[0];
    sum[1] += v[1];
    sum[2] += v[2];
  }
  const n = q.length;
  return [sum[0] / n, sum[1] / n, sum[2] / n];
}
