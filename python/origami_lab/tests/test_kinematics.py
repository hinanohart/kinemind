"""Forward kinematics tests: flat strip, accordion fold, FK consistency."""

from __future__ import annotations

import math

import numpy as np
import pytest

from origami_lab.kinematics import forward_kinematics, forward_kinematics_full
from origami_lab.strip import (
    StripConfig,
    StripState,
    flat_state,
    make_uniform_strip,
)


def test_flat_strip_positions_along_x() -> None:
    """For a flat strip with uniform cell length, positions lie along +X."""
    n = 5
    config = make_uniform_strip(n, cell_length=1.0)
    state = flat_state(config)
    positions, quats = forward_kinematics(config, state)
    # cell i should be at (i, 0, 0)
    for i in range(n):
        assert np.allclose(positions[i], [float(i), 0.0, 0.0], atol=1e-12), (
            f"cell {i}: expected [{i}, 0, 0], got {positions[i]}"
        )


def test_flat_strip_identity_quaternions() -> None:
    """Flat strip should yield identity quaternions for all cells."""
    config = make_uniform_strip(4, cell_length=1.0)
    state = flat_state(config)
    _, quats = forward_kinematics(config, state)
    identity = np.array([1.0, 0.0, 0.0, 0.0])
    for i in range(4):
        # Allow sign flip.
        q = quats[i]
        assert np.allclose(q, identity, atol=1e-12) or np.allclose(q, -identity, atol=1e-12)


def test_cell_0_at_origin() -> None:
    """Cell 0 is always at the world origin regardless of state."""
    config = make_uniform_strip(6, cell_length=2.0)
    state = StripState(thetas=(0.3, -0.5, 0.8, -0.2, 1.1))
    positions, _ = forward_kinematics(config, state)
    assert np.allclose(positions[0], np.zeros(3), atol=1e-12)


def test_accordion_fold_returns_home() -> None:
    """Strip with all hinges = pi should fold back on itself.

    For n=3 cells, thetas = [pi, pi]: cell 2 should be at or near origin.
    Each cell of length L with theta=pi folds 180° back.
    """
    config = make_uniform_strip(3, cell_length=1.0)
    state = StripState(thetas=(math.pi, math.pi))
    positions, _ = forward_kinematics(config, state)
    # cell 0 at origin, cell 1 at (1, 0, 0), cell 2 should be at (0, 0, 0)
    assert np.allclose(positions[0], [0.0, 0.0, 0.0], atol=1e-9)
    assert np.allclose(positions[1], [1.0, 0.0, 0.0], atol=1e-9)
    assert np.allclose(positions[2], [0.0, 0.0, 0.0], atol=1e-9)


def test_single_90deg_fold() -> None:
    """n=2 cells, theta=pi/2: cell 1 should turn +90 deg about Y at x=L."""
    L = 1.5
    config = make_uniform_strip(2, cell_length=L)
    state = StripState(thetas=(math.pi / 2,))
    positions, quats = forward_kinematics(config, state)
    # Cell 0: origin.
    assert np.allclose(positions[0], [0.0, 0.0, 0.0], atol=1e-12)
    # Cell 1: translate by L along x (that IS the position of cell 1).
    assert np.allclose(positions[1], [L, 0.0, 0.0], atol=1e-12)


def test_shapes() -> None:
    """forward_kinematics returns correct array shapes."""
    n = 8
    config = make_uniform_strip(n, cell_length=1.0)
    state = StripState(thetas=tuple(0.1 * i for i in range(n - 1)))
    positions, quats = forward_kinematics(config, state)
    assert positions.shape == (n, 3)
    assert quats.shape == (n, 4)


def test_wrong_state_length_raises() -> None:
    """forward_kinematics should raise ValueError on wrong state length."""
    config = make_uniform_strip(4)
    state = StripState(thetas=(0.0,))  # expected 3 hinges
    with pytest.raises(ValueError):
        forward_kinematics(config, state)


def test_full_vs_simple_parity() -> None:
    """forward_kinematics and forward_kinematics_full must agree on positions/quats."""
    config = make_uniform_strip(6, cell_length=1.2)
    state = StripState(thetas=(0.1, -0.2, 0.3, -0.4, 0.5))
    pos1, q1 = forward_kinematics(config, state)
    result = forward_kinematics_full(config, state)
    assert np.allclose(pos1, result.positions, atol=1e-12)
    # Quaternions may differ by sign.
    for i in range(6):
        assert (
            np.allclose(q1[i], result.quats[i], atol=1e-12)
            or np.allclose(q1[i], -result.quats[i], atol=1e-12)
        )


def test_non_uniform_cell_lengths() -> None:
    """Non-uniform cell lengths should propagate correctly in flat state."""
    config = StripConfig(
        n_cells=3,
        cell_lengths=(1.0, 2.0, 3.0),
    )
    state = flat_state(config)
    positions, _ = forward_kinematics(config, state)
    # Flat: positions at cumulative offsets [0, 1, 3].
    assert np.allclose(positions[0], [0.0, 0.0, 0.0], atol=1e-12)
    assert np.allclose(positions[1], [1.0, 0.0, 0.0], atol=1e-12)
    assert np.allclose(positions[2], [3.0, 0.0, 0.0], atol=1e-12)
