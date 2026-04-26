/**
 * Panel showing RMSE between thetaMental and user's manual predictions,
 * plus a per-hinge difference bar chart.
 */

import { useStripStore } from "../stores/strip-store";

function clampedBarWidth(diffRad: number): number {
  return Math.min(100, (Math.abs(diffRad) / Math.PI) * 100);
}

export function DiffPanel(): React.ReactElement {
  const nCells = useStripStore((s) => s.nCells);
  const thetaMental = useStripStore((s) => s.thetaMental);
  const mentalPrediction = useStripStore((s) => s.mentalPrediction);
  const predictionRmse = useStripStore((s) => s.predictionRmse);

  const nHinges = nCells - 1;

  return (
    <div className="panel space-y-3" role="region" aria-label="Prediction difference panel">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-slate-200">Prediction vs Mental</h3>
        <div
          className="text-xs font-mono"
          aria-live="polite"
          aria-atomic="true"
          aria-label={`RMSE: ${predictionRmse.toFixed(4)} radians`}
        >
          <span className="text-slate-400">RMSE </span>
          <span
            className={
              predictionRmse < 0.1
                ? "text-green-400"
                : predictionRmse < 0.5
                  ? "text-amber-400"
                  : "text-red-400"
            }
          >
            {predictionRmse.toFixed(4)}
          </span>
          <span className="text-slate-500"> rad</span>
        </div>
      </div>

      <p className="text-xs text-slate-500">
        Per-hinge difference |mental − prediction| (bar width = fraction of π)
      </p>

      <div className="space-y-1.5" role="list">
        {Array.from({ length: nHinges }, (_, i) => {
          const mental = thetaMental[i] ?? 0;
          const pred = mentalPrediction.predicted[i] ?? 0;
          const diff = mental - pred;
          const absDiff = Math.abs(diff);
          const barW = clampedBarWidth(diff);
          const diffDeg = ((absDiff * 180) / Math.PI).toFixed(1);

          const color =
            absDiff < 0.1 ? "bg-green-500" : absDiff < 0.5 ? "bg-amber-500" : "bg-red-500";

          return (
            <div
              key={i}
              className="flex items-center gap-2 text-xs"
              role="listitem"
              aria-label={`Hinge ${i + 1} difference: ${diffDeg} degrees`}
            >
              <span className="w-5 text-slate-400 text-right shrink-0" aria-hidden="true">
                {i + 1}
              </span>
              <div
                className="flex-1 bg-slate-700 rounded-full h-2 overflow-hidden"
                aria-hidden="true"
              >
                <div
                  className={`h-2 rounded-full transition-all duration-150 ${color}`}
                  style={{ width: `${barW}%` }}
                />
              </div>
              <span className="w-14 font-mono text-slate-300 text-right shrink-0">{diffDeg}°</span>
            </div>
          );
        })}
      </div>

      {predictionRmse === 0 && (
        <p className="text-xs text-slate-600 text-center pt-2">
          Enter predictions in the panel above to see differences
        </p>
      )}
    </div>
  );
}
