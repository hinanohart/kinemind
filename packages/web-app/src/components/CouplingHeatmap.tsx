/**
 * 7×7 SVG heatmap of the coupling matrix.
 *
 * Color scale: symmetric log mapping to red (negative) / green (positive).
 * The diagonal is always 1.0 (self-coupling).
 */

import { useMemo } from "react";
import { useStripStore } from "../stores/strip-store";
import {
  mirrorCouplingMatrix,
  identityCoupling,
} from "@kinemind/core-math";

const CELL_SIZE = 28;
const PADDING = 24;
const LABEL_SIZE = 16;

function symlogColor(v: number, maxVal: number): string {
  if (maxVal < 1e-10) return "rgb(100,116,139)"; // slate-500 for flat
  const normalized = Math.max(-1, Math.min(1, v / maxVal));
  if (normalized >= 0) {
    const intensity = Math.round(normalized * 200);
    return `rgb(${50 - intensity / 5},${100 + intensity},${50 - intensity / 5})`;
  } else {
    const intensity = Math.round(-normalized * 200);
    return `rgb(${100 + intensity},${50 - intensity / 5},${50 - intensity / 5})`;
  }
}

function formatVal(v: number): string {
  return Math.abs(v) < 0.005 ? "0" : v.toFixed(2);
}

export function CouplingHeatmap(): React.ReactElement {
  const nCells = useStripStore((s) => s.nCells);
  const beta = useStripStore((s) => s.beta);
  const couplingType = useStripStore((s) => s.couplingType);

  const nHinges = nCells - 1;

  const matrix = useMemo(() => {
    const coupling =
      couplingType === "mirror"
        ? mirrorCouplingMatrix(nHinges, beta)
        : identityCoupling(nHinges);
    return coupling.matrix;
  }, [nHinges, beta, couplingType]);

  const maxOffDiag = useMemo(() => {
    let m = 0;
    for (let r = 0; r < nHinges; r++) {
      for (let c = 0; c < nHinges; c++) {
        if (r !== c) {
          m = Math.max(m, Math.abs(matrix[r]?.[c] ?? 0));
        }
      }
    }
    return m;
  }, [matrix, nHinges]);

  const svgW = LABEL_SIZE + nHinges * CELL_SIZE + PADDING;
  const svgH = LABEL_SIZE + nHinges * CELL_SIZE + PADDING;

  const ariaDesc = `${nHinges}x${nHinges} coupling matrix. Type: ${couplingType}, beta: ${beta.toFixed(2)}. Diagonal entries are 1.0 (self-coupling). Off-diagonal entries show cross-hinge coupling strength.`;

  return (
    <div
      className="panel space-y-2"
      role="region"
      aria-label="Coupling matrix heatmap"
    >
      <h3 className="text-sm font-semibold text-slate-200">
        Coupling Matrix C
      </h3>
      <p className="text-xs text-slate-500">
        Green = positive coupling · Red = negative · Diagonal = self (1.0)
      </p>

      <div className="overflow-x-auto">
        <svg
          width={svgW}
          height={svgH}
          role="img"
          aria-label={`Coupling heatmap: ${nHinges}x${nHinges} matrix`}
          aria-description={ariaDesc}
        >
          <title>Coupling Matrix Heatmap</title>
          <desc>{ariaDesc}</desc>

          {/* Column labels */}
          {Array.from({ length: nHinges }, (_, c) => (
            <text
              key={`col-${c}`}
              x={LABEL_SIZE + c * CELL_SIZE + CELL_SIZE / 2}
              y={LABEL_SIZE - 2}
              textAnchor="middle"
              className="fill-slate-400"
              style={{ fontSize: 9, fill: "#94a3b8" }}
            >
              {c + 1}
            </text>
          ))}

          {/* Row labels */}
          {Array.from({ length: nHinges }, (_, r) => (
            <text
              key={`row-${r}`}
              x={LABEL_SIZE - 3}
              y={LABEL_SIZE + r * CELL_SIZE + CELL_SIZE / 2 + 3}
              textAnchor="end"
              style={{ fontSize: 9, fill: "#94a3b8" }}
            >
              {r + 1}
            </text>
          ))}

          {/* Matrix cells */}
          {Array.from({ length: nHinges }, (_, r) =>
            Array.from({ length: nHinges }, (_, c) => {
              const v = matrix[r]?.[c] ?? 0;
              const isDiag = r === c;
              const color = isDiag
                ? "rgb(59,130,246)"
                : symlogColor(v, maxOffDiag);
              const x = LABEL_SIZE + c * CELL_SIZE;
              const y = LABEL_SIZE + r * CELL_SIZE;
              const textVal = formatVal(v);

              return (
                <g key={`${r}-${c}`}>
                  <rect
                    x={x + 1}
                    y={y + 1}
                    width={CELL_SIZE - 2}
                    height={CELL_SIZE - 2}
                    fill={color}
                    rx={2}
                    aria-label={`Row ${r + 1} col ${c + 1}: ${textVal}`}
                  />
                  {CELL_SIZE >= 24 && (
                    <text
                      x={x + CELL_SIZE / 2}
                      y={y + CELL_SIZE / 2 + 3}
                      textAnchor="middle"
                      style={{
                        fontSize: 7,
                        fill: "rgba(255,255,255,0.85)",
                        fontFamily: "monospace",
                      }}
                    >
                      {textVal}
                    </text>
                  )}
                </g>
              );
            }),
          )}
        </svg>
      </div>

      <div className="flex gap-4 text-xs text-slate-500 mt-1">
        <span>
          <span className="inline-block w-3 h-3 rounded-sm bg-blue-500 mr-1 align-middle" />
          diagonal (self=1)
        </span>
        <span>
          <span className="inline-block w-3 h-3 rounded-sm bg-green-500 mr-1 align-middle" />
          positive
        </span>
        <span>
          <span className="inline-block w-3 h-3 rounded-sm bg-red-500 mr-1 align-middle" />
          negative
        </span>
      </div>
    </div>
  );
}
