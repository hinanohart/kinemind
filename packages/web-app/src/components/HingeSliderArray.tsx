/**
 * Array of 7 range sliders controlling thetaIntent[i] ∈ [-π, π].
 */

import { useStripStore } from "../stores/strip-store";

function formatAngle(radians: number): string {
  const deg = ((radians * 180) / Math.PI).toFixed(1);
  return `${deg}°`;
}

interface HingeSliderProps {
  readonly index: number;
  readonly value: number;
  readonly onChange: (index: number, value: number) => void;
}

function HingeSlider({ index, value, onChange }: HingeSliderProps): React.ReactElement {
  const deg = formatAngle(value);
  const label = `Hinge ${index + 1} angle`;

  return (
    <div className="flex items-center gap-2 text-xs">
      <span className="w-14 text-slate-400 shrink-0 text-right" aria-hidden="true">
        H{index + 1}
      </span>
      <input
        id={`hinge-slider-${index}`}
        type="range"
        min={-Math.PI}
        max={Math.PI}
        step={0.01}
        value={value}
        onChange={(e) => onChange(index, Number(e.target.value))}
        className="slider-track flex-1 min-w-0"
        aria-label={`${label}: ${deg}`}
        aria-valuemin={-Math.PI}
        aria-valuemax={Math.PI}
        aria-valuenow={value}
        aria-valuetext={deg}
      />
      <span className="w-14 text-blue-400 font-mono shrink-0" aria-live="polite" aria-atomic="true">
        {deg}
      </span>
    </div>
  );
}

export function HingeSliderArray(): React.ReactElement {
  const nCells = useStripStore((s) => s.nCells);
  const thetaIntent = useStripStore((s) => s.thetaIntent);
  const setThetaIntent = useStripStore((s) => s.setThetaIntent);

  const nHinges = nCells - 1;

  return (
    <div className="panel space-y-3" role="group" aria-labelledby="hinge-sliders-heading">
      <h3 id="hinge-sliders-heading" className="text-sm font-semibold text-slate-200">
        Intent Angles
      </h3>
      <p className="text-xs text-slate-500">Drag sliders to set physical fold angles (−π to +π)</p>
      <div className="space-y-2">
        {Array.from({ length: nHinges }, (_, i) => (
          <HingeSlider key={i} index={i} value={thetaIntent[i] ?? 0} onChange={setThetaIntent} />
        ))}
      </div>
    </div>
  );
}
