"""SAT collision detection tests: Python implementation and TS parity."""

from __future__ import annotations

import math

import numpy as np
import pytest

from origami_lab.collision import (
    SelfIntersection,
    detect_self_intersection_sat,
    quad_quad_overlap,
)
from origami_lab.kinematics import forward_kinematics_full
from origami_lab.strip import StripState, make_uniform_strip


# ---------------------------------------------------------------------------
# quad_quad_overlap unit tests
# ---------------------------------------------------------------------------


def test_non_overlapping_coplanar_quads() -> None:
    """Quads separated in X return None."""
    qa = np.array([[0, 0, 0], [1, 0, 0], [1, 1, 0], [0, 1, 0]], dtype=np.float64)
    qb = np.array([[2, 0, 0], [3, 0, 0], [3, 1, 0], [2, 1, 0]], dtype=np.float64)
    assert quad_quad_overlap(qa, qb) is None


def test_overlapping_coplanar_quads() -> None:
    """Overlapping coplanar quads return positive penetration."""
    qa = np.array([[0, 0, 0], [1, 0, 0], [1, 1, 0], [0, 1, 0]], dtype=np.float64)
    qb = np.array([[0.5, 0, 0], [1.5, 0, 0], [1.5, 1, 0], [0.5, 1, 0]], dtype=np.float64)
    result = quad_quad_overlap(qa, qb)
    assert result is not None
    point, penetration = result
    assert penetration > 0
    assert point.shape == (3,)


def test_touching_edge_returns_none() -> None:
    """Quads touching at edge (penetration < tol) should return None."""
    qa = np.array([[0, 0, 0], [1, 0, 0], [1, 1, 0], [0, 1, 0]], dtype=np.float64)
    qb = np.array([[1, 0, 0], [2, 0, 0], [2, 1, 0], [1, 1, 0]], dtype=np.float64)
    assert quad_quad_overlap(qa, qb, tol=1e-9) is None


def test_3d_non_overlapping_quads_return_none() -> None:
    """Quads at z=0 and z=2 are separated by face-normal axis."""
    qa = np.array([[0, 0, 0], [1, 0, 0], [1, 1, 0], [0, 1, 0]], dtype=np.float64)
    qb = np.array([[0, 0, 2], [1, 0, 2], [1, 1, 2], [0, 1, 2]], dtype=np.float64)
    assert quad_quad_overlap(qa, qb) is None


def test_3d_xz_overlapping_quads() -> None:
    """Coplanar quads in XZ plane overlapping in X return non-null."""
    qa = np.array([[0, 0, 0], [1, 0, 0], [1, 0, 1], [0, 0, 1]], dtype=np.float64)
    qb = np.array([[0.5, 0, 0], [1.5, 0, 0], [1.5, 0, 1], [0.5, 0, 1]], dtype=np.float64)
    result = quad_quad_overlap(qa, qb)
    assert result is not None
    _, penetration = result
    assert penetration > 0


def test_invalid_quad_shape_raises() -> None:
    """Non-4-vertex input should raise ValueError."""
    qa = np.zeros((3, 3))  # triangle, not quad
    qb = np.zeros((4, 3))
    with pytest.raises(ValueError):
        quad_quad_overlap(qa, qb)


# ---------------------------------------------------------------------------
# detect_self_intersection_sat integration tests
# ---------------------------------------------------------------------------


def test_flat_strip_no_intersection() -> None:
    """Flat strip has no self-intersections."""
    config = make_uniform_strip(8, cell_length=1.0)
    state = StripState(thetas=tuple(0.0 for _ in range(config.n_hinges)))
    result = forward_kinematics_full(config, state)
    hits = detect_self_intersection_sat(config, result)
    assert hits == []


def test_accordion_fold_detects_overlap() -> None:
    """N=4 strip with theta=(pi,pi,0) → cells 0 and 2 overlap."""
    config = make_uniform_strip(4, cell_length=1.0)
    state = StripState(thetas=(math.pi, math.pi, 0.0))
    result = forward_kinematics_full(config, state)
    hits = detect_self_intersection_sat(config, result)
    assert len(hits) > 0
    # All hits must have j > i + 1.
    for hit in hits:
        assert hit.j > hit.i + 1
    # Cells 0 and 2 must be in the list.
    assert any(h.i == 0 and h.j == 2 for h in hits), (
        f"Expected (0,2) in hits, got: {[(h.i, h.j) for h in hits]}"
    )


def test_self_intersection_type() -> None:
    """Detected hits should be SelfIntersection instances."""
    config = make_uniform_strip(4)
    state = StripState(thetas=(math.pi, math.pi, 0.0))
    result = forward_kinematics_full(config, state)
    hits = detect_self_intersection_sat(config, result)
    for hit in hits:
        assert isinstance(hit, SelfIntersection)
        assert hit.penetration > 0
        assert hit.point.shape == (3,)
        assert np.all(np.isfinite(hit.point))
