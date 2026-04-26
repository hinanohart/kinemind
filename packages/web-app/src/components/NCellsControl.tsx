/**
 * Slider controlling the number of cells (4–32).
 * Placed at the top of the center controls column.
 */

import { useStripStore } from "../stores/strip-store";

export function NCellsControl(): React.ReactElement {
  const nCells = useStripStore((s) => s.nCells);
  const setNCells = useStripStore((s) => s.setNCells);

  const nHinges = nCells - 1;
  const valueText = `${nCells} cells, ${nHinges} hinges`;

  return (
    <div className="panel space-y-3">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-slate-200">Cell Count</h3>
        <span
          className="text-xs text-blue-400 font-mono"
          aria-live="polite"
          aria-atomic="true"
          aria-label={valueText}
        >
          {nCells} cells
        </span>
      </div>
      <input
        type="range"
        id="n-cells-slider"
        min={4}
        max={32}
        step={1}
        value={nCells}
        onChange={(e) => setNCells(Number(e.target.value))}
        className="slider-track w-full"
        aria-label="Number of cells"
        aria-valuemin={4}
        aria-valuemax={32}
        aria-valuenow={nCells}
        aria-valuetext={valueText}
      />
      <p className="text-xs text-slate-500">
        {nCells} cells · {nHinges} hinges
      </p>
    </div>
  );
}
