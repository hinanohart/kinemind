/**
 * Keyboard shortcuts help modal.
 * Opened by pressing "?" (via useKeyboardShortcuts).
 * Focus-trapped while open; ESC closes it.
 */

import { useEffect, useRef } from "react";

interface Props {
  readonly isOpen: boolean;
  readonly onClose: () => void;
}

export function ShortcutsHelpModal({ isOpen, onClose }: Props): React.ReactElement | null {
  const overlayRef = useRef<HTMLDivElement>(null);
  const closeButtonRef = useRef<HTMLButtonElement>(null);

  // Focus the close button when modal opens
  useEffect(() => {
    if (isOpen) {
      closeButtonRef.current?.focus();
    }
  }, [isOpen]);

  // Close on ESC
  useEffect(() => {
    if (!isOpen) return;

    function handleKeyDown(e: KeyboardEvent): void {
      if (e.key === "Escape") {
        onClose();
      }
    }

    window.addEventListener("keydown", handleKeyDown);
    return () => {
      window.removeEventListener("keydown", handleKeyDown);
    };
  }, [isOpen, onClose]);

  // Close on overlay click
  function handleOverlayClick(e: React.MouseEvent<HTMLDivElement>): void {
    if (e.target === overlayRef.current) {
      onClose();
    }
  }

  if (!isOpen) return null;

  return (
    <div
      ref={overlayRef}
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60"
      role="dialog"
      aria-modal="true"
      aria-label="Keyboard shortcuts"
      onClick={handleOverlayClick}
      onKeyDown={(e) => {
        if ((e.key === "Enter" || e.key === " ") && e.target === overlayRef.current) onClose();
      }}
    >
      <div className="bg-slate-800 border border-slate-700 rounded-xl p-6 w-80 max-w-full shadow-2xl">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-sm font-semibold text-slate-200">Keyboard shortcuts</h2>
          <button
            ref={closeButtonRef}
            type="button"
            onClick={onClose}
            aria-label="Close shortcuts help"
            className="text-slate-400 hover:text-slate-200 text-lg leading-none focus:outline-none focus:ring-2 focus:ring-blue-400 rounded"
          >
            ✕
          </button>
        </div>

        <dl className="space-y-2 text-xs">
          {(
            [
              ["1 – 9", "Focus hinge slider 1–9"],
              ["?", "Show / hide this help"],
            ] as const
          ).map(([key, desc]) => (
            <div key={key} className="flex items-center gap-3">
              <dt>
                <kbd className="bg-slate-700 border border-slate-600 rounded px-1.5 py-0.5 font-mono text-slate-200">
                  {key}
                </kbd>
              </dt>
              <dd className="text-slate-400">{desc}</dd>
            </div>
          ))}
        </dl>
      </div>
    </div>
  );
}
