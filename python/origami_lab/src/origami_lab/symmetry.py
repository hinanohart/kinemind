"""V_4 = Z_2 x Z_2 symmetry group acting on hinge state vectors.

  sigma : permutation that reverses hinge order   (geometric mirror)
  tau   : sign flip on every angle                 (paper-flip)
  sigmatau = sigma . tau                            (anti-symmetry)

These are the natural symmetries of an open path graph P_N.
Numerically mirrors TypeScript ``@kinemind/core-math`` symmetry.ts.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Literal

import numpy as np
from numpy.typing import NDArray

logger = logging.getLogger(__name__)

GroupElement = Literal["e", "sigma", "tau", "sigmatau"]
GROUP_ELEMENTS: tuple[GroupElement, ...] = ("e", "sigma", "tau", "sigmatau")


@dataclass(frozen=True)
class SymmetryGroup:
    """V_4 symmetry group acting on R^{n_hinges}.

    Attributes:
        n_hinges: Dimension of the state vector.
        sigma_perm: Permutation matrix for sigma (reverses order), shape (n,n).
        tau_sign: Sign factor for tau (always -1 for paper-flip).
    """

    n_hinges: int
    sigma_perm: NDArray[np.float64]   # shape (n, n)
    tau_sign: float


def klein_four_strip(n_hinges: int) -> SymmetryGroup:
    """Build the V_4 symmetry group for a strip with n_hinges hinges.

    Args:
        n_hinges: Number of hinges (>= 1).

    Returns:
        SymmetryGroup with sigma = reversal permutation matrix.

    Raises:
        ValueError: if n_hinges is not a positive integer.
    """
    if not isinstance(n_hinges, int) or n_hinges < 1:
        raise ValueError("klein_four_strip: n_hinges must be a positive integer")
    n = n_hinges
    P = np.zeros((n, n), dtype=np.float64)
    for i in range(n):
        P[i, n - 1 - i] = 1.0
    return SymmetryGroup(n_hinges=n, sigma_perm=P, tau_sign=-1.0)


def group_action(
    G: SymmetryGroup,
    g: GroupElement,
    v: NDArray[np.float64],
) -> NDArray[np.float64]:
    """Apply group element g to vector v.

    Args:
        G: SymmetryGroup.
        g: Group element: 'e', 'sigma', 'tau', or 'sigmatau'.
        v: Input vector shape (n_hinges,).

    Returns:
        Transformed vector shape (n_hinges,).

    Raises:
        ValueError: if v length mismatches G.n_hinges.
    """
    v = np.asarray(v, dtype=np.float64)
    if v.shape != (G.n_hinges,):
        raise ValueError(
            f"group_action: vector length {v.shape} mismatched with "
            f"group dim {G.n_hinges}"
        )
    if g == "e":
        return v.copy()
    if g == "sigma":
        return v[::-1].copy()
    if g == "tau":
        return -v
    if g == "sigmatau":
        return -v[::-1]
    raise ValueError(f"group_action: unknown group element '{g}'")


def group_action_matrix(
    G: SymmetryGroup,
    g: GroupElement,
) -> NDArray[np.float64]:
    """Return the n x n matrix representation of group element g.

    Args:
        G: SymmetryGroup.
        g: Group element.

    Returns:
        Matrix shape (n_hinges, n_hinges).
    """
    n = G.n_hinges
    M = np.zeros((n, n), dtype=np.float64)
    e_i = np.zeros(n, dtype=np.float64)
    for i in range(n):
        e_i[:] = 0.0
        e_i[i] = 1.0
        result = group_action(G, g, e_i)
        M[:, i] = result
    return M


def _conjugate(
    G: SymmetryGroup,
    g: GroupElement,
    M: NDArray[np.float64],
) -> NDArray[np.float64]:
    """Compute P_g M P_g^T (conjugate by g).

    Args:
        G: SymmetryGroup.
        g: Group element.
        M: Square matrix shape (n,n).

    Returns:
        Conjugated matrix shape (n,n).
    """
    n = G.n_hinges
    # Apply g to each row.
    left = np.array([group_action(G, g, M[i]) for i in range(n)])
    # Apply g to each column (= apply g to each row of the transpose).
    T = left.T.copy()
    for i in range(n):
        T[i] = group_action(G, g, T[i])
    return T.T


def reynolds_project(
    G: SymmetryGroup,
    M: NDArray[np.float64],
) -> NDArray[np.float64]:
    """Project matrix M onto the G-equivariant subspace via the Reynolds operator.

    M_eq = (1 / |G|) sum_{g in G} P_g M P_g^{-1}

    Args:
        G: SymmetryGroup.
        M: Square matrix shape (n_hinges, n_hinges).

    Returns:
        G-equivariant projection shape (n_hinges, n_hinges).

    Raises:
        ValueError: if M.shape does not match G.n_hinges.
    """
    M = np.asarray(M, dtype=np.float64)
    if M.shape != (G.n_hinges, G.n_hinges):
        raise ValueError(
            f"reynolds_project: matrix shape {M.shape} mismatches "
            f"group dim {G.n_hinges}"
        )
    acc = np.zeros_like(M)
    for g in GROUP_ELEMENTS:
        acc += _conjugate(G, g, M)
    return acc / len(GROUP_ELEMENTS)


def equivariance_residual(
    G: SymmetryGroup,
    M: NDArray[np.float64],
) -> float:
    """Frobenius distance of M to the G-equivariant subspace.

    Args:
        G: SymmetryGroup.
        M: Square matrix shape (n_hinges, n_hinges).

    Returns:
        ||M - reynolds_project(G, M)||_F (float).
    """
    M = np.asarray(M, dtype=np.float64)
    proj = reynolds_project(G, M)
    diff = M - proj
    return float(np.linalg.norm(diff, "fro"))
