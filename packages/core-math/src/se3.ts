/**
 * SE(3) Lie group primitives for rigid body kinematics.
 *
 * We use a minimal, dependency-free implementation so the mathematical
 * structure is auditable line-by-line against MATH.md. Rotations are
 * represented as unit quaternions (drift-resistant under composition);
 * full 4x4 homogeneous matrices are exposed for interop.
 *
 * Conventions
 *  - Quaternion order: (w, x, y, z) with w as the real part.
 *  - Rotation acts on column vectors: v' = R v.
 *  - Composition reads left-to-right: T1.then(T2) means "apply T1 first".
 *  - All angles are radians.
 */

export type Vec3 = readonly [number, number, number];
export type Quat = readonly [number, number, number, number]; // (w, x, y, z)
export type Mat3 = readonly [Vec3, Vec3, Vec3]; // row-major
export type Mat4 = readonly [
  readonly [number, number, number, number],
  readonly [number, number, number, number],
  readonly [number, number, number, number],
  readonly [number, number, number, number],
];

export const EPS = 1e-12;

// ------------------------- vec3 helpers -------------------------

export function v3(x: number, y: number, z: number): Vec3 {
  return [x, y, z];
}

export function v3Add(a: Vec3, b: Vec3): Vec3 {
  return [a[0] + b[0], a[1] + b[1], a[2] + b[2]];
}

export function v3Sub(a: Vec3, b: Vec3): Vec3 {
  return [a[0] - b[0], a[1] - b[1], a[2] - b[2]];
}

export function v3Scale(a: Vec3, s: number): Vec3 {
  return [a[0] * s, a[1] * s, a[2] * s];
}

export function v3Dot(a: Vec3, b: Vec3): number {
  return a[0] * b[0] + a[1] * b[1] + a[2] * b[2];
}

export function v3Cross(a: Vec3, b: Vec3): Vec3 {
  return [
    a[1] * b[2] - a[2] * b[1],
    a[2] * b[0] - a[0] * b[2],
    a[0] * b[1] - a[1] * b[0],
  ];
}

export function v3Norm(a: Vec3): number {
  return Math.hypot(a[0], a[1], a[2]);
}

export function v3Normalize(a: Vec3): Vec3 {
  const n = v3Norm(a);
  if (n < EPS) {
    throw new Error("v3Normalize: zero-length vector");
  }
  return [a[0] / n, a[1] / n, a[2] / n];
}

// ------------------------- quaternion -------------------------

export const QUAT_IDENTITY: Quat = [1, 0, 0, 0];

export function quatFromAxisAngle(axis: Vec3, angle: number): Quat {
  const a = v3Normalize(axis);
  const half = angle * 0.5;
  const s = Math.sin(half);
  return [Math.cos(half), a[0] * s, a[1] * s, a[2] * s];
}

/**
 * Hamilton product. Encodes rotation composition in the order
 * "rotate by q2 first, then by q1" when applied via quatRotate(quatMul(q1, q2), v).
 */
export function quatMul(q1: Quat, q2: Quat): Quat {
  const [w1, x1, y1, z1] = q1;
  const [w2, x2, y2, z2] = q2;
  return [
    w1 * w2 - x1 * x2 - y1 * y2 - z1 * z2,
    w1 * x2 + x1 * w2 + y1 * z2 - z1 * y2,
    w1 * y2 - x1 * z2 + y1 * w2 + z1 * x2,
    w1 * z2 + x1 * y2 - y1 * x2 + z1 * w2,
  ];
}

export function quatConjugate(q: Quat): Quat {
  return [q[0], -q[1], -q[2], -q[3]];
}

export function quatNormalize(q: Quat): Quat {
  const n = Math.hypot(q[0], q[1], q[2], q[3]);
  if (n < EPS) {
    throw new Error("quatNormalize: zero quaternion");
  }
  return [q[0] / n, q[1] / n, q[2] / n, q[3] / n];
}

export function quatRotate(q: Quat, v: Vec3): Vec3 {
  // v' = q * (0, v) * q^{-1}, expanded for efficiency.
  const [w, x, y, z] = q;
  const tx = 2 * (y * v[2] - z * v[1]);
  const ty = 2 * (z * v[0] - x * v[2]);
  const tz = 2 * (x * v[1] - y * v[0]);
  return [
    v[0] + w * tx + (y * tz - z * ty),
    v[1] + w * ty + (z * tx - x * tz),
    v[2] + w * tz + (x * ty - y * tx),
  ];
}

export function quatToMat3(q: Quat): Mat3 {
  const [w, x, y, z] = q;
  const xx = x * x;
  const yy = y * y;
  const zz = z * z;
  const xy = x * y;
  const xz = x * z;
  const yz = y * z;
  const wx = w * x;
  const wy = w * y;
  const wz = w * z;
  return [
    [1 - 2 * (yy + zz), 2 * (xy - wz), 2 * (xz + wy)],
    [2 * (xy + wz), 1 - 2 * (xx + zz), 2 * (yz - wx)],
    [2 * (xz - wy), 2 * (yz + wx), 1 - 2 * (xx + yy)],
  ];
}

// ------------------------- SE(3) -------------------------

/**
 * Rigid body transform: rotation (unit quaternion) + translation (vec3).
 * Stored as immutable triplet so we can flow them through pure pipelines.
 */
export interface SE3 {
  readonly q: Quat;
  readonly t: Vec3;
}

export const SE3_IDENTITY: SE3 = { q: QUAT_IDENTITY, t: [0, 0, 0] };

export function se3(q: Quat, t: Vec3): SE3 {
  return { q, t };
}

/**
 * Compose two transforms: result = a then b (matrix interpretation: M_a M_b).
 * Applied to a vector v: result(v) = a.q * (b.q * v + b.t) + a.t.
 */
export function se3Compose(a: SE3, b: SE3): SE3 {
  return {
    q: quatMul(a.q, b.q),
    t: v3Add(a.t, quatRotate(a.q, b.t)),
  };
}

export function se3Inverse(a: SE3): SE3 {
  const qi = quatConjugate(a.q);
  return { q: qi, t: v3Scale(quatRotate(qi, a.t), -1) };
}

export function se3Apply(a: SE3, v: Vec3): Vec3 {
  return v3Add(quatRotate(a.q, v), a.t);
}

export function se3FromMat4(m: Mat4): SE3 {
  // Trace-based quaternion extraction (Shoemake 1985).
  const [r00, r01, r02] = [m[0][0], m[0][1], m[0][2]];
  const [r10, r11, r12] = [m[1][0], m[1][1], m[1][2]];
  const [r20, r21, r22] = [m[2][0], m[2][1], m[2][2]];
  const tr = r00 + r11 + r22;
  let q: Quat;
  if (tr > 0) {
    const s = 0.5 / Math.sqrt(tr + 1.0);
    q = [0.25 / s, (r21 - r12) * s, (r02 - r20) * s, (r10 - r01) * s];
  } else if (r00 > r11 && r00 > r22) {
    const s = 2.0 * Math.sqrt(1.0 + r00 - r11 - r22);
    q = [(r21 - r12) / s, 0.25 * s, (r01 + r10) / s, (r02 + r20) / s];
  } else if (r11 > r22) {
    const s = 2.0 * Math.sqrt(1.0 + r11 - r00 - r22);
    q = [(r02 - r20) / s, (r01 + r10) / s, 0.25 * s, (r12 + r21) / s];
  } else {
    const s = 2.0 * Math.sqrt(1.0 + r22 - r00 - r11);
    q = [(r10 - r01) / s, (r02 + r20) / s, (r12 + r21) / s, 0.25 * s];
  }
  return { q: quatNormalize(q), t: [m[0][3], m[1][3], m[2][3]] };
}

export function se3ToMat4(a: SE3): Mat4 {
  const r = quatToMat3(a.q);
  const t = a.t;
  return [
    [r[0][0], r[0][1], r[0][2], t[0]],
    [r[1][0], r[1][1], r[1][2], t[1]],
    [r[2][0], r[2][1], r[2][2], t[2]],
    [0, 0, 0, 1],
  ];
}

/**
 * Pure translation along a vector.
 */
export function trans(t: Vec3): SE3 {
  return { q: QUAT_IDENTITY, t };
}

/**
 * Pure rotation about a unit axis through the origin.
 */
export function rot(axis: Vec3, angle: number): SE3 {
  return { q: quatFromAxisAngle(axis, angle), t: [0, 0, 0] };
}
