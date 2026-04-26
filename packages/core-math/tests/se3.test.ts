import fc from "fast-check";
import { describe, expect, it } from "vitest";
import {
  EPS,
  QUAT_IDENTITY,
  SE3_IDENTITY,
  quatFromAxisAngle,
  quatMul,
  quatNormalize,
  quatRotate,
  quatToMat3,
  rot,
  se3Apply,
  se3Compose,
  se3Inverse,
  trans,
  v3Cross,
  v3Dot,
  v3Norm,
  v3Sub,
} from "../src/se3.js";

const arbAngle = fc.double({ min: -Math.PI, max: Math.PI, noNaN: true });
const arbAxis = fc
  .tuple(
    fc.double({ min: -1, max: 1, noNaN: true }),
    fc.double({ min: -1, max: 1, noNaN: true }),
    fc.double({ min: -1, max: 1, noNaN: true }),
  )
  .filter(([x, y, z]) => Math.hypot(x, y, z) > 0.1);
const arbVec3 = fc.tuple(
  fc.double({ min: -10, max: 10, noNaN: true }),
  fc.double({ min: -10, max: 10, noNaN: true }),
  fc.double({ min: -10, max: 10, noNaN: true }),
);

const closeTo = (a: number, b: number, tol = 1e-9) => Math.abs(a - b) <= tol;
const vecClose = (a: readonly number[], b: readonly number[], tol = 1e-9) =>
  a.length === b.length && a.every((x, i) => closeTo(x, b[i] ?? Number.NaN, tol));

describe("quaternion algebra", () => {
  it("identity quaternion does nothing", () => {
    const v = [1, 2, 3] as const;
    const out = quatRotate(QUAT_IDENTITY, v);
    expect(vecClose(out, v)).toBe(true);
  });

  it("axis-angle: rotating axis by any angle leaves it unchanged", () => {
    fc.assert(
      fc.property(arbAxis, arbAngle, (axis, angle) => {
        const norm = Math.hypot(...axis);
        const unit = [axis[0] / norm, axis[1] / norm, axis[2] / norm] as const;
        const q = quatFromAxisAngle(axis, angle);
        const rotated = quatRotate(q, unit);
        return vecClose(rotated, unit, 1e-7);
      }),
      { numRuns: 100 },
    );
  });

  it("composition is associative", () => {
    fc.assert(
      fc.property(
        arbAxis,
        arbAngle,
        arbAxis,
        arbAngle,
        arbAxis,
        arbAngle,
        (a1, t1, a2, t2, a3, t3) => {
          const q1 = quatFromAxisAngle(a1, t1);
          const q2 = quatFromAxisAngle(a2, t2);
          const q3 = quatFromAxisAngle(a3, t3);
          const left = quatMul(quatMul(q1, q2), q3);
          const right = quatMul(q1, quatMul(q2, q3));
          return left.every((x, i) => closeTo(x, right[i] ?? Number.NaN, 1e-7));
        },
      ),
      { numRuns: 50 },
    );
  });

  it("rotation matrix is orthogonal", () => {
    fc.assert(
      fc.property(arbAxis, arbAngle, (axis, angle) => {
        const q = quatFromAxisAngle(axis, angle);
        const R = quatToMat3(q);
        const x: [number, number, number] = [R[0][0], R[1][0], R[2][0]];
        const y: [number, number, number] = [R[0][1], R[1][1], R[2][1]];
        const z: [number, number, number] = [R[0][2], R[1][2], R[2][2]];
        const detPositive = v3Dot(v3Cross(x, y), z) > 0;
        return (
          closeTo(v3Norm(x), 1, 1e-7) &&
          closeTo(v3Norm(y), 1, 1e-7) &&
          closeTo(v3Norm(z), 1, 1e-7) &&
          closeTo(v3Dot(x, y), 0, 1e-7) &&
          detPositive
        );
      }),
      { numRuns: 50 },
    );
  });

  it("normalization is idempotent", () => {
    const q = quatFromAxisAngle([1, 1, 1], 1.0);
    const a = quatNormalize(q);
    const b = quatNormalize(a);
    expect(vecClose(a, b, EPS)).toBe(true);
  });
});

describe("SE(3) group axioms", () => {
  it("identity is a left and right identity", () => {
    const T = se3Compose(rot([0, 0, 1], 0.7), trans([1, 2, 3]));
    const left = se3Compose(SE3_IDENTITY, T);
    const right = se3Compose(T, SE3_IDENTITY);
    expect(vecClose(left.q, T.q)).toBe(true);
    expect(vecClose(left.t, T.t)).toBe(true);
    expect(vecClose(right.q, T.q)).toBe(true);
    expect(vecClose(right.t, T.t)).toBe(true);
  });

  it("inverse undoes composition", () => {
    fc.assert(
      fc.property(arbAxis, arbAngle, arbVec3, (axis, angle, t) => {
        const T = se3Compose(rot(axis, angle), trans(t));
        const Tinv = se3Inverse(T);
        const round = se3Compose(T, Tinv);
        return (
          vecClose(round.q, QUAT_IDENTITY, 1e-7) ||
          // antipodal quaternion equivalence
          vecClose(
            round.q,
            [-QUAT_IDENTITY[0], -QUAT_IDENTITY[1], -QUAT_IDENTITY[2], -QUAT_IDENTITY[3]],
            1e-7,
          )
        );
      }),
      { numRuns: 50 },
    );
  });

  it("apply is linear in translation", () => {
    fc.assert(
      fc.property(arbVec3, arbVec3, (t, v) => {
        const T = trans(t);
        const out = se3Apply(T, v);
        return vecClose(out, [v[0] + t[0], v[1] + t[1], v[2] + t[2]]);
      }),
    );
  });

  it("rotation about Y by pi flips X to -X", () => {
    const T = rot([0, 1, 0], Math.PI);
    const out = se3Apply(T, [1, 0, 0]);
    expect(vecClose(out, [-1, 0, 0], 1e-9)).toBe(true);
  });

  it("composition order: rot(pi/2 about z) then trans(1,0,0) maps (1,0,0) -> rotated then translated", () => {
    const T = se3Compose(rot([0, 0, 1], Math.PI / 2), trans([1, 0, 0]));
    // Apply: first rotate (1,0,0) -> (0,1,0), then translate by R*(1,0,0)=(0,1,0).
    // se3Apply(T, v) = R v + t = R*[1,0,0] + R*[1,0,0] = (0,1,0) + (0,1,0) = (0,2,0).
    const out = se3Apply(T, [1, 0, 0]);
    expect(vecClose(out, [0, 2, 0], 1e-9)).toBe(true);
  });
});

describe("vector helpers", () => {
  it("cross product is anticommutative", () => {
    const a: [number, number, number] = [1, 2, 3];
    const b: [number, number, number] = [4, 5, 6];
    const ab = v3Cross(a, b);
    const ba = v3Cross(b, a);
    expect(
      vecClose(
        ab,
        ba.map((x) => -x),
      ),
    ).toBe(true);
  });

  it("v3Sub matches subtraction", () => {
    expect(vecClose(v3Sub([4, 5, 6], [1, 2, 3]), [3, 3, 3])).toBe(true);
  });
});
