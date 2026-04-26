"""Tree-graph generalization of 1D origami strip kinematics.

A ``TreeStrip`` represents a rooted tree where each non-root node has
a parent connected by a revolute hinge joint.  A path graph P_N is a
special case with ``parents = [None, 0, 1, ..., N-2]``.

Forward kinematics is computed by DFS from the root (node 0), accumulating
SE(3) transforms along each parent→child edge.

Backward compatibility:
    ``forward_kinematics_tree(path_graph_tree(n, L), thetas)``
    produces bit-exact positions matching
    ``forward_kinematics(make_uniform_strip(n, L), state)`` at atol=1e-15.

Parity: matches TypeScript ``@kinemind/core-math`` tree.ts.
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass
from typing import Optional

import numpy as np
from numpy.typing import NDArray

from origami_lab.se3 import (
    SE3,
    Vec3,
    rot,
    se3_apply,
    se3_compose,
    se3_identity,
    trans,
)
from origami_lab.strip import CELL_Y_AXIS

logger = logging.getLogger(__name__)


# ---- Public types ----


@dataclass(frozen=True)
class TreeStrip:
    """Rooted tree of origami cells connected by revolute hinges.

    Attributes:
        n_nodes: Number of nodes (>= 2).
        parents: Length n_nodes; parents[0] must be None (root).
                 parents[i] is the parent index for non-root node i.
        edge_lengths: Length n_nodes - 1; edge length indexed by child node.
        hinge_axes: Optional per-edge hinge axis (defaults to [0,1,0]).
        angle_max: Hard limit on |theta_i| in radians.
    """

    n_nodes: int
    parents: tuple[Optional[int], ...]
    edge_lengths: tuple[float, ...]
    hinge_axes: Optional[tuple[NDArray[np.float64], ...]] = None
    angle_max: float = math.pi

    def __post_init__(self) -> None:
        """Validate geometry."""
        if not isinstance(self.n_nodes, int) or self.n_nodes < 2:
            raise ValueError(
                f"TreeStrip: n_nodes must be an integer >= 2 (got {self.n_nodes})"
            )
        if len(self.parents) != self.n_nodes:
            raise ValueError(
                f"TreeStrip: parents length {len(self.parents)} must equal n_nodes={self.n_nodes}"
            )
        if self.parents[0] is not None:
            raise ValueError("TreeStrip: parents[0] must be None (root node)")
        if len(self.edge_lengths) != self.n_nodes - 1:
            raise ValueError(
                f"TreeStrip: edge_lengths length {len(self.edge_lengths)} "
                f"must equal n_nodes-1={self.n_nodes - 1}"
            )
        for i, L in enumerate(self.edge_lengths):
            if not (math.isfinite(L) and L > 0):
                raise ValueError(
                    f"TreeStrip: edge_lengths[{i}] must be positive finite (got {L})"
                )
        if self.hinge_axes is not None and len(self.hinge_axes) != self.n_nodes - 1:
            raise ValueError(
                "TreeStrip: hinge_axes length must equal n_nodes - 1 when provided"
            )
        if not (math.isfinite(self.angle_max) and 0 < self.angle_max <= math.pi):
            raise ValueError(
                f"TreeStrip: angle_max must be in (0, pi] (got {self.angle_max})"
            )


@dataclass(frozen=True)
class TreeNodePose:
    """World-frame pose and position of a single tree node.

    Attributes:
        frame: SE3 pose of the node's local frame relative to world.
        position: Leading-edge midpoint position shape (3,).
    """

    frame: SE3
    position: NDArray[np.float64]  # shape (3,)


@dataclass(frozen=True)
class TreeKinematicsResult:
    """Output of forward_kinematics_tree.

    Attributes:
        nodes: Ordered list of TreeNodePose for each node.
        positions: (n_nodes, 3) array of node world positions.
    """

    nodes: tuple[TreeNodePose, ...]
    positions: NDArray[np.float64]  # shape (n_nodes, 3)


# ---- Public API ----


def path_graph_tree(
    n_nodes: int,
    cell_length: float = 1.0,
    angle_max: float = math.pi,
) -> TreeStrip:
    """Construct a path-graph TreeStrip with uniform edge lengths.

    Path graph: node 0 is root, node i's parent is i-1 for i > 0.

    Args:
        n_nodes: Number of nodes (>= 2).
        cell_length: Uniform edge length (default 1.0).
        angle_max: Hinge angle limit in radians (default pi).

    Returns:
        TreeStrip representing the path graph P_{n_nodes}.

    Raises:
        ValueError: if parameters are invalid.
    """
    if not isinstance(n_nodes, int) or n_nodes < 2:
        raise ValueError(
            f"path_graph_tree: n_nodes must be an integer >= 2 (got {n_nodes})"
        )
    if not (math.isfinite(cell_length) and cell_length > 0):
        raise ValueError(
            f"path_graph_tree: cell_length must be positive finite (got {cell_length})"
        )
    if not (math.isfinite(angle_max) and 0 < angle_max <= math.pi):
        raise ValueError(
            f"path_graph_tree: angle_max must be in (0, pi] (got {angle_max})"
        )
    parents: tuple[Optional[int], ...] = (None,) + tuple(range(n_nodes - 1))
    edge_lengths: tuple[float, ...] = tuple(cell_length for _ in range(n_nodes - 1))
    return TreeStrip(
        n_nodes=n_nodes,
        parents=parents,
        edge_lengths=edge_lengths,
        angle_max=angle_max,
    )


def forward_kinematics_tree(
    tree: TreeStrip,
    thetas: tuple[float, ...] | list[float] | NDArray[np.float64],
) -> TreeKinematicsResult:
    """Forward kinematics for a tree strip.

    Traverses the tree by DFS from the root (node 0), accumulating SE(3)
    transforms.  Node i's world pose is the composition of all ancestor
    edge transforms along the path from root to i.

    Args:
        tree: TreeStrip configuration.
        thetas: Hinge angles, length = n_nodes - 1 (one per non-root node).
                theta[i-1] is the angle at the edge from parent[i] to node i.

    Returns:
        TreeKinematicsResult with world-frame poses and positions.

    Raises:
        ValueError: if thetas length disagrees with n_nodes - 1.
    """
    thetas_arr = tuple(float(t) for t in thetas)
    if len(thetas_arr) != tree.n_nodes - 1:
        raise ValueError(
            f"forward_kinematics_tree: expected {tree.n_nodes - 1} hinge angles, "
            f"got {len(thetas_arr)}"
        )

    # Build adjacency list: parent → children.
    children: list[list[int]] = [[] for _ in range(tree.n_nodes)]
    for i in range(1, tree.n_nodes):
        p = tree.parents[i]
        if p is None:
            raise ValueError(
                f"forward_kinematics_tree: non-root node {i} has None parent"
            )
        children[p].append(i)

    frames: list[SE3] = [se3_identity()] * tree.n_nodes
    positions_list: list[NDArray[np.float64]] = [np.zeros(3)] * tree.n_nodes

    # DFS from root.
    stack: list[int] = [0]
    frames[0] = se3_identity()
    positions_list[0] = se3_apply(frames[0], np.zeros(3))

    while stack:
        node = stack.pop()
        frame = frames[node]
        positions_list[node] = se3_apply(frame, np.zeros(3))

        for child in children[node]:
            # theta index is child - 1 (root has no incoming edge).
            theta = thetas_arr[child - 1]
            L = tree.edge_lengths[child - 1]
            if tree.hinge_axes is not None:
                axis = tree.hinge_axes[child - 1]
            else:
                axis = CELL_Y_AXIS
            # Compose: translate along L then rotate about hinge axis.
            child_frame = se3_compose(
                frame,
                se3_compose(
                    trans(np.array([L, 0.0, 0.0])),
                    rot(axis, theta),
                ),
            )
            frames[child] = child_frame
            stack.append(child)

    nodes = tuple(
        TreeNodePose(frame=frames[i], position=positions_list[i].copy())
        for i in range(tree.n_nodes)
    )
    positions = np.stack([p.copy() for p in positions_list])

    return TreeKinematicsResult(nodes=nodes, positions=positions)
