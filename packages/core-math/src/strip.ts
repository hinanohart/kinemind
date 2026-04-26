/**
 * 1D origami strip: a path graph P_N of square cells linked by N-1 hinges.
 *
 * The strip lives in its own local frame; cell 0 is anchored at the origin,
 * its plane coincident with the world XY plane. Hinge axes are the shared
 * edges between adjacent cells (running along the local Y axis).
 */

import type { Vec3 } from "./se3.js";

export interface StripConfig {
  /** Number of cells (>= 2). */
  readonly nCells: number;
  /** Per-cell edge length along the chain (defaults to uniform 1). */
  readonly cellLengths: readonly number[];
  /** Hard limit on |theta_i|; physical paper saturates well before pi. */
  readonly angleMax: number;
}

export interface StripState {
  /** Hinge angles, length = nCells - 1; positive = mountain, negative = valley. */
  readonly thetas: readonly number[];
}

/**
 * Build a uniform StripConfig with nCells of length L and angle limit angleMax.
 * Throws when nCells < 2 or non-finite parameters appear.
 */
export function makeUniformStrip(
  nCells: number,
  cellLength = 1,
  angleMax = Math.PI,
): StripConfig {
  if (!Number.isInteger(nCells) || nCells < 2) {
    throw new Error(`makeUniformStrip: nCells must be an integer >= 2 (got ${nCells})`);
  }
  if (!(cellLength > 0) || !Number.isFinite(cellLength)) {
    throw new Error(`makeUniformStrip: cellLength must be positive (got ${cellLength})`);
  }
  if (!(angleMax > 0) || angleMax > Math.PI) {
    throw new Error(`makeUniformStrip: angleMax must be in (0, π] (got ${angleMax})`);
  }
  return {
    nCells,
    cellLengths: Array.from({ length: nCells }, () => cellLength),
    angleMax,
  };
}

export function makeStrip(
  cellLengths: readonly number[],
  angleMax = Math.PI,
): StripConfig {
  if (cellLengths.length < 2) {
    throw new Error("makeStrip: need at least 2 cells");
  }
  for (const L of cellLengths) {
    if (!(L > 0) || !Number.isFinite(L)) {
      throw new Error(`makeStrip: cellLengths must be positive finite (got ${L})`);
    }
  }
  if (!(angleMax > 0) || angleMax > Math.PI) {
    throw new Error(`makeStrip: angleMax must be in (0, π]`);
  }
  return { nCells: cellLengths.length, cellLengths: [...cellLengths], angleMax };
}

export function flatState(config: StripConfig): StripState {
  return { thetas: new Array(config.nCells - 1).fill(0) };
}

export function clampState(config: StripConfig, state: StripState): StripState {
  const m = config.angleMax;
  return {
    thetas: state.thetas.map((t) => Math.max(-m, Math.min(m, t))),
  };
}

export function nHinges(config: StripConfig): number {
  return config.nCells - 1;
}

/**
 * Reflect a state through the strip midpoint.
 * sigma . theta = (theta_{N-1}, theta_{N-2}, ..., theta_1).
 */
export function reflectState(state: StripState): StripState {
  return { thetas: [...state.thetas].reverse() };
}

/**
 * Flip a state (paper-flip): tau . theta = -theta.
 * Mountain <-> Valley.
 */
export function flipState(state: StripState): StripState {
  return { thetas: state.thetas.map((t) => -t) };
}

/** Mountain (M) / Valley (V) / Flat (F) classification of each hinge. */
export type Assignment = "M" | "V" | "F";

export function assignmentOf(state: StripState, eps = 1e-9): readonly Assignment[] {
  return state.thetas.map((t) =>
    t > eps ? "M" : t < -eps ? "V" : "F",
  ) as Assignment[];
}

/** Cell base-plane vectors in local cell frame. */
export const CELL_X_AXIS: Vec3 = [1, 0, 0];
export const CELL_Y_AXIS: Vec3 = [0, 1, 0];
export const CELL_Z_AXIS: Vec3 = [0, 0, 1];
