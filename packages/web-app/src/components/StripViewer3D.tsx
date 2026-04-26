/**
 * 3D viewer for the origami strip using React Three Fiber.
 *
 * Renders two parallel strip representations:
 *   - "Mental" layer (blue): coupling-derived thetaMental, offset +Y
 *   - "Intent" layer (red): user-controlled thetaIntent, offset -Y, semi-transparent
 *
 * Uses forwardKinematics from @kinemind/core-math to compute cell poses.
 * Quaternion conversion: core-math uses (w, x, y, z), Three.js uses (x, y, z, w).
 */

import { Grid, OrbitControls } from "@react-three/drei";
import { Canvas, useFrame } from "@react-three/fiber";
import { Suspense, useMemo, useRef } from "react";
import * as THREE from "three";

import { forwardKinematics, makeUniformStrip } from "@kinemind/core-math";
import type { Quat, Vec3 } from "@kinemind/core-math";
import { useStripStore } from "../stores/strip-store";

/** Convert core-math Vec3 → Three.js Vector3 */
function toV3(v: Vec3): THREE.Vector3 {
  return new THREE.Vector3(v[0], v[1], v[2]);
}

/** Convert core-math Quat (w, x, y, z) → Three.js Quaternion (x, y, z, w) */
function toQuat(q: Quat): THREE.Quaternion {
  return new THREE.Quaternion(q[1], q[2], q[3], q[0]);
}

interface CellMeshProps {
  readonly position: THREE.Vector3;
  readonly quaternion: THREE.Quaternion;
  readonly cellLength: number;
  readonly color: string;
  readonly opacity: number;
  readonly index: number;
}

function CellMesh({
  position,
  quaternion,
  cellLength,
  color,
  opacity,
  index,
}: CellMeshProps): React.ReactElement {
  const meshRef = useRef<THREE.Mesh>(null);

  // Center offset: cell's origin is at leading edge, center at cellLength/2
  const centreOffset = useMemo(() => new THREE.Vector3(cellLength / 2, 0, 0), [cellLength]);

  return (
    <group position={position} quaternion={quaternion}>
      <mesh ref={meshRef} position={centreOffset} aria-label={`Cell ${index + 1}`}>
        <planeGeometry args={[cellLength, 1]} />
        <meshStandardMaterial
          color={color}
          opacity={opacity}
          transparent={opacity < 1}
          side={THREE.DoubleSide}
          roughness={0.6}
          metalness={0.1}
        />
      </mesh>
      {/* Hinge edge line at leading edge */}
      <lineSegments>
        <edgesGeometry args={[new THREE.PlaneGeometry(cellLength, 1)]} />
        <lineBasicMaterial color="#ffffff" opacity={0.15} transparent />
      </lineSegments>
    </group>
  );
}

interface StripChainProps {
  readonly thetas: readonly number[];
  readonly nCells: number;
  readonly color: string;
  readonly opacity: number;
  readonly offsetY: number;
}

function StripChain({
  thetas,
  nCells,
  color,
  opacity,
  offsetY,
}: StripChainProps): React.ReactElement {
  const config = useMemo(() => makeUniformStrip(nCells), [nCells]);
  const state = useMemo(() => ({ thetas }), [thetas]);

  const result = useMemo(() => {
    try {
      return forwardKinematics(config, state);
    } catch {
      return null;
    }
  }, [config, state]);

  if (result === null) return <group />;

  return (
    <group position={[0, offsetY, 0]}>
      {result.cells.map((cell, i) => {
        const cellLength = config.cellLengths[i] ?? 1;
        return (
          <CellMesh
            key={i}
            index={i}
            position={toV3(cell.position)}
            quaternion={toQuat(cell.frame.q)}
            cellLength={cellLength}
            color={color}
            opacity={opacity}
          />
        );
      })}
    </group>
  );
}

/** Auto-rotate tiny indicator when strip is flat */
function SceneSetup(): React.ReactElement {
  const lightRef = useRef<THREE.DirectionalLight>(null);
  useFrame(({ clock }) => {
    if (lightRef.current) {
      const t = clock.elapsedTime * 0.3;
      lightRef.current.position.set(Math.cos(t) * 5, 5, Math.sin(t) * 5);
    }
  });
  return (
    <>
      <ambientLight intensity={0.5} />
      <directionalLight ref={lightRef} intensity={1.2} castShadow />
    </>
  );
}

function WebGLFallback(): React.ReactElement {
  return (
    <div
      role="alert"
      className="flex items-center justify-center h-full bg-slate-900 text-slate-400 text-sm p-4 text-center"
    >
      <div>
        <p className="font-semibold mb-1">WebGL not available</p>
        <p className="text-xs text-slate-500">
          This browser does not support WebGL. Please use a modern browser such as Chrome, Firefox,
          or Safari to view the 3D strip.
        </p>
      </div>
    </div>
  );
}

function StripScene(): React.ReactElement {
  const nCells = useStripStore((s) => s.nCells);
  const thetaIntent = useStripStore((s) => s.thetaIntent);
  const thetaMental = useStripStore((s) => s.thetaMental);

  return (
    <>
      <SceneSetup />
      <OrbitControls
        makeDefault
        enableDamping
        dampingFactor={0.05}
        minPolarAngle={0}
        maxPolarAngle={Math.PI}
      />
      <Grid
        args={[10, 10]}
        cellSize={1}
        cellThickness={0.5}
        cellColor="#475569"
        sectionSize={5}
        sectionThickness={1}
        sectionColor="#64748b"
        fadeDistance={30}
        position={[0, -1.5, 0]}
      />

      {/* Mental layer: blue, offset +0.5 */}
      <StripChain
        thetas={thetaMental}
        nCells={nCells}
        color="#3b82f6"
        opacity={0.9}
        offsetY={0.5}
      />

      {/* Intent layer: red, offset -0.5, semi-transparent */}
      <StripChain
        thetas={thetaIntent}
        nCells={nCells}
        color="#ef4444"
        opacity={0.5}
        offsetY={-0.5}
      />
    </>
  );
}

export function StripViewer3D(): React.ReactElement {
  // Check WebGL support before rendering Canvas
  const webglSupported = useMemo(() => {
    try {
      const canvas = document.createElement("canvas");
      return !!(canvas.getContext("webgl") || canvas.getContext("experimental-webgl"));
    } catch {
      return false;
    }
  }, []);

  if (!webglSupported) {
    return <WebGLFallback />;
  }

  return (
    <div
      className="w-full h-full"
      role="region"
      aria-label="3D strip viewer — use mouse to orbit, scroll to zoom"
    >
      <Canvas
        camera={{ position: [4, 3, 8], fov: 45 }}
        gl={{ antialias: true, alpha: false }}
        shadows
        style={{ background: "#0f172a" }}
      >
        <Suspense fallback={null}>
          <StripScene />
        </Suspense>
      </Canvas>

      {/* Legend overlay */}
      <div
        className="absolute bottom-2 left-2 flex flex-col gap-1 pointer-events-none"
        aria-hidden="true"
      >
        <div className="flex items-center gap-1.5 text-xs">
          <span className="inline-block w-3 h-3 rounded-sm bg-blue-500 opacity-90" />
          <span className="text-slate-300">Mental (+0.5y)</span>
        </div>
        <div className="flex items-center gap-1.5 text-xs">
          <span className="inline-block w-3 h-3 rounded-sm bg-red-500 opacity-50" />
          <span className="text-slate-300">Intent (−0.5y)</span>
        </div>
      </div>
    </div>
  );
}
