import { describe, expect, it } from "vitest";
import fc from "fast-check";
import {
  cellCornersWorld,
  detectSelfIntersectionAabb,
  forwardKinematics,
} from "../src/kinematics.js";
import {
  flatState,
  flipState,
  makeStrip,
  makeUniformStrip,
  reflectState,
} from "../src/strip.js";

const closeTo = (a: number, b: number, tol = 1e-9) => Math.abs(a - b) <= tol;
const vecClose = (a: readonly number[], b: readonly number[], tol = 1e-9) =>
  a.length === b.length && a.every((x, i) => closeTo(x, b[i] ?? Number.NaN, tol));

describe("strip configuration", () => {
  it("rejects nCells < 2", () => {
    expect(() => makeUniformStrip(1)).toThrow();
    expect(() => makeUniformStrip(0)).toThrow();
  });

  it("flat state has nCells - 1 zero entries", () => {
    const cfg = makeUniformStrip(8);
    const s = flatState(cfg);
    expect(s.thetas).toHaveLength(7);
    expect(s.thetas.every((t) => t === 0)).toBe(true);
  });

  it("reflectState reverses hinges", () => {
    const s = { thetas: [0.1, 0.2, 0.3, 0.4] };
    expect(reflectState(s).thetas).toEqual([0.4, 0.3, 0.2, 0.1]);
  });

  it("flipState negates", () => {
    const s = { thetas: [0.1, -0.2, 0.3, -0.4] };
    expect(flipState(s).thetas).toEqual([-0.1, 0.2, -0.3, 0.4]);
  });

  it("rejects non-positive cell lengths", () => {
    expect(() => makeStrip([1, 0, 1])).toThrow();
    expect(() => makeStrip([1, -1, 1])).toThrow();
  });
});

describe("forward kinematics", () => {
  it("flat strip lays cells along +X", () => {
    const cfg = makeUniformStrip(8, 1);
    const result = forwardKinematics(cfg, flatState(cfg));
    expect(result.cells).toHaveLength(8);
    for (let i = 0; i < 8; i++) {
      const cell = result.cells[i]!;
      expect(vecClose(cell.position, [i, 0, 0])).toBe(true);
    }
  });

  it("centroids equal cell midpoints when flat", () => {
    const cfg = makeUniformStrip(4, 2);
    const result = forwardKinematics(cfg, flatState(cfg));
    for (let i = 0; i < 4; i++) {
      const c = result.centroids[i]!;
      expect(vecClose(c, [i * 2 + 1, 0, 0])).toBe(true);
    }
  });

  it("hinge of pi at first joint produces accordion fold (cell 1 above cell 0)", () => {
    const cfg = makeUniformStrip(2, 1);
    const result = forwardKinematics(cfg, { thetas: [Math.PI] });
    // Cell 1's leading edge is at translate(1) then rotate pi about Y, applied to (0,0,0)
    // = rotate(pi, Y) * (0,0,0) + (1,0,0) = (1,0,0). So cell 1 origin is still at x=1
    // but the cell extends back along -X (z stays 0 for pi rotation about Y).
    expect(result.cells[1]).toBeDefined();
    expect(vecClose(result.cells[1]!.position, [1, 0, 0], 1e-9)).toBe(true);
    // Cell 1 centroid is at (1,0,0) + R*(0.5,0,0) = (1 + cos(pi)*0.5, 0, sin(pi)*0.5) = (0.5, 0, 0).
    expect(vecClose(result.centroids[1]!, [0.5, 0, 0], 1e-9)).toBe(true);
  });

  it("alternating angles fold into accordion shape", () => {
    const cfg = makeUniformStrip(4, 1);
    const half = Math.PI / 2;
    const state = { thetas: [half, -half, half] };
    const result = forwardKinematics(cfg, state);
    expect(result.cells).toHaveLength(4);
    // Verify invariants: no NaN, all finite.
    for (const cell of result.cells) {
      expect(cell.position.every((x) => Number.isFinite(x))).toBe(true);
    }
  });

  it("zero-angle round-trip is exact", () => {
    fc.assert(
      fc.property(fc.integer({ min: 2, max: 30 }), (n) => {
        const cfg = makeUniformStrip(n);
        const result = forwardKinematics(cfg, flatState(cfg));
        return result.cells.every((cell, i) =>
          vecClose(cell.position, [i, 0, 0]),
        );
      }),
      { numRuns: 30 },
    );
  });

  it("throws when angle vector length disagrees with config", () => {
    const cfg = makeUniformStrip(8);
    expect(() =>
      forwardKinematics(cfg, { thetas: [0, 0, 0] }),
    ).toThrow(/expected 7/);
  });
});

describe("cell corners and AABB", () => {
  it("cell 0 corners form unit square at origin when flat", () => {
    const cfg = makeUniformStrip(2, 1);
    const result = forwardKinematics(cfg, flatState(cfg));
    const corners = cellCornersWorld(cfg, result);
    expect(corners[0]).toHaveLength(4);
    const expected = [
      [0, -0.5, 0],
      [1, -0.5, 0],
      [1, 0.5, 0],
      [0, 0.5, 0],
    ];
    for (let i = 0; i < 4; i++) {
      expect(vecClose(corners[0]![i]!, expected[i]!)).toBe(true);
    }
  });
});

describe("self-intersection detection", () => {
  it("flat strip has no self-intersection", () => {
    const cfg = makeUniformStrip(8, 1);
    const result = forwardKinematics(cfg, flatState(cfg));
    expect(detectSelfIntersectionAabb(cfg, result)).toBeNull();
  });

  it("tightly folded strip flags overlap (broad-phase AABB)", () => {
    const cfg = makeUniformStrip(4, 1);
    // Fold first hinge fully back; cells 0 and 1 now stack.
    // Cells 1 & 2 are joined, but 0 vs 2 should not overlap because cell 2
    // sits behind cell 1. To guarantee a non-trivial overlap we add a second
    // big fold so cell 2 lands back over cell 0.
    const result = forwardKinematics(cfg, {
      thetas: [Math.PI, Math.PI, 0],
    });
    const intersection = detectSelfIntersectionAabb(cfg, result);
    expect(intersection).not.toBeNull();
  });
});
