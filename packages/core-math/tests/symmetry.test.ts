import { describe, expect, it } from "vitest";
import {
  GROUP_ELEMENTS,
  equivarianceResidual,
  groupAction,
  groupActionMatrix,
  kleinFourStrip,
  reynoldsProject,
} from "../src/symmetry.js";

describe("V_4 group on hinge vectors", () => {
  it("e is identity, sigma reverses, tau negates", () => {
    const G = kleinFourStrip(4);
    const v = [1, 2, 3, 4];
    expect(groupAction(G, "e", v)).toEqual(v);
    expect(groupAction(G, "sigma", v)).toEqual([4, 3, 2, 1]);
    expect(groupAction(G, "tau", v)).toEqual([-1, -2, -3, -4]);
    expect(groupAction(G, "sigmatau", v)).toEqual([-4, -3, -2, -1]);
  });

  it("group is closed under composition", () => {
    const G = kleinFourStrip(5);
    const v = [1, 2, 3, 4, 5];
    for (const g1 of GROUP_ELEMENTS) {
      for (const g2 of GROUP_ELEMENTS) {
        const composed = groupAction(G, g1, groupAction(G, g2, v));
        // Result must equal one of the four orbit elements.
        const matchesAny = GROUP_ELEMENTS.some((g3) =>
          composed.every((x, i) => x === groupAction(G, g3, v)[i]),
        );
        expect(matchesAny).toBe(true);
      }
    }
  });

  it("action matrices have determinant ±1", () => {
    const G = kleinFourStrip(4);
    for (const g of GROUP_ELEMENTS) {
      const M = groupActionMatrix(G, g);
      // 4x4 determinant via cofactor expansion (small enough).
      const det = det4(
        M.map((r) => [...r]) as [
          number[],
          number[],
          number[],
          number[],
        ],
      );
      expect(Math.abs(Math.abs(det) - 1)).toBeLessThan(1e-9);
    }
  });
});

describe("Reynolds projection", () => {
  it("is idempotent", () => {
    const G = kleinFourStrip(4);
    const M = [
      [1, 2, 3, 4],
      [5, 6, 7, 8],
      [9, 10, 11, 12],
      [13, 14, 15, 16],
    ];
    const P1 = reynoldsProject(G, M);
    const P2 = reynoldsProject(
      G,
      P1.map((r) => [...r]),
    );
    for (let i = 0; i < 4; i++) {
      for (let j = 0; j < 4; j++) {
        expect(Math.abs((P1[i]?.[j] ?? 0) - (P2[i]?.[j] ?? 0))).toBeLessThan(1e-12);
      }
    }
  });

  it("equivariance residual is zero on projected matrix", () => {
    const G = kleinFourStrip(5);
    const M = [
      [3, 1, 4, 1, 5],
      [9, 2, 6, 5, 3],
      [5, 8, 9, 7, 9],
      [3, 2, 3, 8, 4],
      [6, 2, 6, 4, 3],
    ];
    const P = reynoldsProject(G, M);
    const Pcopy = P.map((r) => [...r]);
    expect(equivarianceResidual(G, Pcopy)).toBeLessThan(1e-9);
  });
});

function det4(M: [number[], number[], number[], number[]]): number {
  // Laplace expansion along the first row.
  let acc = 0;
  for (let c = 0; c < 4; c++) {
    const minor: number[][] = [];
    for (let r = 1; r < 4; r++) {
      const row: number[] = [];
      for (let cc = 0; cc < 4; cc++) {
        if (cc !== c) row.push(M[r]![cc]!);
      }
      minor.push(row);
    }
    const sign = c % 2 === 0 ? 1 : -1;
    acc += sign * (M[0]![c] ?? 0) * det3(minor);
  }
  return acc;
}

function det3(M: number[][]): number {
  return (
    (M[0]?.[0] ?? 0) *
      ((M[1]?.[1] ?? 0) * (M[2]?.[2] ?? 0) - (M[1]?.[2] ?? 0) * (M[2]?.[1] ?? 0)) -
    (M[0]?.[1] ?? 0) *
      ((M[1]?.[0] ?? 0) * (M[2]?.[2] ?? 0) - (M[1]?.[2] ?? 0) * (M[2]?.[0] ?? 0)) +
    (M[0]?.[2] ?? 0) *
      ((M[1]?.[0] ?? 0) * (M[2]?.[1] ?? 0) - (M[1]?.[1] ?? 0) * (M[2]?.[0] ?? 0))
  );
}
