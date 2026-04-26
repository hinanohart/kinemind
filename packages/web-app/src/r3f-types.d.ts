/**
 * React 19 + @react-three/fiber v8 JSX namespace compatibility shim.
 *
 * @react-three/fiber v8 augments the legacy global `JSX.IntrinsicElements`,
 * but React 19 with `jsx: "react-jsx"` resolves JSX through
 * `react/jsx-runtime`, which has its own `namespace JSX` that delegates
 * to `React.JSX.IntrinsicElements`.
 *
 * This shim augments both `react/jsx-runtime` and `react` so Three.js JSX
 * elements type-check under strict mode.
 *
 * Remove when upgrading to @react-three/fiber v9+ (React 19 native support).
 */

import type { ThreeElements } from "@react-three/fiber";

// Augment react/jsx-runtime — this is what `jsx: "react-jsx"` actually uses
declare module "react/jsx-runtime" {
  namespace JSX {
    interface IntrinsicElements extends ThreeElements {}
  }
}

// Augment React.JSX for type utilities (React.JSX.Element etc.)
declare module "react" {
  namespace JSX {
    interface IntrinsicElements extends ThreeElements {}
  }
}
