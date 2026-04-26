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
from dataclasses import dataclass, field
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
        warnings: List of diagnostic warning strings collected during estimation.
            Mirrors the adaptive singularity detection in coupling.ts
            solveLinearSystem. Non-fatal conditions (near-singular Gram matrix
            with regularisation applied) are stored here rather than raised.
    """

    matrix: NDArray[np.float64]
    n_hinges: int
    group: Optional[SymmetryGroup] = None
    source: str = "analytic"
    beta: Optional[float] = None
    warnings: tuple[str, ...] = field(default_factory=tuple)

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


def _solve_gram(
    XtX: NDArray[np.float64],
    XtY: NDArray[np.float64],
    n_hinges: int,
    lambda_: float,
) -> tuple[NDArray[np.float64], list[str]]:
    """Solve the normal equations XtX B = XtY with adaptive singularity detection.

    Mirrors the adaptive ``singularThreshold`` logic in coupling.ts
    ``solveLinearSystem``.  When the effective condition number suggests near-
    singularity but regularisation has been applied, a warning is emitted
    instead of raising (matching the TS chained-warning pattern).

    Args:
        XtX: Gram matrix (n_hinges, n_hinges), may include lambda ridge term.
        XtY: Cross-product matrix (n_hinges, n_hinges).
        n_hinges: Dimension n.
        lambda_: Regularisation strength (>= 0).

    Returns:
        Tuple (B, warnings) where B = XtX^{-1} XtY and warnings is a list
        of diagnostic strings (empty when no near-singularity was detected).

    Raises:
        ValueError: if the Gram matrix is singular and lambda_ == 0.
    """
    warns: list[str] = []
    # Adaptive threshold: eps_mach * n * ||XtX||_F (same formula as TS).
    frob = float(np.linalg.norm(XtX, "fro"))
    singular_threshold = max(2.22e-16 * n_hinges * frob, 1e-300)
    eigvals = np.linalg.eigvalsh(XtX)
    min_eig = float(eigvals[0])
    if min_eig < singular_threshold:
        msg = (
            f"estimate_coupling: Gram matrix near-singular "
            f"(min_eigval={min_eig:.3e}, threshold={singular_threshold:.3e})"
        )
        if lambda_ > 0.0:
            warns.append(msg + f"; ridge lambda={lambda_:.3e} applied")
            logger.warning(warns[-1])
        else:
            raise ValueError(msg + "; add lambda_ > 0 for regularisation")

    try:
        B = sp_linalg.solve(XtX, XtY, assume_a="sym")
    except sp_linalg.LinAlgError as exc:
        raise ValueError("estimate_coupling: Gram matrix is singular") from exc

    return B, warns


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
        ValueError: if input shapes are inconsistent or Gram matrix is singular.
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
        XtX = XtX + lambda_ * np.eye(n_hinges, dtype=np.float64)

    B, _warns = _solve_gram(XtX, XtY, n_hinges, lambda_)
    C = B.T

    # Optional symmetry projection.
    effective_group = group
    if use_v4 and effective_group is None:
        effective_group = klein_four_strip(n_hinges)
    if effective_group is not None:
        C = reynolds_project(effective_group, C)

    return C


@dataclass(frozen=True)
class CouplingWithCI:
    """Coupling matrix estimate with bootstrapped confidence intervals.

    Attributes:
        C_hat: Point estimate (n_hinges, n_hinges).
        lower_95: 2.5th percentile of bootstrap distribution (n_hinges, n_hinges).
        upper_95: 97.5th percentile of bootstrap distribution (n_hinges, n_hinges).
        bootstrap_n: Number of bootstrap replicates used.
        method: 'non-parametric' or 'analytic'.
    """

    C_hat: NDArray[np.float64]
    lower_95: NDArray[np.float64]
    upper_95: NDArray[np.float64]
    bootstrap_n: int
    method: str

    def __post_init__(self) -> None:
        """Validate field types."""
        if self.method not in ("non-parametric", "analytic"):
            raise ValueError(
                f"CouplingWithCI: method must be 'non-parametric' or 'analytic' "
                f"(got '{self.method}')"
            )
        if self.bootstrap_n < 1:
            raise ValueError(
                f"CouplingWithCI: bootstrap_n must be >= 1 (got {self.bootstrap_n})"
            )


def estimate_coupling_with_ci(
    intents: NDArray[np.float64],
    responses: NDArray[np.float64],
    n_hinges: int,
    *,
    lambda_: float = 0.0,
    bootstrap_n: int = 1000,
    seed: int = 0,
    method: str = "non-parametric",
) -> CouplingWithCI:
    """Estimate coupling matrix with 95% bootstrap confidence intervals.

    Extends :func:`estimate_coupling` with non-parametric case bootstrap CIs.
    The point estimate ``C_hat`` is identical to ``estimate_coupling``'s output.

    Bootstrap procedure (non-parametric):
        For each replicate, resample K rows (with replacement) from the
        (intents, responses) paired dataset, refit via OLS, and collect
        the empirical 2.5/97.5 percentile for each matrix element.

    Args:
        intents: Intent angles shape (K, n_hinges).
        responses: Response angles shape (K, n_hinges).
        n_hinges: Number of hinges.
        lambda_: Tikhonov regularisation applied in each bootstrap fit.
        bootstrap_n: Number of bootstrap replicates (default 1000).
        seed: Random seed for reproducibility (default 0).
        method: Bootstrap method; currently only 'non-parametric' is supported.

    Returns:
        CouplingWithCI with C_hat, lower_95, upper_95, bootstrap_n, method.

    Raises:
        ValueError: if inputs are inconsistent or method is unsupported.
    """
    if method != "non-parametric":
        raise ValueError(
            f"estimate_coupling_with_ci: only 'non-parametric' method is supported "
            f"(got '{method}')"
        )
    X = np.asarray(intents, dtype=np.float64)
    Y = np.asarray(responses, dtype=np.float64)
    if X.ndim != 2 or Y.ndim != 2:
        raise ValueError(
            "estimate_coupling_with_ci: intents and responses must be 2-D arrays"
        )
    if X.shape != Y.shape:
        raise ValueError(
            "estimate_coupling_with_ci: intents and responses shapes disagree"
        )
    K, n = X.shape
    if n != n_hinges:
        raise ValueError(
            f"estimate_coupling_with_ci: column count {n} does not match n_hinges={n_hinges}"
        )
    if K < 2:
        raise ValueError("estimate_coupling_with_ci: at least 2 trials are required for bootstrap")
    if bootstrap_n < 1:
        raise ValueError(f"estimate_coupling_with_ci: bootstrap_n must be >= 1 (got {bootstrap_n})")

    # Point estimate.
    C_hat = estimate_coupling(X, Y, n_hinges, lambda_=lambda_)

    # Non-parametric bootstrap.
    rng = np.random.default_rng(seed)
    boot_samples: list[NDArray[np.float64]] = []

    for _ in range(bootstrap_n):
        idx = rng.integers(0, K, size=K)
        Xb = X[idx]
        Yb = Y[idx]
        XtX_b = Xb.T @ Xb
        XtY_b = Xb.T @ Yb
        if lambda_ > 0.0:
            XtX_b = XtX_b + lambda_ * np.eye(n_hinges, dtype=np.float64)
        try:
            B_b, _ = _solve_gram(XtX_b, XtY_b, n_hinges, lambda_)
            boot_samples.append(B_b.T)
        except ValueError:
            # Near-singular bootstrap sample: skip without counting as failure.
            logger.debug("estimate_coupling_with_ci: singular bootstrap sample skipped")
            continue

    if len(boot_samples) == 0:
        raise ValueError(
            "estimate_coupling_with_ci: all bootstrap samples were singular; "
            "increase lambda_ or provide more data"
        )

    stack = np.stack(boot_samples, axis=0)  # (B, n, n)
    lower_95 = np.percentile(stack, 2.5, axis=0)
    upper_95 = np.percentile(stack, 97.5, axis=0)

    return CouplingWithCI(
        C_hat=C_hat,
        lower_95=lower_95,
        upper_95=upper_95,
        bootstrap_n=len(boot_samples),
        method=method,
    )


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
