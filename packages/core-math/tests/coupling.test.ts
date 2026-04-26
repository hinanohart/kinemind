import fc from "fast-check";
import { describe, expect, it } from "vitest";
import {
  applyCoupling,
  couplingEquivarianceResidual,
  effectiveRank,
  estimateCoupling,
  identityCoupling,
  mirrorCouplingMatrix,
  spectralRadius,
} from "../src/coupling.js";
import { kleinFourStrip } from "../src/symmetry.js";

const closeTo = (a: number, b: number, tol = 1e-7) => Math.abs(a - b) <= tol;

describe("identity coupling", () => {
  it("is the n x n identity", () => {
    const C = identityCoupling(7);
    for (let i = 0; i < 7; i++) {
      for (let j = 0; j < 7; j++) {
        expect(C.matrix[i]![j]).toBe(i === j ? 1 : 0);
      }
    }
  });

  it("preserves the intent vector", () => {
    const intent = [0.1, -0.2, 0.3, 0.4, -0.5, 0.6, -0.7];
    const out = applyCoupling(identityCoupling(7), intent);
    intent.forEach((v, i) => expect(closeTo(out[i]!, v)).toBe(true));
  });
});

describe("mirror coupling", () => {
  it("diagonal is 1, mirror entries are beta", () => {
    const beta = 0.6;
    const C = mirrorCouplingMatrix(7, beta);
    for (let i = 0; i < 7; i++) {
      expect(C.matrix[i]![i]).toBe(1);
      const j = 6 - i;
      if (j !== i) expect(C.matrix[i]![j]).toBeCloseTo(beta, 12);
    }
  });

  it("center hinge of odd-length strip is fixed", () => {
    const C = mirrorCouplingMatrix(7, 0.5);
    // With n=7 the central hinge is index 3; mirror of 3 is also 3, so the
    // off-diagonal entry is omitted by construction.
    expect(C.matrix[3]![3]).toBe(1);
    for (let j = 0; j < 7; j++) {
      if (j !== 3) expect(C.matrix[3]![j]).toBe(0);
    }
  });

  it("rejects beta outside [0, 1]", () => {
    expect(() => mirrorCouplingMatrix(7, -0.1)).toThrow();
    expect(() => mirrorCouplingMatrix(7, 1.1)).toThrow();
  });

  it("is V_4 equivariant", () => {
    const G = kleinFourStrip(7);
    fc.assert(
      fc.property(fc.double({ min: 0, max: 1, noNaN: true }), (beta) => {
        const C = mirrorCouplingMatrix(7, beta);
        return couplingEquivarianceResidual(C, G) < 1e-9;
      }),
      { numRuns: 30 },
    );
  });

  it("spectral radius equals 1 + beta", () => {
    const beta = 0.5;
    const C = mirrorCouplingMatrix(8, beta);
    expect(closeTo(spectralRadius(C.matrix), 1 + beta, 1e-6)).toBe(true);
  });
});

describe("estimateCoupling", () => {
  it("recovers identity from clean data", () => {
    const intents: number[][] = [];
    const responses: number[][] = [];
    for (let i = 0; i < 7; i++) {
      const e = new Array<number>(7).fill(0);
      e[i] = 1;
      intents.push(e);
      responses.push(e);
    }
    const C = estimateCoupling(intents, responses, { nHinges: 7 });
    for (let i = 0; i < 7; i++) {
      for (let j = 0; j < 7; j++) {
        expect(closeTo(C.matrix[i]![j]!, i === j ? 1 : 0, 1e-9)).toBe(true);
      }
    }
  });

  it("recovers mirror coupling from synthetic mental responses", () => {
    const beta = 0.4;
    const truth = mirrorCouplingMatrix(7, beta);
    const intents: number[][] = [];
    const responses: number[][] = [];
    for (let i = 0; i < 7; i++) {
      const e = new Array<number>(7).fill(0);
      e[i] = 1;
      intents.push(e);
      responses.push([...applyCoupling(truth, e)]);
    }
    const C = estimateCoupling(intents, responses, { nHinges: 7 });
    for (let i = 0; i < 7; i++) {
      for (let j = 0; j < 7; j++) {
        const expected = truth.matrix[i]?.[j] ?? 0;
        expect(closeTo(C.matrix[i]![j]!, expected, 1e-7)).toBe(true);
      }
    }
  });

  it("equivariance projection cancels noise antisymmetric to V_4", () => {
    const beta = 0.5;
    const truth = mirrorCouplingMatrix(7, beta);
    const G = kleinFourStrip(7);
    // Inject asymmetric noise then estimate with group constraint.
    const intents: number[][] = [];
    const responses: number[][] = [];
    const noise = (i: number, j: number) => 0.05 * Math.sin(7 * i + 3 * j);
    for (let i = 0; i < 7; i++) {
      const e = new Array<number>(7).fill(0);
      e[i] = 1;
      intents.push(e);
      const r = [...applyCoupling(truth, e)];
      for (let j = 0; j < 7; j++) {
        r[j] = (r[j] ?? 0) + noise(i, j);
      }
      responses.push(r);
    }
    const Craw = estimateCoupling(intents, responses, { nHinges: 7 });
    const Ceq = estimateCoupling(intents, responses, { nHinges: 7, group: G });
    expect(couplingEquivarianceResidual(Ceq, G)).toBeLessThan(1e-9);
    expect(couplingEquivarianceResidual(Craw, G)).toBeGreaterThan(0);
  });

  it("Tikhonov regularisation tames degenerate intent matrices", () => {
    // All-zero intents -> XtX is zero and singular.
    const intents = [[0, 0, 0]];
    const responses = [[1, 0, 0]];
    expect(() => estimateCoupling(intents, responses, { nHinges: 3 })).toThrow();
    expect(() => estimateCoupling(intents, responses, { nHinges: 3, lambda: 1e-3 })).not.toThrow();
  });
});

describe("rank and spectrum", () => {
  it("identity has effective rank n", () => {
    const C = identityCoupling(8);
    expect(effectiveRank(C.matrix)).toBe(8);
  });

  it("mirror coupling has full rank for 0 < beta < 1", () => {
    const C = mirrorCouplingMatrix(8, 0.5);
    expect(effectiveRank(C.matrix)).toBe(8);
  });

  it("zero coupling has rank 0", () => {
    const Z = Array.from({ length: 5 }, () => new Array<number>(5).fill(0));
    expect(effectiveRank(Z)).toBe(0);
  });
});
