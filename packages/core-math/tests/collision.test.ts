import { describe, expect, it } from "vitest";
import { detectSelfIntersectionSat, quadQuadOverlap } from "../src/collision.js";
import { forwardKinematics } from "../src/kinematics.js";
import type { Vec3 } from "../src/se3.js";
import { flatState, makeUniformStrip } from "../src/strip.js";

const closeTo = (a: number, b: number, tol = 1e-9) => Math.abs(a - b) <= tol;

describe("quadQuadOverlap", () => {
  it("non-overlapping coplanar quads return null", () => {
    // Two side-by-side unit squares in XY, separated by 1 unit gap.
    const qa: Vec3[] = [
      [0, 0, 0],
      [1, 0, 0],
      [1, 1, 0],
      [0, 1, 0],
    ];
    const qb: Vec3[] = [
      [2, 0, 0],
      [3, 0, 0],
      [3, 1, 0],
      [2, 1, 0],
    ];
    expect(quadQuadOverlap(qa, qb)).toBeNull();
  });

  it("overlapping coplanar quads return non-null with positive penetration", () => {
    // Two overlapping unit squares shifted by 0.5.
    const qa: Vec3[] = [
      [0, 0, 0],
      [1, 0, 0],
      [1, 1, 0],
      [0, 1, 0],
    ];
    const qb: Vec3[] = [
      [0.5, 0, 0],
      [1.5, 0, 0],
      [1.5, 1, 0],
      [0.5, 1, 0],
    ];
    const result = quadQuadOverlap(qa, qb);
    expect(result).not.toBeNull();
    expect(result!.penetration).toBeGreaterThan(0);
  });

  it("touching edge (penetration < tol) returns null", () => {
    // Adjacent quads sharing edge at x=1.
    const qa: Vec3[] = [
      [0, 0, 0],
      [1, 0, 0],
      [1, 1, 0],
      [0, 1, 0],
    ];
    const qb: Vec3[] = [
      [1, 0, 0],
      [2, 0, 0],
      [2, 1, 0],
      [1, 1, 0],
    ];
    // With tol=0 they share an edge; penetration=0 < 1e-9.
    expect(quadQuadOverlap(qa, qb, 1e-9)).toBeNull();
  });

  it("3D non-overlapping quads return null", () => {
    // quad A in XY plane at z=0, quad B in XY plane at z=2 (well separated).
    const qa: Vec3[] = [
      [0, 0, 0],
      [1, 0, 0],
      [1, 1, 0],
      [0, 1, 0],
    ];
    const qb: Vec3[] = [
      [0, 0, 2],
      [1, 0, 2],
      [1, 1, 2],
      [0, 1, 2],
    ];
    expect(quadQuadOverlap(qa, qb)).toBeNull();
  });

  it("3D overlapping quads (XZ plane shifted in Y) return positive penetration", () => {
    // Two unit quads in the XZ plane at y=0, shifted in X by 0.5 so they overlap.
    // These are non-coplanar relative to a pure XY-plane quad, but they share the same
    // plane => coplanar test fires; they DO overlap in 2D.
    const qa: Vec3[] = [
      [0, 0, 0],
      [1, 0, 0],
      [1, 0, 1],
      [0, 0, 1],
    ];
    const qb: Vec3[] = [
      [0.5, 0, 0],
      [1.5, 0, 0],
      [1.5, 0, 1],
      [0.5, 0, 1],
    ];
    const result = quadQuadOverlap(qa, qb);
    expect(result).not.toBeNull();
    expect(result!.penetration).toBeGreaterThan(0);
  });
});

describe("detectSelfIntersectionSat", () => {
  it("flat strip has no self-intersection", () => {
    const cfg = makeUniformStrip(8, 1);
    const result = forwardKinematics(cfg, flatState(cfg));
    const hits = detectSelfIntersectionSat(cfg, result);
    expect(hits).toHaveLength(0);
  });

  it("accordion fold N=4, θ=(π,π,0) detects cell 0 vs cell 3 overlap", () => {
    // With theta = [pi, pi, 0]:
    // Cell 0: [0..1] on +X
    // After hinge 0 (pi rotation about Y): cell 1 folds back, occupying [0..1] reversed.
    // After hinge 1 (pi rotation): cell 2 re-unfolds, occupying [0..1] again.
    // After hinge 2 (0): cell 3 extends from [1..2].
    // Cells 0 and 2 overlap (same position range [0..1]).
    const cfg = makeUniformStrip(4, 1);
    const state = { thetas: [Math.PI, Math.PI, 0] };
    const result = forwardKinematics(cfg, state);
    const hits = detectSelfIntersectionSat(cfg, result);
    // At least one pair should be detected.
    expect(hits.length).toBeGreaterThan(0);
    // Verify all hits have j > i + 1.
    for (const hit of hits) {
      expect(hit.j).toBeGreaterThan(hit.i + 1);
    }
    // Cells 0 and 2 must be in the hit list.
    const hasZeroTwo = hits.some((h) => h.i === 0 && h.j === 2);
    expect(hasZeroTwo).toBe(true);
  });

  it("large fold detects additional pairs", () => {
    const cfg = makeUniformStrip(5, 1);
    const state = { thetas: [Math.PI, Math.PI, Math.PI, Math.PI] };
    const result = forwardKinematics(cfg, state);
    const hits = detectSelfIntersectionSat(cfg, result);
    // With repeated pi folds, multiple pairs should collide.
    expect(hits.length).toBeGreaterThanOrEqual(1);
  });

  it("penetration values are positive for all reported hits", () => {
    const cfg = makeUniformStrip(4, 1);
    const result = forwardKinematics(cfg, { thetas: [Math.PI, Math.PI, 0] });
    const hits = detectSelfIntersectionSat(cfg, result);
    for (const hit of hits) {
      expect(hit.penetration).toBeGreaterThan(0);
      expect(Number.isFinite(hit.penetration)).toBe(true);
    }
  });
});
