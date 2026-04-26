/**
 * V_4 = Z_2 x Z_2 symmetry group acting on hinge state vectors of a 1D strip.
 *
 *   sigma : permutation that reverses hinge order   (geometric mirror)
 *   tau   : sign flip on every angle                 (paper-flip)
 *   sigmatau = sigma . tau                            (anti-symmetry)
 *
 * These are the natural symmetries of an open path graph P_N: full dihedral
 * groups appear only on closed (cyclic) graphs. Treating the strip with V_4
 * is what lets the coupling matrix decompose into low-dimensional irreducible
 * components; see MATH.md for the Schur-lemma derivation.
 */

export type GroupElement = "e" | "sigma" | "tau" | "sigmatau";

export const GROUP_ELEMENTS: readonly GroupElement[] = ["e", "sigma", "tau", "sigmatau"];

export interface SymmetryGroup {
  /** Number of hinges (state-vector dimension). */
  readonly nHinges: number;
  /** Permutation matrix for sigma (reverses hinge order). Stored as flat row-major n^2 array. */
  readonly sigmaPerm: readonly number[];
  /** Sign factor for tau acting on each hinge: tau = -I. */
  readonly tauSign: number;
}

export function kleinFourStrip(nHinges: number): SymmetryGroup {
  if (!Number.isInteger(nHinges) || nHinges < 1) {
    throw new Error(`kleinFourStrip: nHinges must be a positive integer`);
  }
  const P = new Array<number>(nHinges * nHinges).fill(0);
  for (let i = 0; i < nHinges; i++) {
    P[i * nHinges + (nHinges - 1 - i)] = 1;
  }
  return { nHinges, sigmaPerm: P, tauSign: -1 };
}

export function groupAction(
  G: SymmetryGroup,
  g: GroupElement,
  v: readonly number[],
): readonly number[] {
  if (v.length !== G.nHinges) {
    throw new Error(
      `groupAction: vector length ${v.length} mismatched with group dim ${G.nHinges}`,
    );
  }
  const reversed = (): number[] => {
    const out = new Array<number>(G.nHinges).fill(0);
    for (let i = 0; i < G.nHinges; i++) out[i] = v[G.nHinges - 1 - i] ?? 0;
    return out;
  };
  switch (g) {
    case "e":
      return [...v];
    case "sigma":
      return reversed();
    case "tau":
      return v.map((x) => -x);
    case "sigmatau":
      return reversed().map((x) => -x);
  }
}

export function groupActionMatrix(
  G: SymmetryGroup,
  g: GroupElement,
): readonly (readonly number[])[] {
  const n = G.nHinges;
  const M: number[][] = Array.from({ length: n }, () => new Array(n).fill(0));
  for (let i = 0; i < n; i++) {
    const e = new Array<number>(n).fill(0);
    e[i] = 1;
    const result = groupAction(G, g, e);
    for (let j = 0; j < n; j++) M[j]![i] = result[j] ?? 0;
  }
  return M;
}

/**
 * Reynolds operator: average of P_g M P_g^T over the group, projecting an
 * arbitrary nxn matrix to the G-equivariant subspace.
 *
 *   M_eq = (1 / |G|) sum_{g in G} P_g M P_g^{-1}
 *
 * For our V_4, each P_g is orthogonal so P_g^{-1} = P_g^T.
 */
export function reynoldsProject(
  G: SymmetryGroup,
  M: readonly (readonly number[])[],
): readonly (readonly number[])[] {
  const n = G.nHinges;
  if (M.length !== n) {
    throw new Error(`reynoldsProject: matrix size mismatch`);
  }
  const acc: number[][] = Array.from({ length: n }, () => new Array(n).fill(0));
  for (const g of GROUP_ELEMENTS) {
    const transformed = conjugate(G, g, M);
    for (let i = 0; i < n; i++) {
      for (let j = 0; j < n; j++) {
        acc[i]![j]! += (transformed[i]?.[j] ?? 0) / GROUP_ELEMENTS.length;
      }
    }
  }
  return acc;
}

function conjugate(
  G: SymmetryGroup,
  g: GroupElement,
  M: readonly (readonly number[])[],
): readonly (readonly number[])[] {
  const n = G.nHinges;
  const left = new Array<number[]>(n);
  for (let i = 0; i < n; i++) {
    const row = (M[i] ?? new Array(n).fill(0)).slice();
    left[i] = groupAction(G, g, row).slice();
  }
  // Now apply g to columns: equivalent to applying g to rows of transpose.
  const trans = transposeMatrix(left);
  for (let i = 0; i < trans.length; i++) {
    trans[i] = groupAction(G, g, trans[i]!).slice();
  }
  return transposeMatrix(trans);
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
 * Frobenius distance to the equivariant subspace, useful as an empirical test.
 */
export function equivarianceResidual(G: SymmetryGroup, M: readonly (readonly number[])[]): number {
  const proj = reynoldsProject(G, M);
  let acc = 0;
  for (let i = 0; i < G.nHinges; i++) {
    for (let j = 0; j < G.nHinges; j++) {
      const d = (M[i]?.[j] ?? 0) - (proj[i]?.[j] ?? 0);
      acc += d * d;
    }
  }
  return Math.sqrt(acc);
}
