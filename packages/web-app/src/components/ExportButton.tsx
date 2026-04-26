/**
 * Exports the current trial state as a JSON file conforming to TrialResponseSchema.
 */

import { TrialResponseSchema } from "@kinemind/shared-types";
import { useStripStore } from "../stores/strip-store";

// Inline minimal uuid v4 to avoid adding uuid package dependency.
// We generate a UUID-compatible string using Web Crypto.
function generateUuid(): string {
  if (typeof crypto !== "undefined" && crypto.randomUUID) {
    return crypto.randomUUID();
  }
  // Fallback: RFC 4122 v4 via Math.random (not cryptographically secure, acceptable for trial IDs)
  return "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g, (c) => {
    const r = (Math.random() * 16) | 0;
    const v = c === "x" ? r : (r & 0x3) | 0x8;
    return v.toString(16);
  });
}

export function ExportButton(): React.ReactElement {
  const nCells = useStripStore((s) => s.nCells);
  const config = useStripStore((s) => s.config);
  const thetaIntent = useStripStore((s) => s.thetaIntent);
  const mentalPrediction = useStripStore((s) => s.mentalPrediction);
  const beta = useStripStore((s) => s.beta);
  const couplingType = useStripStore((s) => s.couplingType);
  const addTrial = useStripStore((s) => s.addTrial);

  function handleExport(): void {
    const trialId = generateUuid();
    const stripId = generateUuid();
    const now = new Date().toISOString();

    // Find which hinges user marked as coupled
    const predictedCoupledHinges = mentalPrediction.coupled
      .map((v, i) => (v ? i : -1))
      .filter((i) => i >= 0);

    const raw = {
      trialId,
      subjectId: "web-app-user",
      strip: {
        id: stripId,
        nCells,
        cellLengths: Array.from(config.cellLengths),
        angleMax: config.angleMax,
        thickness: 0.001,
      },
      presentedHinge: 0,
      presentedAngle: thetaIntent[0] ?? 0,
      predictedAngles: Array.from(mentalPrediction.predicted),
      predictedCoupledHinges,
      confidence: 50,
      rtMs: 0,
      timestamp: now,
      device: {
        userAgent: navigator.userAgent,
        viewportWidth: window.innerWidth,
        viewportHeight: window.innerHeight,
      },
      experimentVersion: "0.1.0",
    };

    // Validate with zod before export
    const parsed = TrialResponseSchema.safeParse(raw);
    if (!parsed.success) {
      console.error("[ExportButton] TrialResponseSchema validation failed:", parsed.error);
      alert(`Export validation failed:\n${parsed.error.message}`);
      return;
    }

    addTrial(parsed.data);

    const exportData = {
      trial: parsed.data,
      couplingParams: { beta, couplingType },
    };

    const blob = new Blob([JSON.stringify(exportData, null, 2)], {
      type: "application/json",
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `kinemind-trial-${trialId.slice(0, 8)}.json`;
    a.click();
    URL.revokeObjectURL(url);
  }

  return (
    <button
      type="button"
      onClick={handleExport}
      aria-label="Export current trial as JSON file"
      className="w-full px-4 py-2 bg-blue-600 hover:bg-blue-500 active:bg-blue-700 text-white text-sm font-medium rounded-lg transition-colors focus:outline-none focus:ring-2 focus:ring-blue-400 focus:ring-offset-2 focus:ring-offset-slate-800"
    >
      Export Trial JSON
    </button>
  );
}
