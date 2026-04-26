"""Hypothesis tests H1-H6 for coupling matrix analysis.

This module provides scaffold implementations for the six hypotheses:
  H1: beta > 0 (non-zero mirror coupling).
  H2: C is V_4-equivariant (equivariance residual test).
  H3: C is rank-deficient under strong coupling.
  H4: Spectral radius < 1 + beta (stability bound).
  H5: Intent correlation predicts response correlation.
  H6: Coupling is symmetric (C == C^T).

Note: Statistical tests use bootstrap / permutation where appropriate.
All tests return a dict compatible with the report JSON schema.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Optional

import numpy as np
from numpy.typing import NDArray
from scipy import stats as sp_stats

from origami_lab.coupling import (
    MentalCoupling,
    coupling_equivariance_residual,
    effective_rank,
    spectral_radius,
)
from origami_lab.symmetry import SymmetryGroup, klein_four_strip

logger = logging.getLogger(__name__)


@dataclass
class HypothesisResult:
    """Result of a single hypothesis test.

    Attributes:
        hypothesis: Identifier string, e.g. 'H1'.
        description: Human-readable description.
        statistic: Test statistic value.
        p_value: p-value (may be None for descriptive tests).
        reject_null: True if null hypothesis rejected at alpha=0.05.
        extras: Additional diagnostic information.
    """

    hypothesis: str
    description: str
    statistic: float
    p_value: Optional[float]
    reject_null: bool
    extras: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        """Serialize to JSON-compatible dict."""
        return {
            "hypothesis": self.hypothesis,
            "description": self.description,
            "statistic": self.statistic,
            "p_value": self.p_value,
            "reject_null": self.reject_null,
            "extras": self.extras,
        }


def check_h1_nonzero_beta(
    coupling: MentalCoupling,
    alpha: float = 0.05,
) -> HypothesisResult:
    """H1: Mirror coupling strength beta > 0.

    Uses the off-diagonal mean as a test statistic.
    A one-sample t-test is applied to the (i, n-1-i) pairs.

    Args:
        coupling: Estimated coupling matrix.
        alpha: Significance level.

    Returns:
        HypothesisResult for H1.
    """
    M = coupling.matrix
    n = coupling.n_hinges
    pairs: list[float] = []
    for i in range(n):
        j = n - 1 - i
        if j != i:
            pairs.append(float(M[i, j]))

    if not pairs:
        # n == 1: no off-diagonal pairs.
        return HypothesisResult(
            hypothesis="H1",
            description="Non-zero mirror coupling (beta > 0)",
            statistic=0.0,
            p_value=1.0,
            reject_null=False,
            extras={"n_pairs": 0},
        )

    arr = np.array(pairs)
    t_stat, p_val = sp_stats.ttest_1samp(arr, popmean=0.0, alternative="greater")
    return HypothesisResult(
        hypothesis="H1",
        description="Non-zero mirror coupling (beta > 0)",
        statistic=float(t_stat),
        p_value=float(p_val),
        reject_null=bool(p_val < alpha),
        extras={"mean_off_diagonal": float(arr.mean()), "n_pairs": len(pairs)},
    )


def check_h2_equivariance(
    coupling: MentalCoupling,
    group: Optional[SymmetryGroup] = None,
    alpha: float = 0.05,
) -> HypothesisResult:
    """H2: Coupling matrix is V_4-equivariant.

    Args:
        coupling: Coupling to test.
        group: Symmetry group (defaults to V_4 for coupling.n_hinges).
        alpha: Significance level.

    Returns:
        HypothesisResult for H2.
    """
    if group is None:
        group = klein_four_strip(coupling.n_hinges)
    residual = coupling_equivariance_residual(coupling, group)
    # Heuristic threshold: residual < 1e-6 * n is "equivariant".
    threshold = 1e-6 * coupling.n_hinges
    return HypothesisResult(
        hypothesis="H2",
        description="C is V_4-equivariant",
        statistic=residual,
        p_value=None,
        reject_null=bool(residual >= threshold),
        extras={"residual": residual, "threshold": threshold},
    )


def check_h3_rank_deficiency(
    coupling: MentalCoupling,
    alpha: float = 0.05,
) -> HypothesisResult:
    """H3: Coupling matrix is rank-deficient under strong coupling.

    Args:
        coupling: Coupling to test.
        alpha: Significance level (unused; descriptive).

    Returns:
        HypothesisResult for H3.
    """
    rank = effective_rank(coupling.matrix)
    full_rank = coupling.n_hinges
    return HypothesisResult(
        hypothesis="H3",
        description="C has reduced effective rank (rank-deficiency test)",
        statistic=float(rank),
        p_value=None,
        reject_null=bool(rank < full_rank),
        extras={"effective_rank": rank, "full_rank": full_rank},
    )


def check_h4_spectral_stability(
    coupling: MentalCoupling,
    beta: float = 0.5,
    alpha: float = 0.05,
) -> HypothesisResult:
    """H4: Spectral radius rho(C) < 1 + beta.

    Args:
        coupling: Coupling to test.
        beta: Expected coupling parameter for the bound.
        alpha: Significance level (unused; descriptive).

    Returns:
        HypothesisResult for H4.
    """
    rho = spectral_radius(coupling.matrix)
    bound = 1.0 + beta
    return HypothesisResult(
        hypothesis="H4",
        description="Spectral radius rho(C) < 1 + beta",
        statistic=rho,
        p_value=None,
        reject_null=bool(rho >= bound),
        extras={"spectral_radius": rho, "bound": bound, "beta": beta},
    )


def check_h5_intent_response_correlation(
    intents: NDArray[np.float64],
    responses: NDArray[np.float64],
    alpha: float = 0.05,
) -> HypothesisResult:
    """H5: Intent hinge angles predict response hinge angles (per-hinge Pearson r).

    Args:
        intents: shape (K, n_hinges) intent angles.
        responses: shape (K, n_hinges) response angles.
        alpha: Significance level.

    Returns:
        HypothesisResult for H5.

    Raises:
        ValueError: if shapes mismatch.
    """
    X = np.asarray(intents, dtype=np.float64)
    Y = np.asarray(responses, dtype=np.float64)
    if X.shape != Y.shape:
        raise ValueError("test_h5: intents and responses shapes must match")
    n_hinges = X.shape[1]
    rs: list[float] = []
    ps: list[float] = []
    for j in range(n_hinges):
        r, p = sp_stats.pearsonr(X[:, j], Y[:, j])
        rs.append(float(r))
        ps.append(float(p))
    mean_r = float(np.mean(rs))
    mean_p = float(np.mean(ps))
    return HypothesisResult(
        hypothesis="H5",
        description="Intent predicts response (per-hinge Pearson r)",
        statistic=mean_r,
        p_value=mean_p,
        reject_null=bool(mean_p < alpha),
        extras={"per_hinge_r": rs, "per_hinge_p": ps},
    )


def check_h6_symmetry(
    coupling: MentalCoupling,
    alpha: float = 0.05,
) -> HypothesisResult:
    """H6: Coupling matrix is symmetric (C == C^T).

    Args:
        coupling: Coupling to test.
        alpha: Significance level (unused; descriptive).

    Returns:
        HypothesisResult for H6.
    """
    M = coupling.matrix
    asym = float(np.linalg.norm(M - M.T, "fro"))
    return HypothesisResult(
        hypothesis="H6",
        description="C is symmetric (C == C^T)",
        statistic=asym,
        p_value=None,
        reject_null=bool(asym > 1e-9),
        extras={"asymmetry_frobenius": asym},
    )


def run_all_tests(
    coupling: MentalCoupling,
    intents: Optional[NDArray[np.float64]] = None,
    responses: Optional[NDArray[np.float64]] = None,
    group: Optional[SymmetryGroup] = None,
    beta: float = 0.5,
    alpha: float = 0.05,
) -> list[HypothesisResult]:
    """Run H1-H6 hypothesis tests on a coupling matrix.

    Args:
        coupling: Estimated or analytic coupling.
        intents: Optional (K, n) intent data for H5.
        responses: Optional (K, n) response data for H5.
        group: Optional symmetry group for H2.
        beta: Expected beta for H4 bound.
        alpha: Significance level.

    Returns:
        List of HypothesisResult objects (H1-H6).
    """
    results: list[HypothesisResult] = [
        check_h1_nonzero_beta(coupling, alpha=alpha),
        check_h2_equivariance(coupling, group=group, alpha=alpha),
        check_h3_rank_deficiency(coupling, alpha=alpha),
        check_h4_spectral_stability(coupling, beta=beta, alpha=alpha),
    ]
    if intents is not None and responses is not None:
        results.append(
            check_h5_intent_response_correlation(intents, responses, alpha=alpha)
        )
    results.append(check_h6_symmetry(coupling, alpha=alpha))
    return results
