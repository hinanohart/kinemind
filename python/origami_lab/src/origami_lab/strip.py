"""1D origami strip configuration and state.

The strip is a path graph P_N of square cells linked by N-1 hinges.
Cell 0 is anchored at the world origin with its plane in the XY plane.
Hinge axes run along the local Y axis (shared edges between adjacent cells).
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass
from typing import Sequence

import numpy as np

logger = logging.getLogger(__name__)

# Cell local-frame canonical axes (matches TS CELL_*_AXIS constants).
CELL_X_AXIS = np.array([1.0, 0.0, 0.0], dtype=np.float64)
CELL_Y_AXIS = np.array([0.0, 1.0, 0.0], dtype=np.float64)
CELL_Z_AXIS = np.array([0.0, 0.0, 1.0], dtype=np.float64)


@dataclass(frozen=True)
class StripConfig:
    """Immutable strip geometry specification.

    Attributes:
        n_cells: Number of cells (>= 2).
        cell_lengths: Per-cell edge length along the chain.
        angle_max: Hard limit on |theta_i| in radians; defaults to pi.
    """

    n_cells: int
    cell_lengths: tuple[float, ...]
    angle_max: float = math.pi

    def __post_init__(self) -> None:
        """Validate parameters."""
        if not isinstance(self.n_cells, int) or self.n_cells < 2:
            raise ValueError(
                f"StripConfig: n_cells must be an integer >= 2 (got {self.n_cells})"
            )
        if len(self.cell_lengths) != self.n_cells:
            raise ValueError(
                f"StripConfig: cell_lengths length {len(self.cell_lengths)} "
                f"must equal n_cells={self.n_cells}"
            )
        for i, L in enumerate(self.cell_lengths):
            if not (math.isfinite(L) and L > 0):
                raise ValueError(
                    f"StripConfig: cell_lengths[{i}] must be positive finite (got {L})"
                )
        if not (math.isfinite(self.angle_max) and 0 < self.angle_max <= math.pi):
            raise ValueError(
                f"StripConfig: angle_max must be in (0, pi] (got {self.angle_max})"
            )

    @property
    def n_hinges(self) -> int:
        """Number of hinges = n_cells - 1."""
        return self.n_cells - 1


@dataclass(frozen=True)
class StripState:
    """Immutable hinge angle vector.

    Attributes:
        thetas: Hinge angles, length = n_cells - 1.
                Positive = mountain fold, negative = valley fold.
    """

    thetas: tuple[float, ...]

    def __post_init__(self) -> None:
        """Convert to tuple if needed."""
        object.__setattr__(self, "thetas", tuple(float(t) for t in self.thetas))


def make_uniform_strip(
    n_cells: int,
    cell_length: float = 1.0,
    angle_max: float = math.pi,
) -> StripConfig:
    """Build a uniform StripConfig with equal cell lengths.

    Args:
        n_cells: Number of cells (>= 2).
        cell_length: Length of each cell (default 1.0).
        angle_max: Maximum hinge angle magnitude in radians (default pi).

    Returns:
        StripConfig with uniform cell lengths.

    Raises:
        ValueError: if parameters are invalid.
    """
    if not isinstance(n_cells, int) or n_cells < 2:
        raise ValueError(
            f"make_uniform_strip: n_cells must be an integer >= 2 (got {n_cells})"
        )
    if not (math.isfinite(cell_length) and cell_length > 0):
        raise ValueError(
            f"make_uniform_strip: cell_length must be positive finite (got {cell_length})"
        )
    if not (math.isfinite(angle_max) and 0 < angle_max <= math.pi):
        raise ValueError(
            f"make_uniform_strip: angle_max must be in (0, pi] (got {angle_max})"
        )
    return StripConfig(
        n_cells=n_cells,
        cell_lengths=tuple(cell_length for _ in range(n_cells)),
        angle_max=angle_max,
    )


def flat_state(config: StripConfig) -> StripState:
    """Return the flat (all-zero) hinge state for a strip.

    Args:
        config: Strip configuration.

    Returns:
        StripState with all thetas == 0.
    """
    return StripState(thetas=tuple(0.0 for _ in range(config.n_hinges)))


def clamp_state(config: StripConfig, state: StripState) -> StripState:
    """Clamp hinge angles to [-angle_max, angle_max].

    Args:
        config: Strip configuration carrying angle_max.
        state: Hinge state to clamp.

    Returns:
        Clamped StripState.
    """
    m = config.angle_max
    return StripState(
        thetas=tuple(max(-m, min(m, t)) for t in state.thetas)
    )


def reflect_state(state: StripState) -> StripState:
    """Reflect hinge angles through the strip midpoint (sigma action).

    sigma . theta = (theta_{N-1}, ..., theta_0).

    Args:
        state: Original hinge state.

    Returns:
        Reversed StripState.
    """
    return StripState(thetas=tuple(reversed(state.thetas)))


def flip_state(state: StripState) -> StripState:
    """Flip all hinge angles (tau action: mountain <-> valley).

    tau . theta = -theta.

    Args:
        state: Original hinge state.

    Returns:
        Sign-flipped StripState.
    """
    return StripState(thetas=tuple(-t for t in state.thetas))
