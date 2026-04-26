/**
 * Skeleton placeholder for StripViewer3D while the lazy chunk loads.
 * CSS-only, zero JS animations, fixed dimensions to prevent CLS.
 */

export function StripViewerSkeleton(): React.ReactElement {
  return (
    <div
      className="w-full h-full bg-slate-900 flex items-center justify-center"
      aria-label="Loading 3D viewer…"
      aria-busy="true"
    >
      <div className="flex flex-col items-center gap-3">
        {/* Animated pulse bars — pure CSS, no JS */}
        <div className="flex gap-1.5 items-end h-12" aria-hidden="true">
          {[0, 1, 2, 3, 4].map((i) => (
            <div
              key={i}
              className="w-2 bg-slate-700 rounded-sm animate-pulse"
              style={{
                height: `${[32, 48, 24, 40, 20][i]}px`,
                animationDelay: `${i * 0.12}s`,
              }}
            />
          ))}
        </div>
        <p className="text-xs text-slate-500">Loading 3D viewer…</p>
      </div>
    </div>
  );
}
