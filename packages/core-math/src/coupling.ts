/**
 * Mental coupling matrix C: the linear operator that maps a participant's
 * intended hinge angle vector to the hinge configuration they actually
 * picture. Diagonal entries encode self-fidelity (always 1 in the linear
 * regime); off-diagonal entries encode involuntary co-activation.
 *
 * The Kinematic Mental Mirroring (KMM) hypothesis predicts that C is
 * V_4-equivariant: reflecting the strip leaves C unchanged, and so does a
 * paper-flip. By Schur's lemma C then lives in a 4-dimensional parameter
 * family for the V_4 representation that arises on R^{N-1}; the simplest
 * non-trivial point in that family is the mirror coupling matrix below.
 *
 * Linear-algebra primitives are kept dependency-free: small matrix sizes
 * (n <= 50 hinges in v0.1) make a tight, audited implementation faster
 * than dispatching to a black-box numerical library.
 */

import {
  type GroupElement,
  GROUP_ELEMENTS,
  groupAction,
  reynoldsProject,
  type SymmetryGroup,
  equivarianceResidual,
} from "./symmetry.js";

export type Matrix = readonly (readonly number[])[];

export interface MentalCoupling {
  /** N x N coupling matrix where N is the hinge count. */
  readonly matrix: Matrix;
  readonly nHinges: number;
  /** Group used to constrain estimation; undefined if no symmetry was imposed. */
  readonly group?: SymmetryGroup;
  /** Provenance: closed form vs estimated from data. */
  readonly source: "analytic" | "empirical";
  /** Strength parameter beta in [0, 1] when source="analytic". */
  readonly beta?: number;
}

/**
 * Identity coupling: each hinge moves only itself. The null hypothesis
 * baseline against which empirical couplings are compared.
 */
export function identityCoupling(nHinges: number): MentalCoupling {
  if (!Number.isInteger(nHinges) || nHinges < 1) {
    throw new Error("identityCoupling: nHinges must be a positive integer");
  }
  const M: number[][] = Array.from({ length: nHinges }, (_, i) =>
    Array.from({ length: nHinges }, (_, j) => (i === j ? 1 : 0)),
  );
  return { matrix: M, nHinges, source: "analytic", beta: 0 };
}

/**
 * Mirror coupling matrix C(beta):
 *   C[i][i]      = 1
 *   C[i][n-1-i]  = beta if i != n-1-i
 *   else         = 0
 *
 * Eigenvalues:  {1+beta} (multiplicity floor(n/2)),
 *               {1-beta} (multiplicity floor(n/2)),
 *               {1}       (only when n is odd; central hinge is fixed by sigma).
 *
 * For beta in [0, 1] the matrix is contracting (all eigenvalues in [1-beta, 1+beta] >= 0)
 * and V_4-equivariant by construction.
 */
export function mirrorCouplingMatrix(
  nHinges: number,
  beta: number,
): MentalCoupling {
  if (!Number.isInteger(nHinges) || nHinges < 1) {
    throw new Error("mirrorCouplingMatrix: nHinges must be a positive integer");
  }
  if (!(beta >= 0) || !(beta <= 1)) {
    throw new Error(`mirrorCouplingMatrix: beta must be in [0, 1] (got ${beta})`);
  }
  const M: number[][] = Array.from({ length: nHinges }, () =>
    new Array<number>(nHinges).fill(0),
  );
  for (let i = 0; i < nHinges; i++) {
    M[i]![i] = 1;
    const j = nHinges - 1 - i;
    if (j !== i) {
      M[i]![j] = beta;
    }
  }
  return {
    matrix: M,
    nHinges,
    source: "analytic",
    beta,
  };
}

/**
 * Apply a coupling matrix to an intent vector: theta_mental = C theta_intent.
 * Output is clipped to [-angleMax, angleMax] when angleMax is provided.
 */
export function applyCoupling(
  coupling: MentalCoupling,
  thetaIntent: readonly number[],
  angleMax?: number,
): readonly number[] {
  const n = coupling.nHinges;
  if (thetaIntent.length !== n) {
    throw new Error(
      `applyCoupling: intent length ${thetaIntent.length} mismatched with coupling dim ${n}`,
    );
  }
  const out = new Array<number>(n).fill(0);
  for (let i = 0; i < n; i++) {
    let acc = 0;
    const row = coupling.matrix[i] ?? [];
    for (let j = 0; j < n; j++) {
      acc += (row[j] ?? 0) * (thetaIntent[j] ?? 0);
    }
    out[i] = angleMax === undefined ? acc : Math.max(-angleMax, Math.min(angleMax, acc));
  }
  return out;
}

/**
 * Estimate a coupling matrix from a stack of (intent, response) pairs by
 * ordinary least squares with optional Tikhonov regularisation:
 *
 *     C_hat = (X^T X + lambda I)^{-1} X^T Y .
 *
 * If a SymmetryGroup is supplied, the estimate is post-projected onto the
 * G-equivariant subspace via the Reynolds operator (Section 3.5 of MATH.md).
 *
 * Solver: Gauss-Jordan elimination on the small (n_hinges x n_hinges) Gram
 * matrix. n_hinges <= 50 keeps this comfortably under a millisecond.
 */
export function estimateCoupling(
  intents: readonly (readonly number[])[],
  responses: readonly (readonly number[])[],
  options: {
    nHinges: number;
    lambda?: number;
    group?: SymmetryGroup;
  },
): MentalCoupling {
  const { nHinges, lambda = 0, group } = options;
  if (intents.length !== responses.length) {
    throw new Error("estimateCoupling: intent and response counts disagree");
  }
  if (intents.length === 0) {
    throw new Error("estimateCoupling: at least one trial is required");
  }
  const K = intents.length;
  for (let k = 0; k < K; k++) {
    if ((intents[k]?.length ?? 0) !== nHinges) {
      throw new Error(`estimateCoupling: intents[${k}] has wrong length`);
    }
    if ((responses[k]?.length ?? 0) !== nHinges) {
      throw new Error(`estimateCoupling: responses[${k}] has wrong length`);
    }
  }

  // Build X^T X (nHinges x nHinges) and X^T Y (nHinges x nHinges).
  const xtx: number[][] = Array.from({ length: nHinges }, () =>
    new Array<number>(nHinges).fill(0),
  );
  const xty: number[][] = Array.from({ length: nHinges }, () =>
    new Array<number>(nHinges).fill(0),
  );
  for (let k = 0; k < K; k++) {
    const x = intents[k]!;
    const y = responses[k]!;
    for (let i = 0; i < nHinges; i++) {
      for (let j = 0; j < nHinges; j++) {
        xtx[i]![j]! += (x[i] ?? 0) * (x[j] ?? 0);
        xty[i]![j]! += (x[i] ?? 0) * (y[j] ?? 0);
      }
    }
  }
  if (lambda > 0) {
    for (let i = 0; i < nHinges; i++) xtx[i]![i]! += lambda;
  }

  // Solve xtx * B = xty for B.
  const B = solveLinearSystem(xtx, xty);
  // C such that response = C intent => Y = X C^T => B = (X^T X)^{-1} X^T Y = C^T.
  // Therefore C = B^T.
  let C: number[][] = transposeMatrix(B);
  if (group) {
    C = reynoldsProject(group, C).map((r) => [...r]);
  }
  return {
    matrix: C,
    nHinges,
    source: "empirical",
    group,
  };
}

/**
 * Frobenius norm of (M . expected_invariance - expected_invariance . M).
 * Returns 0 (within epsilon) when M is exactly G-equivariant.
 */
export function couplingEquivarianceResidual(
  coupling: MentalCoupling,
  group: SymmetryGroup,
): number {
  return equivarianceResidual(group, coupling.matrix);
}

/**
 * Power-method spectral radius (largest |eigenvalue|). For symmetric or
 * near-symmetric coupling matrices this converges quickly; we cap iterations
 * to keep the call cheap for UI use.
 */
export function spectralRadius(
  M: Matrix,
  options: { maxIter?: number; tol?: number } = {},
): number {
  const { maxIter = 200, tol = 1e-10 } = options;
  const n = M.length;
  if (n === 0) return 0;
  let v: number[] = new Array(n).fill(1);
  v[0] = 1;
  let lambda = 0;
  for (let iter = 0; iter < maxIter; iter++) {
    const Mv = new Array<number>(n).fill(0);
    for (let i = 0; i < n; i++) {
      for (let j = 0; j < n; j++) {
        Mv[i]! += (M[i]?.[j] ?? 0) * (v[j] ?? 0);
      }
    }
    const norm = Math.hypot(...Mv);
    if (norm < 1e-300) return 0;
    const next = Mv.map((x) => x / norm);
    let delta = 0;
    for (let i = 0; i < n; i++) {
      const d = (next[i] ?? 0) - (v[i] ?? 0);
      delta += d * d;
    }
    v = next;
    const lambdaNext = norm;
    if (Math.abs(lambdaNext - lambda) < tol && Math.sqrt(delta) < tol) {
      return lambdaNext;
    }
    lambda = lambdaNext;
  }
  return lambda;
}

/**
 * Effective rank: number of singular values exceeding threshold * sigma_max.
 * Implemented via Jacobi eigendecomposition of M M^T (sufficient for n <= 50).
 */
export function effectiveRank(M: Matrix, threshold = 1e-6): number {
  const n = M.length;
  if (n === 0) return 0;
  const MMT: number[][] = Array.from({ length: n }, () =>
    new Array<number>(n).fill(0),
  );
  for (let i = 0; i < n; i++) {
    for (let j = 0; j < n; j++) {
      let acc = 0;
      for (let k = 0; k < n; k++) {
        acc += (M[i]?.[k] ?? 0) * (M[j]?.[k] ?? 0);
      }
      MMT[i]![j] = acc;
    }
  }
  const eig = jacobiEigenvalues(MMT);
  const sigmas = eig.map((e) => Math.sqrt(Math.max(0, e))).sort((a, b) => b - a);
  const sigmaMax = sigmas[0] ?? 0;
  if (sigmaMax === 0) return 0;
  return sigmas.filter((s) => s > threshold * sigmaMax).length;
}

// ---- internal linear algebra ----

function solveLinearSystem(A: number[][], B: number[][]): number[][] {
  // Solve A X = B for X. A is n x n, B is n x m. Gauss-Jordan on augmented.
  const n = A.length;
  const m = B[0]?.length ?? 0;
  const aug: number[][] = Array.from({ length: n }, (_, i) =>
    [...(A[i] ?? new Array(n).fill(0)), ...(B[i] ?? new Array(m).fill(0))],
  );

  for (let col = 0; col < n; col++) {
    let pivotRow = col;
    let pivotMag = Math.abs(aug[col]?.[col] ?? 0);
    for (let r = col + 1; r < n; r++) {
      const mag = Math.abs(aug[r]?.[col] ?? 0);
      if (mag > pivotMag) {
        pivotMag = mag;
        pivotRow = r;
      }
    }
    if (pivotMag < 1e-12) {
      throw new Error("solveLinearSystem: singular matrix");
    }
    if (pivotRow !== col) {
      const tmp = aug[col]!;
      aug[col] = aug[pivotRow]!;
      aug[pivotRow] = tmp;
    }
    const pivot = aug[col]![col]!;
    for (let j = 0; j < n + m; j++) aug[col]![j]! /= pivot;
    for (let r = 0; r < n; r++) {
      if (r === col) continue;
      const factor = aug[r]![col]!;
      if (factor === 0) continue;
      for (let j = 0; j < n + m; j++) {
        aug[r]![j]! -= factor * aug[col]![j]!;
      }
    }
  }

  const X: number[][] = Array.from({ length: n }, (_, i) =>
    Array.from({ length: m }, (_, j) => aug[i]?.[n + j] ?? 0),
  );
  return X;
}

function transposeMatrix(M: number[][]): number[][] {
  const r = M.length;
  const c = M[0]?.length ?? 0;
  const out: number[][] = Array.from({ length: c }, () => new Array(r).fill(0));
  for (let i = 0; i < r; i++) {
    for (let j = 0; j < c; j++) {
      out[j]![i] = M[i]?.[j] ?? 0;
    }
  }
  return out;
}

/**
 * Symmetric Jacobi eigenvalue solver. Converges quadratically near a
 * diagonal matrix; for our small (<=50) symmetric inputs it's a one-line
 * dependency-free option.
 */
function jacobiEigenvalues(
  Sin: readonly (readonly number[])[],
  maxIter = 200,
  tol = 1e-12,
): number[] {
  const n = Sin.length;
  const S: number[][] = Sin.map((row) => [...row]);
  for (let iter = 0; iter < maxIter; iter++) {
    let maxOff = 0;
    let p = 0;
    let q = 1;
    for (let i = 0; i < n; i++) {
      for (let j = i + 1; j < n; j++) {
        const v = Math.abs(S[i]?.[j] ?? 0);
        if (v > maxOff) {
          maxOff = v;
          p = i;
          q = j;
        }
      }
    }
    if (maxOff < tol) break;
    const Spp = S[p]?.[p] ?? 0;
    const Sqq = S[q]?.[q] ?? 0;
    const Spq = S[p]?.[q] ?? 0;
    const theta = (Sqq - Spp) / (2 * Spq || 1e-300);
    const t = Math.sign(theta) / (Math.abs(theta) + Math.sqrt(theta * theta + 1));
    const c = 1 / Math.sqrt(1 + t * t);
    const s = t * c;
    for (let i = 0; i < n; i++) {
      const Sip = S[i]?.[p] ?? 0;
      const Siq = S[i]?.[q] ?? 0;
      S[i]![p] = c * Sip - s * Siq;
      S[i]![q] = s * Sip + c * Siq;
    }
    for (let j = 0; j < n; j++) {
      const Spj = S[p]?.[j] ?? 0;
      const Sqj = S[q]?.[j] ?? 0;
      S[p]![j] = c * Spj - s * Sqj;
      S[q]![j] = s * Spj + c * Sqj;
    }
  }
  return Array.from({ length: n }, (_, i) => S[i]?.[i] ?? 0);
}

// Re-export for users who want to inspect the underlying group.
export { GROUP_ELEMENTS };
export type { GroupElement };
