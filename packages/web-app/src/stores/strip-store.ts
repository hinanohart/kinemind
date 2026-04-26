/**
 * Zustand store for the kinemind strip simulation.
 *
 * State model:
 *   - nCells: number of cells (default 8, so 7 hinges)
 *   - thetaIntent: user-controlled hinge angles (length = nCells - 1)
 *   - thetaMental: coupling-derived mental prediction (computed from thetaIntent)
 *   - beta: coupling strength in [0, 1]
 *   - couplingType: 'mirror' | 'identity'
 *   - trialHistory: saved trial records
 */

import { create } from "zustand";
import {
  makeUniformStrip,
  mirrorCouplingMatrix,
  identityCoupling,
  applyCoupling,
  type StripConfig,
} from "@kinemind/core-math";
import type { TrialResponse } from "@kinemind/shared-types";

export type CouplingType = "mirror" | "identity";

export interface MentalPrediction {
  /** Per-hinge: whether user thinks this hinge co-activates */
  readonly coupled: readonly boolean[];
  /** Per-hinge: user's manually entered predicted angle */
  readonly predicted: readonly number[];
}

export interface StripStore {
  // --- Config ---
  readonly nCells: number;
  readonly config: StripConfig;

  // --- Intent (user-controlled angles) ---
  readonly thetaIntent: readonly number[];

  // --- Mental (coupling-computed angles) ---
  readonly thetaMental: readonly number[];

  // --- Coupling params ---
  readonly beta: number;
  readonly couplingType: CouplingType;

  // --- Mental prediction (user's subjective prediction) ---
  readonly mentalPrediction: MentalPrediction;

  // --- Trial history ---
  readonly trialHistory: readonly TrialResponse[];

  // --- Derived ---
  /** RMSE between thetaMental and mentalPrediction.predicted */
  readonly predictionRmse: number;

  // --- Actions ---
  setNCells: (n: number) => void;
  setThetaIntent: (index: number, value: number) => void;
  setBeta: (beta: number) => void;
  setCouplingType: (type: CouplingType) => void;
  setPredictionCoupled: (index: number, coupled: boolean) => void;
  setPredictionAngle: (index: number, angle: number) => void;
  addTrial: (trial: TrialResponse) => void;
  resetTrials: () => void;
}

/** Recompute thetaMental from current intent + coupling params. */
function computeMental(
  thetaIntent: readonly number[],
  beta: number,
  couplingType: CouplingType,
): readonly number[] {
  const nHinges = thetaIntent.length;
  if (nHinges === 0) return [];

  const coupling =
    couplingType === "mirror"
      ? mirrorCouplingMatrix(nHinges, beta)
      : identityCoupling(nHinges);

  return applyCoupling(coupling, thetaIntent, Math.PI);
}

/** Compute RMSE between two angle arrays. */
function computeRmse(a: readonly number[], b: readonly number[]): number {
  if (a.length === 0 || b.length !== a.length) return 0;
  const sumSq = a.reduce((acc, ai, i) => {
    const bi = b[i] ?? 0;
    return acc + (ai - bi) ** 2;
  }, 0);
  return Math.sqrt(sumSq / a.length);
}

/** Build initial intent/prediction arrays for nCells. */
function buildInitialArrays(nCells: number): {
  thetaIntent: readonly number[];
  thetaMental: readonly number[];
  mentalPrediction: MentalPrediction;
} {
  const nHinges = nCells - 1;
  const thetaIntent = Array.from<number>({ length: nHinges }).fill(0);
  const thetaMental = Array.from<number>({ length: nHinges }).fill(0);
  const mentalPrediction: MentalPrediction = {
    coupled: Array.from<boolean>({ length: nHinges }).fill(false),
    predicted: Array.from<number>({ length: nHinges }).fill(0),
  };
  return { thetaIntent, thetaMental, mentalPrediction };
}

const DEFAULT_N_CELLS = 8;
const DEFAULT_BETA = 0.6;

export const useStripStore = create<StripStore>((set) => {
  const { thetaIntent, thetaMental, mentalPrediction } =
    buildInitialArrays(DEFAULT_N_CELLS);

  return {
    nCells: DEFAULT_N_CELLS,
    config: makeUniformStrip(DEFAULT_N_CELLS),
    thetaIntent,
    thetaMental,
    beta: DEFAULT_BETA,
    couplingType: "mirror" as CouplingType,
    mentalPrediction,
    trialHistory: [],
    predictionRmse: 0,

    setNCells: (n: number) => {
      const safeN = Math.max(2, Math.min(50, n));
      const { thetaIntent, thetaMental, mentalPrediction } =
        buildInitialArrays(safeN);
      set({
        nCells: safeN,
        config: makeUniformStrip(safeN),
        thetaIntent,
        thetaMental,
        mentalPrediction,
        predictionRmse: 0,
      });
    },

    setThetaIntent: (index: number, value: number) => {
      set((state) => {
        const next = [...state.thetaIntent];
        next[index] = Math.max(-Math.PI, Math.min(Math.PI, value));
        const nextMental = computeMental(next, state.beta, state.couplingType);
        return {
          thetaIntent: next,
          thetaMental: nextMental,
          predictionRmse: computeRmse(
            nextMental,
            state.mentalPrediction.predicted,
          ),
        };
      });
    },

    setBeta: (beta: number) => {
      set((state) => {
        const safeBeta = Math.max(0, Math.min(1, beta));
        const nextMental = computeMental(
          state.thetaIntent,
          safeBeta,
          state.couplingType,
        );
        return {
          beta: safeBeta,
          thetaMental: nextMental,
          predictionRmse: computeRmse(
            nextMental,
            state.mentalPrediction.predicted,
          ),
        };
      });
    },

    setCouplingType: (type: CouplingType) => {
      set((state) => {
        const nextMental = computeMental(state.thetaIntent, state.beta, type);
        return {
          couplingType: type,
          thetaMental: nextMental,
          predictionRmse: computeRmse(
            nextMental,
            state.mentalPrediction.predicted,
          ),
        };
      });
    },

    setPredictionCoupled: (index: number, coupled: boolean) => {
      set((state) => {
        const next = [...state.mentalPrediction.coupled];
        next[index] = coupled;
        return {
          mentalPrediction: { ...state.mentalPrediction, coupled: next },
        };
      });
    },

    setPredictionAngle: (index: number, angle: number) => {
      set((state) => {
        const next = [...state.mentalPrediction.predicted];
        next[index] = Math.max(-Math.PI, Math.min(Math.PI, angle));
        return {
          mentalPrediction: {
            ...state.mentalPrediction,
            predicted: next,
          },
          predictionRmse: computeRmse(state.thetaMental, next),
        };
      });
    },

    addTrial: (trial: TrialResponse) => {
      set((state) => ({
        trialHistory: [...state.trialHistory, trial],
      }));
    },

    resetTrials: () => {
      set({ trialHistory: [] });
    },
  };
});
