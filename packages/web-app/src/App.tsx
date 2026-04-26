/**
 * Top-level application layout.
 *
 * Layout: header + 3-column grid
 *   Left   — 3D strip viewer (StripViewer3D)
 *   Center — controls (HingeSliderArray + BetaSlider + ExportButton)
 *   Right  — heatmap + prediction + diff panels
 */

import { Header } from "./components/Header";
import { StripViewer3D } from "./components/StripViewer3D";
import { HingeSliderArray } from "./components/HingeSliderArray";
import { MentalPredictionPanel } from "./components/MentalPredictionPanel";
import { CouplingHeatmap } from "./components/CouplingHeatmap";
import { DiffPanel } from "./components/DiffPanel";
import { ExportButton } from "./components/ExportButton";
import { BetaSlider } from "./components/BetaSlider";

export function App(): React.ReactElement {
  return (
    <div className="flex flex-col h-screen overflow-hidden bg-slate-950">
      <Header />

      <main className="flex-1 grid grid-cols-1 lg:grid-cols-[1fr_320px_320px] gap-2 p-2 overflow-hidden min-h-0">
        {/* Left: 3D viewer */}
        <section
          className="relative bg-slate-900 rounded-lg overflow-hidden min-h-[300px]"
          aria-label="3D strip visualization"
        >
          <StripViewer3D />
        </section>

        {/* Center: Controls */}
        <aside
          className="flex flex-col gap-2 overflow-y-auto"
          aria-label="Strip controls"
        >
          <HingeSliderArray />
          <BetaSlider />
          <ExportButton />
        </aside>

        {/* Right: Data panels */}
        <aside
          className="flex flex-col gap-2 overflow-y-auto"
          aria-label="Data analysis panels"
        >
          <CouplingHeatmap />
          <MentalPredictionPanel />
          <DiffPanel />
        </aside>
      </main>
    </div>
  );
}
