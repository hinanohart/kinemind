/**
 * Slider for the coupling strength parameter beta ∈ [0, 1].
 */

import { useStripStore } from "../stores/strip-store";
import type { CouplingType } from "../stores/strip-store";

export function BetaSlider(): React.ReactElement {
  const beta = useStripStore((s) => s.beta);
  const couplingType = useStripStore((s) => s.couplingType);
  const setBeta = useStripStore((s) => s.setBeta);
  const setCouplingType = useStripStore((s) => s.setCouplingType);

  return (
    <div className="panel space-y-3">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-slate-200">Coupling Parameters</h3>
        <span className="text-xs text-blue-400 font-mono" aria-live="polite" aria-atomic="true">
          β = {beta.toFixed(2)}
        </span>
      </div>

      <div className="space-y-1">
        <label htmlFor="beta-slider" className="text-xs text-slate-400 flex justify-between">
          <span>Coupling strength β</span>
          <span className="text-slate-500">0 → identity · 1 → mirror</span>
        </label>
        <input
          id="beta-slider"
          type="range"
          min={0}
          max={1}
          step={0.01}
          value={beta}
          onChange={(e) => setBeta(Number(e.target.value))}
          className="slider-track w-full"
          aria-label={`Coupling strength beta: ${beta.toFixed(2)}`}
          aria-valuemin={0}
          aria-valuemax={1}
          aria-valuenow={beta}
        />
      </div>

      <div className="flex items-center gap-3">
        <span className="text-xs text-slate-400">Coupling type:</span>
        {(["mirror", "identity"] as CouplingType[]).map((type) => (
          <button
            key={type}
            type="button"
            onClick={() => setCouplingType(type)}
            aria-pressed={couplingType === type}
            className={`text-xs px-2 py-1 rounded transition-colors ${
              couplingType === type
                ? "bg-blue-600 text-white"
                : "bg-slate-700 text-slate-300 hover:bg-slate-600"
            }`}
          >
            {type}
          </button>
        ))}
      </div>
    </div>
  );
}
