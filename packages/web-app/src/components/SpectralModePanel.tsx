/**
 * SpectralModePanel — SVG bar chart of eigenvalues of the coupling matrix.
 *
 * For mirror coupling: closed-form eigenvalues (1+β, 1-β, each ⌊n/2⌋ times,
 * plus {1} if n is odd).
 * Click an eigenvalue bar to set thetaIntent to its analytical eigenvector.
 */

import { useMemo } from "react";
import { useStripStore } from "../stores/strip-store";

// ---- Closed-form mirror eigendecomposition ----

interface EigenPair {
  readonly value: number;
  readonly vector: readonly number[];
  readonly label: string;
}

function mirrorEigenPairs(nHinges: number, beta: number): readonly EigenPair[] {
  if (nHinges === 0) return [];

  const pairs: EigenPair[] = [];
  const half = Math.floor(nHinges / 2);

  // Symmetric pairs: (e_i + e_{n-1-i}) / sqrt(2)   eigenvalue = 1 + beta
  for (let i = 0; i < half; i++) {
    const vec = new Array<number>(nHinges).fill(0);
    vec[i] = 1 / Math.SQRT2;
    vec[nHinges - 1 - i] = 1 / Math.SQRT2;
    pairs.push({ value: 1 + beta, vector: vec, label: `sym-${i}` });
  }

  // Antisymmetric pairs: (e_i - e_{n-1-i}) / sqrt(2)   eigenvalue = 1 - beta
  for (let i = 0; i < half; i++) {
    const vec = new Array<number>(nHinges).fill(0);
    vec[i] = 1 / Math.SQRT2;
    vec[nHinges - 1 - i] = -1 / Math.SQRT2;
    pairs.push({ value: 1 - beta, vector: vec, label: `anti-${i}` });
  }

  // Centre mode (only when nHinges is odd): standard basis e_{n/2}  eigenvalue = 1
  if (nHinges % 2 === 1) {
    const mid = Math.floor(nHinges / 2);
    const vec = new Array<number>(nHinges).fill(0);
    vec[mid] = 1;
    pairs.push({ value: 1, vector: vec, label: "centre" });
  }

  // Sort descending by eigenvalue
  pairs.sort((a, b) => b.value - a.value);
  return pairs;
}

// ---- Jacobi eigendecomposition for general (identity) case ----
// Only needed when couplingType === 'identity'; for identity matrix all λ=1.
// We keep it simple: for identity coupling, λ_i = 1 ∀ i.

function identityEigenPairs(nHinges: number): readonly EigenPair[] {
  return Array.from({ length: nHinges }, (_, i) => {
    const vec = new Array<number>(nHinges).fill(0);
    vec[i] = 1;
    return { value: 1, vector: vec, label: `e${i}` };
  });
}

// ---- SVG constants ----
const BAR_WIDTH = 14;
const BAR_GAP = 4;
const MAX_HEIGHT = 60;
const SVG_PADDING_TOP = 4;
const SVG_PADDING_BOTTOM = 16; // space for axis labels

// ---- Component ----

export function SpectralModePanel(): React.ReactElement {
  const nCells = useStripStore((s) => s.nCells);
  const beta = useStripStore((s) => s.beta);
  const couplingType = useStripStore((s) => s.couplingType);
  const setThetaIntent = useStripStore((s) => s.setThetaIntent);
  const nHinges = nCells - 1;

  const pairs = useMemo<readonly EigenPair[]>(() => {
    if (nHinges <= 0) return [];
    if (couplingType === "mirror") return mirrorEigenPairs(nHinges, beta);
    return identityEigenPairs(nHinges);
  }, [nHinges, beta, couplingType]);

  const maxEig = useMemo(() => Math.max(...pairs.map((p) => Math.abs(p.value)), 1), [pairs]);

  const svgWidth = Math.max(10, pairs.length * (BAR_WIDTH + BAR_GAP) - BAR_GAP);
  const svgHeight = MAX_HEIGHT + SVG_PADDING_TOP + SVG_PADDING_BOTTOM;

  function handleBarClick(pair: EigenPair): void {
    // Scale eigenvector to π/2 for a visible fold
    const scale = Math.PI / 2;
    pair.vector.forEach((v, i) => {
      setThetaIntent(i, v * scale);
    });
  }

  return (
    <div className="panel space-y-3" role="region" aria-label="Spectral mode visualizer">
      <h3 className="text-sm font-semibold text-slate-200" id="spectral-heading">
        Spectral Modes
      </h3>
      <p className="text-xs text-slate-500">
        Eigenvalues of the coupling matrix — click a bar to set that eigenvector
      </p>

      {pairs.length === 0 ? (
        <p className="text-xs text-slate-600 italic">No hinges</p>
      ) : (
        <svg
          width={svgWidth}
          height={svgHeight}
          aria-labelledby="spectral-heading"
          role="img"
          className="overflow-visible"
        >
          <title>Eigenvalue bar chart</title>
          {pairs.map((pair, idx) => {
            const barHeight = Math.max(2, (Math.abs(pair.value) / maxEig) * MAX_HEIGHT);
            const x = idx * (BAR_WIDTH + BAR_GAP);
            const y = SVG_PADDING_TOP + (MAX_HEIGHT - barHeight);
            const isPositive = pair.value >= 0;
            const fill = isPositive ? "#3b82f6" : "#ef4444";

            return (
              <g key={pair.label}>
                <rect
                  x={x}
                  y={y}
                  width={BAR_WIDTH}
                  height={barHeight}
                  fill={fill}
                  rx={2}
                  style={{ cursor: "pointer" }}
                  onClick={() => handleBarClick(pair)}
                  tabIndex={0}
                  role="button"
                  aria-label={`Eigenvalue ${pair.value.toFixed(3)}: click to set eigenvector`}
                  onKeyDown={(e) => {
                    if (e.key === "Enter" || e.key === " ") {
                      e.preventDefault();
                      handleBarClick(pair);
                    }
                  }}
                />
                {/* Axis label: eigenvalue rounded */}
                <text
                  x={x + BAR_WIDTH / 2}
                  y={svgHeight - 2}
                  textAnchor="middle"
                  fontSize={8}
                  fill="#94a3b8"
                >
                  {pair.value.toFixed(2)}
                </text>
              </g>
            );
          })}
        </svg>
      )}

      <p className="text-xs text-slate-600">
        {couplingType === "mirror" ? "Closed-form (mirror)" : "Identity: all λ=1"}
      </p>
    </div>
  );
}
