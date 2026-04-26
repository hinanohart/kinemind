"""SAT narrow-phase self-intersection detection for origami strips.

Implements quad-quad overlap tests using the classic 11-axis SAT:
    - 2 face normals (one per quad, derived from cross products of consecutive edges)
    - 9 edge-edge cross products (3 edges × 3 edges)

Reference: Akenine-Möller (1997) "A Fast Triangle-Triangle Intersection Test".
For coplanar quads the degenerate cross products are zero; a 2D SAT fallback
(all 8 edge normals projected onto the common plane) is used in that case.

Parity: identical algorithm to TypeScript
``@kinemind/core-math`` collision.ts.
All position/penetration values agree to atol=1e-12 on the same golden inputs.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

import numpy as np
from numpy.typing import NDArray

from origami_lab.kinematics import KinematicsResult, cell_corners_world
from origami_lab.strip import StripConfig, StripState

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class SelfIntersection:
    """Record of a detected self-intersection between two quads.

    Attributes:
        i: Index of the first (lower index) cell.
        j: Index of the second (higher index) cell; always j > i + 1.
        point: Approximate contact point (midpoint of quad centroids).
        penetration: Penetration depth (minimum overlap along SAT axes).
    """

    i: int
    j: int
    point: NDArray[np.float64]  # shape (3,)
    penetration: float


def detect_self_intersection_sat(
    config: StripConfig,
    result: KinematicsResult,
    tol: float = 1e-9,
) -> list[SelfIntersection]:
    """Detect all pairwise self-intersections using SAT narrow-phase.

    Non-adjacent cell pairs only (j > i + 1).  O(nCells^2 * 11) per call.

    Args:
        config: Strip geometry.
        result: Forward kinematics result (KinematicsResult).
        tol: Separation tolerance (default 1e-9).  Overlaps smaller than
             tol are not reported.

    Returns:
        List of detected SelfIntersection records; empty if no overlaps.
    """
    corners = cell_corners_world(config, result)
    hits: list[SelfIntersection] = []
    n = len(corners)
    for i in range(n):
        for j in range(i + 2, n):
            qa = corners[i]
            qb = corners[j]
            hit = quad_quad_overlap(qa, qb, tol=tol)
            if hit is not None:
                point, penetration = hit
                hits.append(SelfIntersection(i=i, j=j, point=point, penetration=penetration))
    return hits


def quad_quad_overlap(
    qa: NDArray[np.float64],
    qb: NDArray[np.float64],
    *,
    tol: float = 1e-9,
) -> Optional[tuple[NDArray[np.float64], float]]:
    """Test two convex quads for SAT overlap.

    Args:
        qa: First quad corners shape (4, 3).
        qb: Second quad corners shape (4, 3).
        tol: Separation tolerance.

    Returns:
        Tuple (contact_point, penetration) if overlapping, None if separated.

    Raises:
        ValueError: if a quad does not have exactly 4 vertices.
    """
    qa = np.asarray(qa, dtype=np.float64)
    qb = np.asarray(qb, dtype=np.float64)
    if qa.shape != (4, 3):
        raise ValueError(f"quad_quad_overlap: qa must have shape (4, 3), got {qa.shape}")
    if qb.shape != (4, 3):
        raise ValueError(f"quad_quad_overlap: qb must have shape (4, 3), got {qb.shape}")

    edges_a = _quad_edges(qa)  # (4, 3)
    edges_b = _quad_edges(qb)  # (4, 3)

    # Face normals.
    normal_a = _safe_normalize(np.cross(edges_a[0], edges_a[1]))
    normal_b = _safe_normalize(np.cross(edges_b[0], edges_b[1]))

    # Detect parallel face normals.
    parallel_normals = (
        normal_a is not None
        and normal_b is not None
        and abs(float(np.dot(normal_a, normal_b))) > 1.0 - 1e-7
    )

    # Detect coplanar: parallel normals AND offset centroid perpendicular to normal.
    coplanar = False
    if parallel_normals and normal_a is not None:
        cent_a = qa.mean(axis=0)
        cent_b = qb.mean(axis=0)
        offset_along_normal = abs(float(np.dot(cent_b - cent_a, normal_a)))
        coplanar = offset_along_normal < 1e-9

    axes: list[NDArray[np.float64]] = []

    if not coplanar:
        # General case: face normals + 9 edge-edge cross products.
        if normal_a is not None:
            axes.append(normal_a)
        if normal_b is not None:
            axes.append(normal_b)
        for a in range(3):
            for b in range(3):
                ax = _safe_normalize(np.cross(edges_a[a], edges_b[b]))
                if ax is not None:
                    axes.append(ax)
    else:
        # Coplanar fallback: 2D SAT with all 8 edge direction axes.
        for e in np.vstack([edges_a, edges_b]):
            ax = _safe_normalize(e)
            if ax is not None:
                axes.append(ax)

    min_penetration = np.inf
    for axis in axes:
        min_a, max_a = _project_onto_axis(qa, axis)
        min_b, max_b = _project_onto_axis(qb, axis)
        overlap = min(max_a, max_b) - max(min_a, min_b)
        if overlap < tol:
            return None
        if overlap < min_penetration:
            min_penetration = overlap

    # No separating axis → intersection.
    centroid_a = qa.mean(axis=0)
    centroid_b = qb.mean(axis=0)
    point = (centroid_a + centroid_b) * 0.5
    return point, float(min_penetration)


# ---- Internal helpers ----

def _quad_edges(q: NDArray[np.float64]) -> NDArray[np.float64]:
    """Return the 4 edge vectors of a quad (consecutive vertex differences).

    Args:
        q: Quad corners shape (4, 3).

    Returns:
        Edge vectors shape (4, 3).
    """
    n = q.shape[0]
    return np.array([q[(i + 1) % n] - q[i] for i in range(n)], dtype=np.float64)


def _project_onto_axis(
    q: NDArray[np.float64], axis: NDArray[np.float64]
) -> tuple[float, float]:
    """Project quad vertices onto axis; return (min, max) scalar range.

    Args:
        q: Quad corners shape (4, 3).
        axis: Unit axis shape (3,).

    Returns:
        (min, max) projection values.
    """
    dots = q @ axis  # shape (4,)
    return float(dots.min()), float(dots.max())


def _safe_normalize(v: NDArray[np.float64]) -> Optional[NDArray[np.float64]]:
    """Normalize a 3-vector; return None if near-zero.

    Args:
        v: 3-vector shape (3,).

    Returns:
        Unit vector or None.
    """
    n = float(np.linalg.norm(v))
    if n < 1e-12:
        return None
    return v / n
