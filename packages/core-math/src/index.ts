/**
 * @kinemind/core-math: SE(3) kinematics, V_4 symmetry, and mental coupling
 * matrix primitives for 1D origami strips.
 *
 * Public API surface for the rest of the kinemind monorepo. See MATH.md
 * for the formal derivations and ARCHITECTURE.md for how these primitives
 * compose with the simulation, web, and analysis layers.
 */

export * from "./se3.js";
export * from "./strip.js";
export * from "./kinematics.js";
export * from "./symmetry.js";
export * from "./coupling.js";

export const KINEMIND_CORE_MATH_VERSION = "0.1.0" as const;
