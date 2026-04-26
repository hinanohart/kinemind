/**
 * Keyboard shortcuts for kinemind.
 *
 * 1–9  →  focus hinge-slider-{0}…{8}
 * ?    →  toggle shortcuts help modal
 */

import { useEffect, useState } from "react";

/** Returns whether the keyboard shortcuts help modal is open. */
export function useKeyboardShortcuts(): { helpOpen: boolean; closeHelp: () => void } {
  const [helpOpen, setHelpOpen] = useState(false);

  useEffect(() => {
    function handleKeydown(e: KeyboardEvent): void {
      // Ignore when user is typing in an input / textarea / select / contenteditable
      const target = e.target as HTMLElement | null;
      if (
        target instanceof HTMLInputElement ||
        target instanceof HTMLTextAreaElement ||
        target instanceof HTMLSelectElement ||
        target?.isContentEditable
      ) {
        return;
      }

      if (e.key === "?") {
        setHelpOpen((prev) => !prev);
        return;
      }

      // Keys 1–9 focus the corresponding hinge slider (0-indexed)
      const digit = Number(e.key);
      if (Number.isInteger(digit) && digit >= 1 && digit <= 9) {
        const slider = document.getElementById(`hinge-slider-${digit - 1}`);
        slider?.focus();
      }
    }

    window.addEventListener("keydown", handleKeydown);
    return () => {
      window.removeEventListener("keydown", handleKeydown);
    };
  }, []);

  const closeHelp = (): void => setHelpOpen(false);

  return { helpOpen, closeHelp };
}
