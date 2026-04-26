"""SE(3) axiom tests: identity, inverse, associativity.

Includes hypothesis-based property tests for the group axioms.
"""

from __future__ import annotations

import numpy as np
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st
from hypothesis.extra.numpy import arrays

from origami_lab.se3 import (
    SE3,
    EPS,
    quat_conjugate,
    quat_from_axis_angle,
    quat_mul,
    quat_normalize,
    quat_rotate,
    quat_to_mat3,
    rot,
    se3_apply,
    se3_compose,
    se3_identity,
    se3_inverse,
    trans,
    mat3_to_quat,
)

# ---------- helpers ----------

def _random_se3(rng: np.random.Generator) -> SE3:
    axis = rng.standard_normal(3)
    axis /= np.linalg.norm(axis) + 1e-15
    angle = rng.uniform(-np.pi, np.pi)
    t = rng.standard_normal(3)
    return SE3(q=quat_from_axis_angle(axis, angle), t=t)


def _assert_quat_close(q1: np.ndarray, q2: np.ndarray, atol: float = 1e-9) -> None:
    """Assert q1 ≈ q2 up to global sign flip."""
    assert np.allclose(q1, q2, atol=atol) or np.allclose(q1, -q2, atol=atol), (
        f"Quaternions differ: {q1} vs {q2}"
    )


def _assert_se3_close(a: SE3, b: SE3, atol: float = 1e-9) -> None:
    _assert_quat_close(a.q, b.q, atol=atol)
    assert np.allclose(a.t, b.t, atol=atol), f"Translations differ: {a.t} vs {b.t}"


# ---------- unit tests ----------

def test_se3_identity_compose_left() -> None:
    """I @ T == T."""
    rng = np.random.default_rng(0)
    T = _random_se3(rng)
    result = se3_compose(se3_identity(), T)
    _assert_se3_close(result, T)


def test_se3_identity_compose_right() -> None:
    """T @ I == T."""
    rng = np.random.default_rng(1)
    T = _random_se3(rng)
    result = se3_compose(T, se3_identity())
    _assert_se3_close(result, T)


def test_se3_inverse_left() -> None:
    """T^{-1} @ T == I."""
    rng = np.random.default_rng(2)
    T = _random_se3(rng)
    result = se3_compose(se3_inverse(T), T)
    _assert_se3_close(result, se3_identity())


def test_se3_inverse_right() -> None:
    """T @ T^{-1} == I."""
    rng = np.random.default_rng(3)
    T = _random_se3(rng)
    result = se3_compose(T, se3_inverse(T))
    _assert_se3_close(result, se3_identity())


def test_se3_associativity() -> None:
    """(A @ B) @ C == A @ (B @ C)."""
    rng = np.random.default_rng(4)
    A = _random_se3(rng)
    B = _random_se3(rng)
    C = _random_se3(rng)
    lhs = se3_compose(se3_compose(A, B), C)
    rhs = se3_compose(A, se3_compose(B, C))
    _assert_se3_close(lhs, rhs)


def test_se3_apply_origin() -> None:
    """se3_apply(T, [0,0,0]) == T.t."""
    rng = np.random.default_rng(5)
    T = _random_se3(rng)
    result = se3_apply(T, np.zeros(3))
    assert np.allclose(result, T.t, atol=1e-12)


def test_quat_from_axis_angle_zero_angle() -> None:
    """Rotation by 0 should give identity quaternion."""
    q = quat_from_axis_angle(np.array([0.0, 1.0, 0.0]), 0.0)
    assert np.allclose(q, np.array([1.0, 0.0, 0.0, 0.0]), atol=1e-12)


def test_quat_from_axis_angle_zero_axis_raises() -> None:
    """Zero axis should raise ValueError."""
    with pytest.raises(ValueError):
        quat_from_axis_angle(np.zeros(3), 1.0)


def test_quat_mul_identity() -> None:
    """q * I == q."""
    rng = np.random.default_rng(6)
    axis = rng.standard_normal(3)
    axis /= np.linalg.norm(axis)
    q = quat_from_axis_angle(axis, 1.0)
    I = np.array([1.0, 0.0, 0.0, 0.0])
    assert np.allclose(quat_mul(q, I), q, atol=1e-12)
    assert np.allclose(quat_mul(I, q), q, atol=1e-12)


def test_quat_conjugate_inverse() -> None:
    """q * conj(q) == identity."""
    q = quat_from_axis_angle(np.array([0.0, 0.0, 1.0]), np.pi / 4)
    prod = quat_mul(q, quat_conjugate(q))
    assert np.allclose(prod, np.array([1.0, 0.0, 0.0, 0.0]), atol=1e-12)


def test_quat_rotate_preserves_length() -> None:
    """Rotation should preserve vector norm."""
    rng = np.random.default_rng(7)
    q = quat_normalize(rng.standard_normal(4))
    v = rng.standard_normal(3)
    vr = quat_rotate(q, v)
    assert np.isclose(np.linalg.norm(vr), np.linalg.norm(v), atol=1e-12)


def test_quat_to_mat3_is_rotation() -> None:
    """R should be orthogonal with det = +1."""
    q = quat_from_axis_angle(np.array([1.0, 2.0, 3.0]) / np.sqrt(14), np.pi / 3)
    R = quat_to_mat3(q)
    assert np.allclose(R @ R.T, np.eye(3), atol=1e-12)
    assert np.isclose(np.linalg.det(R), 1.0, atol=1e-12)


def test_mat3_to_quat_roundtrip() -> None:
    """quat_to_mat3 and mat3_to_quat should be inverse operations."""
    q_orig = quat_from_axis_angle(np.array([0.0, 1.0, 0.0]), np.pi / 6)
    R = quat_to_mat3(q_orig)
    q_back = mat3_to_quat(R)
    _assert_quat_close(q_orig, q_back)


def test_trans_pure_translation() -> None:
    """trans(t).t == t and trans(t).q == identity."""
    t = np.array([1.0, 2.0, 3.0])
    T = trans(t)
    assert np.allclose(T.t, t, atol=1e-12)
    assert np.allclose(T.q, np.array([1.0, 0.0, 0.0, 0.0]), atol=1e-12)


def test_rot_pure_rotation() -> None:
    """rot(axis, angle).t == 0."""
    T = rot(np.array([0.0, 1.0, 0.0]), np.pi / 2)
    assert np.allclose(T.t, np.zeros(3), atol=1e-12)


# ---------- hypothesis property tests ----------

float_strat = st.floats(min_value=-10.0, max_value=10.0, allow_nan=False, allow_infinity=False)
angle_strat = st.floats(min_value=-np.pi, max_value=np.pi, allow_nan=False, allow_infinity=False)


def _make_se3_from_params(ax: np.ndarray, angle: float, t: np.ndarray) -> SE3:
    n = np.linalg.norm(ax)
    if n < 1e-7:
        ax = np.array([0.0, 0.0, 1.0])
    else:
        ax = ax / n
    return SE3(q=quat_from_axis_angle(ax, angle), t=t)


@given(
    ax=arrays(np.float64, (3,), elements=st.floats(-1.0, 1.0, allow_nan=False, allow_infinity=False)),
    angle=angle_strat,
    t=arrays(np.float64, (3,), elements=float_strat),
)
@settings(max_examples=100)
def test_property_identity_left(
    ax: np.ndarray, angle: float, t: np.ndarray
) -> None:
    """Property: I @ T == T for arbitrary T."""
    ax = np.where(np.isfinite(ax), ax, 0.0)
    ax = ax.copy()
    T = _make_se3_from_params(ax, angle, t)
    result = se3_compose(se3_identity(), T)
    _assert_se3_close(result, T, atol=1e-9)


@given(
    ax=arrays(np.float64, (3,), elements=st.floats(-1.0, 1.0, allow_nan=False, allow_infinity=False)),
    angle=angle_strat,
    t=arrays(np.float64, (3,), elements=float_strat),
)
@settings(max_examples=100)
def test_property_inverse(
    ax: np.ndarray, angle: float, t: np.ndarray
) -> None:
    """Property: T^{-1} @ T == I for arbitrary T."""
    ax = np.where(np.isfinite(ax), ax, 0.0)
    ax = ax.copy()
    T = _make_se3_from_params(ax, angle, t)
    result = se3_compose(se3_inverse(T), T)
    _assert_se3_close(result, se3_identity(), atol=1e-9)


@given(
    ax1=arrays(np.float64, (3,), elements=st.floats(-1.0, 1.0, allow_nan=False, allow_infinity=False)),
    a1=angle_strat,
    t1=arrays(np.float64, (3,), elements=float_strat),
    ax2=arrays(np.float64, (3,), elements=st.floats(-1.0, 1.0, allow_nan=False, allow_infinity=False)),
    a2=angle_strat,
    t2=arrays(np.float64, (3,), elements=float_strat),
    ax3=arrays(np.float64, (3,), elements=st.floats(-1.0, 1.0, allow_nan=False, allow_infinity=False)),
    a3=angle_strat,
    t3=arrays(np.float64, (3,), elements=float_strat),
)
@settings(max_examples=50)
def test_property_associativity(
    ax1: np.ndarray, a1: float, t1: np.ndarray,
    ax2: np.ndarray, a2: float, t2: np.ndarray,
    ax3: np.ndarray, a3: float, t3: np.ndarray,
) -> None:
    """Property: (A @ B) @ C == A @ (B @ C)."""
    for ax in (ax1, ax2, ax3):
        ax[:] = np.where(np.isfinite(ax), ax, 0.0)
    A = _make_se3_from_params(ax1, a1, t1)
    B = _make_se3_from_params(ax2, a2, t2)
    C = _make_se3_from_params(ax3, a3, t3)
    lhs = se3_compose(se3_compose(A, B), C)
    rhs = se3_compose(A, se3_compose(B, C))
    _assert_se3_close(lhs, rhs, atol=1e-9)
