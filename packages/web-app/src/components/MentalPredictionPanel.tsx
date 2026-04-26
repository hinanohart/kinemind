/**
 * Panel where users enter their subjective mental predictions.
 * For each hinge: a checkbox (coupled?) and a number input (predicted angle).
 */

import { useStripStore } from "../stores/strip-store";

function formatAngle(radians: number): string {
  return ((radians * 180) / Math.PI).toFixed(1);
}

function parseAngle(deg: string): number {
  const val = Number(deg);
  if (!Number.isFinite(val)) return 0;
  return Math.max(-180, Math.min(180, val)) * (Math.PI / 180);
}

export function MentalPredictionPanel(): React.ReactElement {
  const nCells = useStripStore((s) => s.nCells);
  const thetaMental = useStripStore((s) => s.thetaMental);
  const mentalPrediction = useStripStore((s) => s.mentalPrediction);
  const setPredictionCoupled = useStripStore((s) => s.setPredictionCoupled);
  const setPredictionAngle = useStripStore((s) => s.setPredictionAngle);
  const predictionRmse = useStripStore((s) => s.predictionRmse);

  const nHinges = nCells - 1;

  return (
    <div className="panel space-y-3" role="region" aria-label="Mental prediction panel">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-slate-200">
          Mental Predictions
        </h3>
        <span
          className="text-xs text-amber-400 font-mono"
          aria-live="polite"
          aria-atomic="true"
          aria-label={`Prediction RMSE: ${predictionRmse.toFixed(3)} radians`}
        >
          RMSE {predictionRmse.toFixed(3)} rad
        </span>
      </div>
      <p className="text-xs text-slate-500">
        For each hinge: check if you think it co-activates, then enter your
        predicted angle (°)
      </p>

      <div className="space-y-1">
        {/* Header row */}
        <div className="grid grid-cols-[2rem_1fr_5rem_5rem] gap-2 text-xs text-slate-500 pb-1 border-b border-slate-700">
          <span aria-hidden="true">H</span>
          <span>Co-active?</span>
          <span className="text-right">Predicted (°)</span>
          <span className="text-right">Actual (°)</span>
        </div>

        {Array.from({ length: nHinges }, (_, i) => {
          const isCoupled = mentalPrediction.coupled[i] ?? false;
          const predAngle = mentalPrediction.predicted[i] ?? 0;
          const actualAngle = thetaMental[i] ?? 0;

          return (
            <div
              key={i}
              className="grid grid-cols-[2rem_1fr_5rem_5rem] gap-2 items-center text-xs"
            >
              <span className="text-slate-400" aria-hidden="true">
                {i + 1}
              </span>

              <label className="flex items-center gap-1.5 cursor-pointer">
                <input
                  type="checkbox"
                  checked={isCoupled}
                  onChange={(e) => setPredictionCoupled(i, e.target.checked)}
                  className="w-3 h-3 accent-blue-500"
                  aria-label={`Hinge ${i + 1} co-activates`}
                />
                <span className="text-slate-300 text-xs">
                  {isCoupled ? "yes" : "no"}
                </span>
              </label>

              <input
                type="number"
                min={-180}
                max={180}
                step={1}
                value={formatAngle(predAngle)}
                onChange={(e) => setPredictionAngle(i, parseAngle(e.target.value))}
                className="bg-slate-700 border border-slate-600 rounded px-1 py-0.5 text-xs text-right text-slate-200 w-full focus:outline-none focus:border-blue-500"
                aria-label={`Hinge ${i + 1} predicted angle in degrees`}
              />

              <span
                className="text-slate-400 font-mono text-right"
                aria-label={`Hinge ${i + 1} actual mental angle: ${formatAngle(actualAngle)} degrees`}
              >
                {formatAngle(actualAngle)}°
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
