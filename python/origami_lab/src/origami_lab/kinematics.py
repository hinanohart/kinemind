"""Forward kinematics for a 1D origami strip.

Cell 0's local frame coincides with the world frame: origin at the
leading-edge midpoint, +X pointing along the chain, +Y along the hinge axis.

Cell i's frame is obtained from cell (i-1)'s frame by:
  1. translating by L_{i-1} along the cell's +X axis (to the shared edge),
  2. rotating by theta_{i-1} about the cell's +Y axis (the hinge).

This is the standard Denavit-Hartenberg pattern restricted to 1-DoF
revolute joints in a planar chain.

Numerically mirrors TypeScript ``@kinemind/core-math`` kinematics.ts.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

from origami_lab.se3 import (
    SE3,
    se3_apply,
    se3_compose,
    se3_identity,
    rot,
    trans,
    quat_to_mat3,
    Vec3,
    Quat,
)
from origami_lab.strip import CELL_Y_AXIS, StripConfig, StripState

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class CellPose:
    """World-frame pose of a single origami cell.

    Attributes:
        frame: SE3 pose of the cell's local frame relative to world.
        position: Leading-edge midpoint position shape (3,).
    """

    frame: SE3
    position: NDArray[np.float64]


@dataclass(frozen=True)
class KinematicsResult:
    """Output of forward_kinematics.

    Attributes:
        cells: Ordered list of CellPose for each cell.
        centroids: World-frame centroid of each cell (leading + trailing edges averaged).
        positions: (N,3) array of cell leading-edge midpoints.
        quats: (N,4) array of cell orientation quaternions (w,x,y,z).
        rotations: (N,3,3) array of cell rotation matrices.
    """

    cells: tuple[CellPose, ...]
    centroids: tuple[NDArray[np.float64], ...]
    positions: NDArray[np.float64]   # shape (N, 3)
    quats: NDArray[np.float64]       # shape (N, 4)
    rotations: NDArray[np.float64]   # shape (N, 3, 3)


def forward_kinematics(
    config: StripConfig,
    state: StripState,
) -> tuple[NDArray[np.float64], NDArray[np.float64]]:
    """Compute world-frame poses for every cell. O(nCells) time.

    Args:
        config: Strip geometry (cell lengths, angle limits).
        state: Hinge angle vector with len(thetas) == config.n_hinges.

    Returns:
        Tuple (positions, quats):
            - positions: ndarray shape (N, 3), leading-edge midpoints.
            - quats: ndarray shape (N, 4), cell orientations (w,x,y,z).

    Raises:
        ValueError: if state.thetas length does not match config.n_hinges.
    """
    n = config.n_cells
    if len(state.thetas) != config.n_hinges:
        raise ValueError(
            f"forward_kinematics: expected {config.n_hinges} hinge angles, "
            f"got {len(state.thetas)}"
        )

    positions = np.empty((n, 3), dtype=np.float64)
    quats = np.empty((n, 4), dtype=np.float64)

    frame = se3_identity()

    for i in range(n):
        # position = leading-edge midpoint = se3_apply(frame, [0,0,0])
        positions[i] = se3_apply(frame, np.zeros(3))
        quats[i] = frame.q

        if i < n - 1:
            L_i = float(config.cell_lengths[i])
            theta = float(state.thetas[i])
            # Translate to shared edge, then rotate about hinge axis (+Y).
            frame = se3_compose(
                frame,
                se3_compose(
                    trans(np.array([L_i, 0.0, 0.0])),
                    rot(CELL_Y_AXIS, theta),
                ),
            )

    return positions, quats


def forward_kinematics_full(
    config: StripConfig,
    state: StripState,
) -> KinematicsResult:
    """Compute full kinematics result including centroids and rotation matrices.

    Args:
        config: Strip geometry.
        state: Hinge angle vector.

    Returns:
        KinematicsResult with cells, centroids, positions, quats, rotations.

    Raises:
        ValueError: if state shape disagrees with config.
    """
    n = config.n_cells
    if len(state.thetas) != config.n_hinges:
        raise ValueError(
            f"forward_kinematics_full: expected {config.n_hinges} hinge angles, "
            f"got {len(state.thetas)}"
        )

    cells_list: list[CellPose] = []
    centroids_list: list[NDArray[np.float64]] = []

    frame = se3_identity()

    for i in range(n):
        pos = se3_apply(frame, np.zeros(3))
        cells_list.append(CellPose(frame=frame, position=pos.copy()))
        L_i = float(config.cell_lengths[i])
        centroids_list.append(se3_apply(frame, np.array([L_i * 0.5, 0.0, 0.0])))

        if i < n - 1:
            theta = float(state.thetas[i])
            frame = se3_compose(
                frame,
                se3_compose(
                    trans(np.array([L_i, 0.0, 0.0])),
                    rot(CELL_Y_AXIS, theta),
                ),
            )

    positions = np.stack([c.position for c in cells_list])
    quats = np.stack([c.frame.q for c in cells_list])
    rotations = np.stack([quat_to_mat3(c.frame.q) for c in cells_list])

    return KinematicsResult(
        cells=tuple(cells_list),
        centroids=tuple(centroids_list),
        positions=positions,
        quats=quats,
        rotations=rotations,
    )


def cell_corners_local(cell_length: float) -> NDArray[np.float64]:
    """Return the 4 corners of a cell in its local frame (CCW from +Z).

    Mirrors TypeScript ``cellCornersLocal`` in kinematics.ts.

    Args:
        cell_length: Cell length along +X.

    Returns:
        Corners array shape (4, 3) in CCW order viewed from +Z.
    """
    half = 0.5
    return np.array(
        [
            [0.0, -half, 0.0],
            [cell_length, -half, 0.0],
            [cell_length, half, 0.0],
            [0.0, half, 0.0],
        ],
        dtype=np.float64,
    )


def cell_corners_world(
    config: StripConfig,
    result: "KinematicsResult",
) -> list[NDArray[np.float64]]:
    """Return world-frame corners of every cell.

    Mirrors TypeScript ``cellCornersWorld`` in kinematics.ts.

    Args:
        config: Strip geometry.
        result: KinematicsResult from :func:`forward_kinematics_full`.

    Returns:
        List of length n_cells; each element is an ndarray shape (4, 3).
    """
    out: list[NDArray[np.float64]] = []
    for i, cell_pose in enumerate(result.cells):
        L = float(config.cell_lengths[i])
        local = cell_corners_local(L)
        # Apply SE3 transform to each corner.
        world = np.stack([se3_apply(cell_pose.frame, local[k]) for k in range(4)])
        out.append(world)
    return out
