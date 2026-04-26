"""Mental coupling matrix estimation and manipulation.

The coupling matrix C maps intended hinge angle vector to the configuration
actually pictured. Diagonal entries encode self-fidelity (== 1 in the linear
regime); off-diagonal entries encode involuntary co-activation.

The Kinematic Mental Mirroring (KMM) hypothesis predicts that C is
V_4-equivariant. By Schur's lemma C lives in a 4-dimensional parameter family.

Numerically mirrors TypeScript ``@kinemind/core-math`` coupling.ts.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

import numpy as np
from numpy.typing import NDArray
from scipy import linalg as sp_linalg

from origami_lab.symmetry import (
    SymmetryGroup,
    equivariance_residual,
    reynolds_project,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class MentalCoupling:
    """Container for a coupling matrix and its provenance.

    Attributes:
        matrix: (n_hinges, n_hinges) coupling matrix.
        n_hinges: Number of hinges.
        group: Optional symmetry group used during estimation.
        source: 'analytic' if built analytically, 'empirical' if estimated.
        beta: Strength parameter in [0,1] when source='analytic'.
    """

    matrix: NDArray[np.float64]
    n_hinges: int
    group: Optional[SymmetryGroup] = None
    source: str = "analytic"
    beta: Optional[float] = None

    def __post_init__(self) -> None:
        """Validate and sanitize inputs."""
        object.__setattr__(
            self, "matrix", np.asarray(self.matrix, dtype=np.float64)
        )
        if self.matrix.shape != (self.n_hinges, self.n_hinges):
            raise ValueError(
                f"MentalCoupling: matrix shape {self.matrix.shape} does not "
                f"match n_hinges={self.n_hinges}"
            )
        if self.source not in ("analytic", "empirical"):
            raise ValueError(
                f"MentalCoupling: source must be 'analytic' or 'empirical' "
                f"(got '{self.source}')"
            )


def identity_coupling(n_hinges: int) -> MentalCoupling:
    """Return the identity (null-hypothesis) coupling matrix.

    Args:
        n_hinges: Number of hinges (>= 1).

    Returns:
        MentalCoupling with identity matrix (beta=0).

    Raises:
        ValueError: if n_hinges is not a positive integer.
    """
    if not isinstance(n_hinges, int) or n_hinges < 1:
        raise ValueError("identity_coupling: n_hinges must be a positive integer")
    M = np.eye(n_hinges, dtype=np.float64)
    return MentalCoupling(matrix=M, n_hinges=n_hinges, source="analytic", beta=0.0)


def mirror_coupling_matrix(n_hinges: int, beta: float) -> NDArray[np.float64]:
    """Compute the mirror coupling matrix C(beta) as a plain ndarray.

    C[i][i]      = 1
    C[i][n-1-i]  = beta  (if i != n-1-i)
    else         = 0

    Eigenvalues: {1+beta} (floor(n/2) times), {1-beta} (floor(n/2) times),
    {1} once when n is odd.

    Args:
        n_hinges: Number of hinges (>= 1).
        beta: Mirror coupling strength in [0, 1].

    Returns:
        ndarray shape (n_hinges, n_hinges).

    Raises:
        ValueError: if inputs are invalid.
    """
    if not isinstance(n_hinges, int) or n_hinges < 1:
        raise ValueError("mirror_coupling_matrix: n_hinges must be a positive integer")
    if not (0.0 <= beta <= 1.0):
        raise ValueError(
            f"mirror_coupling_matrix: beta must be in [0, 1] (got {beta})"
        )
    M = np.zeros((n_hinges, n_hinges), dtype=np.float64)
    for i in range(n_hinges):
        M[i, i] = 1.0
        j = n_hinges - 1 - i
        if j != i:
            M[i, j] = beta
    return M


def mirror_coupling(n_hinges: int, beta: float) -> MentalCoupling:
    """Build a MentalCoupling object from the mirror coupling matrix.

    Args:
        n_hinges: Number of hinges (>= 1).
        beta: Mirror coupling strength in [0, 1].

    Returns:
        MentalCoupling with analytic mirror structure.
    """
    M = mirror_coupling_matrix(n_hinges, beta)
    return MentalCoupling(matrix=M, n_hinges=n_hinges, source="analytic", beta=beta)


def apply_coupling(
    coupling: MentalCoupling,
    theta_intent: NDArray[np.float64],
    angle_max: Optional[float] = None,
) -> NDArray[np.float64]:
    """Apply coupling matrix to an intent vector: theta_mental = C theta_intent.

    Args:
        coupling: MentalCoupling container.
        theta_intent: Intent angles shape (n_hinges,).
        angle_max: Optional clamp limit (applied element-wise).

    Returns:
        Mental angles shape (n_hinges,).

    Raises:
        ValueError: if theta_intent length mismatches coupling dimension.
    """
    x = np.asarray(theta_intent, dtype=np.float64)
    if x.shape != (coupling.n_hinges,):
        raise ValueError(
            f"apply_coupling: intent shape {x.shape} mismatched with "
            f"coupling dim {coupling.n_hinges}"
        )
    out = coupling.matrix @ x
    if angle_max is not None:
        out = np.clip(out, -angle_max, angle_max)
    return out


def estimate_coupling(
    intents: NDArray[np.float64],
    responses: NDArray[np.float64],
    n_hinges: int,
    lambda_: float = 0.0,
    use_v4: bool = False,
    group: Optional[SymmetryGroup] = None,
) -> NDArray[np.float64]:
    """Estimate coupling matrix by ordinary least squares (Tikhonov optional).

    C_hat = argmin_C ||Y - X C^T||_F^2 + lambda ||C||_F^2

    where X is the (K, n_hinges) intent matrix and Y is the (K, n_hinges)
    response matrix. If group is provided (or use_v4=True), the estimate is
    post-projected onto the G-equivariant subspace via the Reynolds operator.

    Args:
        intents: Intent angles shape (K, n_hinges).
        responses: Response angles shape (K, n_hinges).
        n_hinges: Number of hinges.
        lambda_: Tikhonov regularisation coefficient (default 0).
        use_v4: If True and group is None, auto-construct V_4 group.
        group: Optional SymmetryGroup for equivariant projection.

    Returns:
        Estimated coupling matrix ndarray shape (n_hinges, n_hinges).

    Raises:
        ValueError: if input shapes are inconsistent.
    """
    from origami_lab.symmetry import klein_four_strip  # local to avoid cycle

    X = np.asarray(intents, dtype=np.float64)
    Y = np.asarray(responses, dtype=np.float64)

    if X.ndim != 2 or Y.ndim != 2:
        raise ValueError("estimate_coupling: intents and responses must be 2-D arrays")
    if X.shape != Y.shape:
        raise ValueError("estimate_coupling: intents and responses shapes disagree")
    K, n = X.shape
    if n != n_hinges:
        raise ValueError(
            f"estimate_coupling: column count {n} does not match n_hinges={n_hinges}"
        )
    if K == 0:
        raise ValueError("estimate_coupling: at least one trial is required")

    # Build Gram matrix X^T X (n x n) and cross-product X^T Y (n x n).
    XtX = X.T @ X
    XtY = X.T @ Y

    if lambda_ > 0.0:
        XtX += lambda_ * np.eye(n_hinges, dtype=np.float64)

    # Solve XtX B = XtY  =>  B = C^T  =>  C = B^T
    try:
        B = sp_linalg.solve(XtX, XtY, assume_a="sym")
    except sp_linalg.LinAlgError as exc:
        raise ValueError("estimate_coupling: Gram matrix is singular") from exc

    C = B.T

    # Optional symmetry projection.
    effective_group = group
    if use_v4 and effective_group is None:
        effective_group = klein_four_strip(n_hinges)
    if effective_group is not None:
        C = reynolds_project(effective_group, C)

    return C


def coupling_equivariance_residual(
    coupling: MentalCoupling,
    group: SymmetryGroup,
) -> float:
    """Frobenius distance of the coupling matrix to the G-equivariant subspace.

    Args:
        coupling: MentalCoupling container.
        group: SymmetryGroup.

    Returns:
        ||C - reynolds_project(G, C)||_F (float).
    """
    return equivariance_residual(group, coupling.matrix)


def spectral_radius(
    M: NDArray[np.float64],
    max_iter: int = 200,
    tol: float = 1e-10,
) -> float:
    """Power-method spectral radius (largest absolute eigenvalue).

    Args:
        M: Square matrix shape (n, n).
        max_iter: Maximum power iterations (default 200).
        tol: Convergence tolerance (default 1e-10).

    Returns:
        Spectral radius (float).
    """
    M = np.asarray(M, dtype=np.float64)
    n = M.shape[0]
    if n == 0:
        return 0.0
    v = np.ones(n, dtype=np.float64)
    v[0] = 1.0
    lam = 0.0
    for _ in range(max_iter):
        Mv = M @ v
        norm = float(np.linalg.norm(Mv))
        if norm < 1e-300:
            return 0.0
        next_v = Mv / norm
        delta = float(np.linalg.norm(next_v - v))
        v = next_v
        lam_next = norm
        if abs(lam_next - lam) < tol and delta < tol:
            return lam_next
        lam = lam_next
    return lam


def effective_rank(M: NDArray[np.float64], threshold: float = 1e-6) -> int:
    """Number of singular values exceeding threshold * sigma_max.

    Args:
        M: Matrix shape (m, n).
        threshold: Relative threshold (default 1e-6).

    Returns:
        Effective rank (int).
    """
    M = np.asarray(M, dtype=np.float64)
    if M.size == 0:
        return 0
    sv = np.linalg.svd(M, compute_uv=False)
    sigma_max = sv[0] if sv.size > 0 else 0.0
    if sigma_max == 0.0:
        return 0
    return int(np.sum(sv > threshold * sigma_max))
