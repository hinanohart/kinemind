"""Tree-graph kinematics tests: path graph parity and Y-tree."""

from __future__ import annotations

import math

import numpy as np
import pytest

from origami_lab.kinematics import forward_kinematics
from origami_lab.strip import StripState, make_uniform_strip
from origami_lab.tree import (
    TreeStrip,
    forward_kinematics_tree,
    path_graph_tree,
)


# ---------------------------------------------------------------------------
# path_graph_tree construction
# ---------------------------------------------------------------------------


def test_path_graph_tree_parents() -> None:
    """Parents of P_5 should be [None, 0, 1, 2, 3]."""
    tree = path_graph_tree(5)
    assert tree.parents == (None, 0, 1, 2, 3)


def test_path_graph_tree_edge_lengths_uniform() -> None:
    """Edge lengths should equal cell_length for all edges."""
    tree = path_graph_tree(5, cell_length=2.0)
    assert all(abs(L - 2.0) < 1e-15 for L in tree.edge_lengths)
    assert len(tree.edge_lengths) == 4


def test_path_graph_tree_rejects_invalid() -> None:
    """Invalid inputs should raise ValueError."""
    with pytest.raises(ValueError):
        path_graph_tree(1)
    with pytest.raises(ValueError):
        path_graph_tree(4, cell_length=0)
    with pytest.raises(ValueError):
        path_graph_tree(4, angle_max=4.0)


# ---------------------------------------------------------------------------
# forward_kinematics_tree — path graph backward compatibility
# ---------------------------------------------------------------------------


def test_path_graph_flat_matches_strip_positions_atol_1e15() -> None:
    """Flat path graph tree must match strip forward kinematics positions at atol=1e-15."""
    n = 8
    tree = path_graph_tree(n, cell_length=1.0)
    thetas = [0.0] * (n - 1)
    tree_result = forward_kinematics_tree(tree, thetas)

    config = make_uniform_strip(n, cell_length=1.0)
    state = StripState(thetas=tuple(0.0 for _ in range(config.n_hinges)))
    positions_strip, _ = forward_kinematics(config, state)

    assert np.allclose(tree_result.positions, positions_strip, atol=1e-15), (
        f"Max diff = {np.abs(tree_result.positions - positions_strip).max():.2e}"
    )


def test_path_graph_nontrivial_matches_strip_positions_atol_1e15() -> None:
    """Non-flat path graph tree must match strip forward kinematics at atol=1e-15."""
    n = 8
    thetas = (0.1, 0.2, -0.3, 0.4, -0.5, 0.6, -0.7)
    tree = path_graph_tree(n, cell_length=1.0)
    tree_result = forward_kinematics_tree(tree, thetas)

    config = make_uniform_strip(n, cell_length=1.0)
    state = StripState(thetas=thetas)
    positions_strip, _ = forward_kinematics(config, state)

    assert np.allclose(tree_result.positions, positions_strip, atol=1e-15), (
        f"Max diff = {np.abs(tree_result.positions - positions_strip).max():.2e}"
    )


def test_forward_kinematics_tree_root_at_origin() -> None:
    """Root node (0) must always be at world origin."""
    tree = path_graph_tree(6, cell_length=1.5)
    thetas = [0.3, -0.1, 0.5, -0.2, 0.4]
    result = forward_kinematics_tree(tree, thetas)
    assert np.allclose(result.positions[0], np.zeros(3), atol=1e-15)


def test_forward_kinematics_tree_wrong_thetas_length() -> None:
    """Mismatched thetas length should raise ValueError."""
    tree = path_graph_tree(5)
    with pytest.raises(ValueError, match="expected 4 hinge angles"):
        forward_kinematics_tree(tree, [0.0, 0.0])
    with pytest.raises(ValueError, match="expected 4 hinge angles"):
        forward_kinematics_tree(tree, [0.0] * 5)


# ---------------------------------------------------------------------------
# Y-shaped tree (K_{1,3})
# ---------------------------------------------------------------------------


def _make_y_tree() -> TreeStrip:
    """Root (0) with 3 children (1, 2, 3), each at unit edge length."""
    return TreeStrip(
        n_nodes=4,
        parents=(None, 0, 0, 0),
        edge_lengths=(1.0, 1.0, 1.0),
        angle_max=math.pi,
    )


def test_y_tree_flat_children_at_1_0_0() -> None:
    """All children of root at flat angles should be at [1, 0, 0]."""
    tree = _make_y_tree()
    result = forward_kinematics_tree(tree, [0.0, 0.0, 0.0])
    for c in range(1, 4):
        assert np.allclose(result.positions[c], [1.0, 0.0, 0.0], atol=1e-15), (
            f"Child {c} position {result.positions[c]} != [1,0,0]"
        )


def test_y_tree_nontrivial_orientations_differ() -> None:
    """Non-zero hinge angles should produce different child frame orientations."""
    tree = _make_y_tree()
    thetas = [0.3, -0.5, 1.0]
    result = forward_kinematics_tree(tree, thetas)
    # All positions at [1,0,0] (hinge acts on orientation, not position).
    for c in range(1, 4):
        assert np.allclose(result.positions[c], [1.0, 0.0, 0.0], atol=1e-15)
    # Frames (orientations) must differ between children with different thetas.
    q1 = result.nodes[1].frame.q
    q2 = result.nodes[2].frame.q
    assert not np.allclose(q1, q2, atol=1e-9), "Children with different thetas must differ"


def test_y_tree_all_positions_finite() -> None:
    """All positions in a non-trivial Y-tree should be finite."""
    tree = _make_y_tree()
    result = forward_kinematics_tree(tree, [0.3, -0.5, 1.0])
    assert np.all(np.isfinite(result.positions))
