"""SE(3) Lie group primitives for rigid body kinematics.

Conventions:
    - Quaternion order: (w, x, y, z) with w as the real part.
    - Rotation acts on column vectors: v' = R v.
    - Composition reads left-to-right: se3_compose(a, b) means "apply a first".
    - All angles are radians.

Numerically mirrors TypeScript ``@kinemind/core-math`` se3.ts line-by-line.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING

import numpy as np
from numpy.typing import NDArray

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)

EPS: float = 1e-12

# Type aliases
Vec3 = NDArray[np.float64]   # shape (3,)
Quat = NDArray[np.float64]   # shape (4,)  (w, x, y, z)
Mat3 = NDArray[np.float64]   # shape (3, 3)
Mat4 = NDArray[np.float64]   # shape (4, 4)


# -------------------------  quaternion helpers  -------------------------

QUAT_IDENTITY: Quat = np.array([1.0, 0.0, 0.0, 0.0], dtype=np.float64)


def quat_from_axis_angle(axis: Vec3, angle: float) -> Quat:
    """Construct unit quaternion (w,x,y,z) from axis-angle.

    Args:
        axis: 3-vector rotation axis (need not be unit length).
        angle: rotation angle in radians.

    Returns:
        Unit quaternion ndarray of shape (4,).

    Raises:
        ValueError: if axis is zero-length.
    """
    a = np.asarray(axis, dtype=np.float64)
    n = float(np.linalg.norm(a))
    if n < EPS:
        raise ValueError("quat_from_axis_angle: zero-length axis")
    a = a / n
    half = angle * 0.5
    s = np.sin(half)
    return np.array([np.cos(half), a[0] * s, a[1] * s, a[2] * s], dtype=np.float64)


def quat_mul(q1: Quat, q2: Quat) -> Quat:
    """Hamilton product of two unit quaternions.

    Args:
        q1: quaternion (w,x,y,z) shape (4,).
        q2: quaternion (w,x,y,z) shape (4,).

    Returns:
        Product quaternion (w,x,y,z) shape (4,).
    """
    q1 = np.asarray(q1, dtype=np.float64)
    q2 = np.asarray(q2, dtype=np.float64)
    w1, x1, y1, z1 = q1
    w2, x2, y2, z2 = q2
    return np.array(
        [
            w1 * w2 - x1 * x2 - y1 * y2 - z1 * z2,
            w1 * x2 + x1 * w2 + y1 * z2 - z1 * y2,
            w1 * y2 - x1 * z2 + y1 * w2 + z1 * x2,
            w1 * z2 + x1 * y2 - y1 * x2 + z1 * w2,
        ],
        dtype=np.float64,
    )


def quat_conjugate(q: Quat) -> Quat:
    """Return the conjugate (w, -x, -y, -z).

    Args:
        q: unit quaternion shape (4,).

    Returns:
        Conjugate quaternion shape (4,).
    """
    q = np.asarray(q, dtype=np.float64)
    return np.array([q[0], -q[1], -q[2], -q[3]], dtype=np.float64)


def quat_normalize(q: Quat) -> Quat:
    """Normalize a quaternion to unit length.

    Args:
        q: quaternion shape (4,).

    Returns:
        Unit quaternion shape (4,).

    Raises:
        ValueError: if q is a zero quaternion.
    """
    q = np.asarray(q, dtype=np.float64)
    n = float(np.linalg.norm(q))
    if n < EPS:
        raise ValueError("quat_normalize: zero quaternion")
    return q / n


def quat_rotate(q: Quat, v: Vec3) -> Vec3:
    """Rotate vector v by unit quaternion q: v' = q * (0,v) * q^{-1}.

    Args:
        q: unit quaternion (w,x,y,z) shape (4,).
        v: 3-vector shape (3,).

    Returns:
        Rotated 3-vector shape (3,).
    """
    q = np.asarray(q, dtype=np.float64)
    v = np.asarray(v, dtype=np.float64)
    w, x, y, z = q
    vx, vy, vz = v
    # Rodrigues-like expansion for efficiency, identical to TS implementation.
    tx = 2.0 * (y * vz - z * vy)
    ty = 2.0 * (z * vx - x * vz)
    tz = 2.0 * (x * vy - y * vx)
    return np.array(
        [
            vx + w * tx + (y * tz - z * ty),
            vy + w * ty + (z * tx - x * tz),
            vz + w * tz + (x * ty - y * tx),
        ],
        dtype=np.float64,
    )


def quat_to_mat3(q: Quat) -> Mat3:
    """Convert unit quaternion to 3x3 rotation matrix (row-major).

    Args:
        q: unit quaternion (w,x,y,z) shape (4,).

    Returns:
        Rotation matrix shape (3,3).
    """
    q = np.asarray(q, dtype=np.float64)
    w, x, y, z = q
    xx = x * x
    yy = y * y
    zz = z * z
    xy = x * y
    xz = x * z
    yz = y * z
    wx = w * x
    wy = w * y
    wz = w * z
    return np.array(
        [
            [1 - 2 * (yy + zz), 2 * (xy - wz), 2 * (xz + wy)],
            [2 * (xy + wz), 1 - 2 * (xx + zz), 2 * (yz - wx)],
            [2 * (xz - wy), 2 * (yz + wx), 1 - 2 * (xx + yy)],
        ],
        dtype=np.float64,
    )


def mat3_to_quat(R: Mat3) -> Quat:
    """Convert 3x3 rotation matrix to unit quaternion (Shoemake 1985).

    Args:
        R: rotation matrix shape (3,3).

    Returns:
        Unit quaternion (w,x,y,z) shape (4,).
    """
    R = np.asarray(R, dtype=np.float64)
    r00, r01, r02 = R[0, 0], R[0, 1], R[0, 2]
    r10, r11, r12 = R[1, 0], R[1, 1], R[1, 2]
    r20, r21, r22 = R[2, 0], R[2, 1], R[2, 2]
    tr = r00 + r11 + r22
    if tr > 0:
        s = 0.5 / np.sqrt(tr + 1.0)
        q = np.array([0.25 / s, (r21 - r12) * s, (r02 - r20) * s, (r10 - r01) * s])
    elif r00 > r11 and r00 > r22:
        s = 2.0 * np.sqrt(1.0 + r00 - r11 - r22)
        q = np.array([(r21 - r12) / s, 0.25 * s, (r01 + r10) / s, (r02 + r20) / s])
    elif r11 > r22:
        s = 2.0 * np.sqrt(1.0 + r11 - r00 - r22)
        q = np.array([(r02 - r20) / s, (r01 + r10) / s, 0.25 * s, (r12 + r21) / s])
    else:
        s = 2.0 * np.sqrt(1.0 + r22 - r00 - r11)
        q = np.array([(r10 - r01) / s, (r02 + r20) / s, (r12 + r21) / s, 0.25 * s])
    return quat_normalize(q)


# -------------------------  SE(3)  -------------------------


@dataclass(frozen=True)
class SE3:
    """Rigid body transform: unit quaternion (w,x,y,z) + translation.

    Attributes:
        q: unit quaternion (w,x,y,z) ndarray shape (4,).
        t: translation vector ndarray shape (3,).
    """

    q: Quat
    t: Vec3

    def __post_init__(self) -> None:
        """Validate and convert to float64 arrays."""
        object.__setattr__(self, "q", np.asarray(self.q, dtype=np.float64))
        object.__setattr__(self, "t", np.asarray(self.t, dtype=np.float64))
        if self.q.shape != (4,):
            raise ValueError(f"SE3: q must have shape (4,), got {self.q.shape}")
        if self.t.shape != (3,):
            raise ValueError(f"SE3: t must have shape (3,), got {self.t.shape}")


def se3_identity() -> SE3:
    """Return the identity SE(3) transform.

    Returns:
        SE3 with identity quaternion and zero translation.
    """
    return SE3(q=QUAT_IDENTITY.copy(), t=np.zeros(3, dtype=np.float64))


def se3_compose(a: SE3, b: SE3) -> SE3:
    """Compose two transforms: result = a then b.

    The composition formula: result(v) = a.q * (b.q * v + b.t) + a.t.

    Args:
        a: first transform applied.
        b: second transform applied.

    Returns:
        Composed SE3 transform.
    """
    return SE3(
        q=quat_mul(a.q, b.q),
        t=a.t + quat_rotate(a.q, b.t),
    )


def se3_inverse(a: SE3) -> SE3:
    """Compute the inverse of an SE(3) transform.

    Args:
        a: SE3 transform.

    Returns:
        Inverse SE3 transform.
    """
    qi = quat_conjugate(a.q)
    return SE3(q=qi, t=-quat_rotate(qi, a.t))


def se3_apply(a: SE3, v: Vec3) -> Vec3:
    """Apply SE(3) transform to a 3-vector: v' = R*v + t.

    Args:
        a: SE3 transform.
        v: 3-vector shape (3,).

    Returns:
        Transformed 3-vector shape (3,).
    """
    v = np.asarray(v, dtype=np.float64)
    return quat_rotate(a.q, v) + a.t


def trans(t: Vec3) -> SE3:
    """Pure translation SE(3) transform.

    Args:
        t: translation vector shape (3,).

    Returns:
        SE3 with identity rotation and given translation.
    """
    return SE3(q=QUAT_IDENTITY.copy(), t=np.asarray(t, dtype=np.float64))


def rot(axis: Vec3, angle: float) -> SE3:
    """Pure rotation SE(3) transform.

    Args:
        axis: rotation axis shape (3,) (need not be unit).
        angle: rotation angle in radians.

    Returns:
        SE3 with given rotation and zero translation.
    """
    return SE3(
        q=quat_from_axis_angle(np.asarray(axis, dtype=np.float64), angle),
        t=np.zeros(3, dtype=np.float64),
    )


def se3_to_mat4(a: SE3) -> Mat4:
    """Convert SE3 to 4x4 homogeneous matrix.

    Args:
        a: SE3 transform.

    Returns:
        4x4 homogeneous matrix shape (4,4).
    """
    R = quat_to_mat3(a.q)
    M = np.eye(4, dtype=np.float64)
    M[:3, :3] = R
    M[:3, 3] = a.t
    return M


def se3_from_mat4(M: Mat4) -> SE3:
    """Extract SE3 from 4x4 homogeneous matrix (Shoemake 1985).

    Args:
        M: 4x4 homogeneous matrix shape (4,4).

    Returns:
        SE3 transform.
    """
    M = np.asarray(M, dtype=np.float64)
    q = mat3_to_quat(M[:3, :3])
    t = M[:3, 3].copy()
    return SE3(q=q, t=t)
