/**
 * Top-level application layout.
 *
 * Layout: header + 3-column grid
 *   Left   — 3D strip viewer (StripViewer3D) — lazy-loaded chunk
 *   Center — controls (NCellsControl + HingeSliderArray + BetaSlider + ExportButton)
 *   Right  — heatmap + prediction + diff + spectral panels
 */

import { Suspense, lazy } from "react";
import { BetaSlider } from "./components/BetaSlider";
import { CouplingHeatmap } from "./components/CouplingHeatmap";
import { DiffPanel } from "./components/DiffPanel";
import { ErrorBoundary } from "./components/ErrorBoundary";
import { ExportButton } from "./components/ExportButton";
import { Header } from "./components/Header";
import { HingeSliderArray } from "./components/HingeSliderArray";
import { MentalPredictionPanel } from "./components/MentalPredictionPanel";
import { NCellsControl } from "./components/NCellsControl";
import { ShortcutsHelpModal } from "./components/ShortcutsHelpModal";
import { SpectralModePanel } from "./components/SpectralModePanel";
import { StripViewerSkeleton } from "./components/StripViewerSkeleton";
import { useKeyboardShortcuts } from "./hooks/useKeyboardShortcuts";

// Lazy-load the heavy Three.js / R3F chunk (three-r3f manualChunk).
const StripViewer3D = lazy(() =>
  import("./components/StripViewer3D").then((m) => ({ default: m.StripViewer3D })),
);

export function App(): React.ReactElement {
  const { helpOpen, closeHelp } = useKeyboardShortcuts();

  return (
    <div className="flex flex-col h-screen overflow-hidden bg-slate-950">
      <Header />

      <main className="flex-1 grid grid-cols-1 lg:grid-cols-[1fr_320px_320px] gap-2 p-2 overflow-hidden min-h-0">
        {/* Left: 3D viewer — lazy chunk with skeleton fallback */}
        <section
          className="relative bg-slate-900 rounded-lg overflow-hidden min-h-[300px]"
          aria-label="3D strip visualization"
        >
          <ErrorBoundary>
            <Suspense fallback={<StripViewerSkeleton />}>
              <StripViewer3D />
            </Suspense>
          </ErrorBoundary>
        </section>

        {/* Center: Controls */}
        <aside className="flex flex-col gap-2 overflow-y-auto" aria-label="Strip controls">
          <NCellsControl />
          <HingeSliderArray />
          <BetaSlider />
          <ExportButton />
        </aside>

        {/* Right: Data panels */}
        <aside className="flex flex-col gap-2 overflow-y-auto" aria-label="Data analysis panels">
          <CouplingHeatmap />
          <MentalPredictionPanel />
          <DiffPanel />
          <SpectralModePanel />
        </aside>
      </main>

      <ShortcutsHelpModal isOpen={helpOpen} onClose={closeHelp} />
    </div>
  );
}
