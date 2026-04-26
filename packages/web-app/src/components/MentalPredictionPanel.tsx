/**
 * Panel where users enter their subjective mental predictions.
 * For each hinge: a checkbox (coupled?) and a number input (predicted angle).
 * Layout uses a semantic <table> for proper a11y cell association.
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
        <h3 className="text-sm font-semibold text-slate-200">Mental Predictions</h3>
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
        For each hinge: check if you think it co-activates, then enter your predicted angle (°)
      </p>

      <table className="w-full text-xs border-collapse" aria-label="Hinge prediction table">
        <thead>
          <tr className="text-slate-500 border-b border-slate-700">
            <th scope="col" className="text-left py-1 w-8">
              H
            </th>
            <th scope="col" className="text-left py-1">
              Co-active?
            </th>
            <th scope="col" className="text-right py-1">
              Predicted (°)
            </th>
            <th scope="col" className="text-right py-1">
              Actual (°)
            </th>
          </tr>
        </thead>
        <tbody>
          {Array.from({ length: nHinges }, (_, i) => {
            const isCoupled = mentalPrediction.coupled[i] ?? false;
            const predAngle = mentalPrediction.predicted[i] ?? 0;
            const actualAngle = thetaMental[i] ?? 0;

            return (
              <tr key={i} className="border-b border-slate-800 last:border-0">
                <th scope="row" className="text-left text-slate-400 py-1 font-normal">
                  {i + 1}
                </th>

                <td className="py-1">
                  <label className="flex items-center gap-1.5 cursor-pointer w-fit">
                    <input
                      type="checkbox"
                      checked={isCoupled}
                      onChange={(e) => setPredictionCoupled(i, e.target.checked)}
                      className="w-3 h-3 accent-blue-500"
                      aria-label={`Hinge ${i + 1} co-activates`}
                    />
                    <span className="text-slate-300">{isCoupled ? "yes" : "no"}</span>
                  </label>
                </td>

                <td className="py-1 text-right">
                  <input
                    type="number"
                    min={-180}
                    max={180}
                    step={1}
                    value={formatAngle(predAngle)}
                    onChange={(e) => setPredictionAngle(i, parseAngle(e.target.value))}
                    className="bg-slate-700 border border-slate-600 rounded px-1 py-0.5 text-xs text-right text-slate-200 w-16 focus:outline-none focus:border-blue-500"
                    aria-label={`Hinge ${i + 1} predicted angle in degrees`}
                  />
                </td>

                <td
                  className="text-slate-400 font-mono text-right py-1"
                  aria-label={`Hinge ${i + 1} actual mental angle: ${formatAngle(actualAngle)} degrees`}
                >
                  {formatAngle(actualAngle)}°
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
