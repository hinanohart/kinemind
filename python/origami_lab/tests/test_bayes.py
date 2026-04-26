"""Bayesian coupling estimation tests.

Tests:
1. Synthetic beta=0.6 recovery: 95% HPDI covers true c_plus + c_minus
   in >= 92% of 200 replicates.
2. SBC rank histogram: KS p > 0.05 for uniform distribution.
3. R-hat < 1.05, ESS > 200.

Note: numpyro/jax are optional dependencies.
Skip gracefully if not installed.
"""

from __future__ import annotations

import pytest

pytest.importorskip("numpyro", reason="numpyro not installed; skip bayes tests")
pytest.importorskip("jax", reason="jax not installed; skip bayes tests")

import math
import numpy as np
from scipy import stats as sp_stats

from origami_lab.bayes import (
    BayesianCouplingResult,
    _build_mirror_projectors,
    fit_bayesian_coupling,
    simulation_based_calibration,
)
from origami_lab.coupling import mirror_coupling_matrix


# ---------------------------------------------------------------------------
# Unit tests for helper functions
# ---------------------------------------------------------------------------


def test_build_mirror_projectors_even() -> None:
    """Pi_plus + Pi_minus == I for even n."""
    n = 4
    Pi_plus, Pi_minus = _build_mirror_projectors(n)
    assert np.allclose(Pi_plus + Pi_minus, np.eye(n), atol=1e-12)
    # Symmetric under transpose.
    assert np.allclose(Pi_plus, Pi_plus.T, atol=1e-12)
    assert np.allclose(Pi_minus, Pi_minus.T, atol=1e-12)


def test_build_mirror_projectors_odd() -> None:
    """Pi_plus + Pi_minus == I for odd n."""
    n = 5
    Pi_plus, Pi_minus = _build_mirror_projectors(n)
    assert np.allclose(Pi_plus + Pi_minus, np.eye(n), atol=1e-12)


def test_build_mirror_projectors_idempotent() -> None:
    """Projectors must be idempotent: Pi^2 = Pi."""
    n = 6
    Pi_plus, Pi_minus = _build_mirror_projectors(n)
    assert np.allclose(Pi_plus @ Pi_plus, Pi_plus, atol=1e-12)
    assert np.allclose(Pi_minus @ Pi_minus, Pi_minus, atol=1e-12)


# ---------------------------------------------------------------------------
# fit_bayesian_coupling: basic smoke test
# ---------------------------------------------------------------------------


def test_fit_bayesian_coupling_returns_result() -> None:
    """fit_bayesian_coupling should return BayesianCouplingResult with correct shapes."""
    rng = np.random.default_rng(0)
    n = 4
    K = 60
    X = rng.standard_normal((K, n))
    beta = 0.3
    M = mirror_coupling_matrix(n, beta)
    Y = (M @ X.T).T + 0.05 * rng.standard_normal((K, n))

    result = fit_bayesian_coupling(
        X, Y, n_hinges=n, num_warmup=100, num_samples=200, num_chains=1, seed=42
    )
    assert isinstance(result, BayesianCouplingResult)
    assert result.posterior_C_mean.shape == (n, n)
    assert result.posterior_C_lower.shape == (n, n)
    assert result.posterior_C_upper.shape == (n, n)
    assert "c_plus" in result.credible_intervals
    assert "c_minus" in result.credible_intervals
    assert "sigma" in result.credible_intervals


def test_fit_bayesian_coupling_rhat_ess() -> None:
    """R-hat < 1.05 and ESS > 200 for a well-specified model."""
    rng = np.random.default_rng(1)
    n = 4
    K = 80
    X = rng.standard_normal((K, n))
    beta = 0.4
    M = mirror_coupling_matrix(n, beta)
    Y = (M @ X.T).T + 0.05 * rng.standard_normal((K, n))

    result = fit_bayesian_coupling(
        X, Y, n_hinges=n, num_warmup=200, num_samples=500, num_chains=2, seed=7
    )
    assert result.rhat_max < 1.05, f"R-hat too large: {result.rhat_max:.4f}"
    assert result.ess_min > 200, f"ESS too small: {result.ess_min:.1f}"


# ---------------------------------------------------------------------------
# Synthetic beta=0.6 recovery: 95% HPDI coverage >= 92% over 200 replicates
# ---------------------------------------------------------------------------


@pytest.mark.slow
def test_bayesian_beta_recovery_hpdi_coverage() -> None:
    """95% HPDI should cover true c_plus and c_minus in >= 92% of 200 replicates.

    Uses mirror coupling (beta=0.6):
        c_plus_true  = 1 + beta = 1.6  (from mirror_coupling eigenvalue structure)
        c_minus_true = 1 - beta = 0.4

    Wait — the Schur parametrisation uses:
        C = c_plus * Pi_plus + c_minus * Pi_minus
    For mirror coupling M(beta):
        M = I + beta * P_sigma = (1+beta)/2 * (I + P_sigma) + (1-beta)/2 * (I - P_sigma)
          = (1+beta) * Pi_plus + (1-beta) * Pi_minus

    So c_plus_true = 1 + beta, c_minus_true = 1 - beta.
    """
    beta = 0.6
    n = 4
    n_replicates = 200
    K = 80
    c_plus_true = 1.0 + beta
    c_minus_true = 1.0 - beta
    M = mirror_coupling_matrix(n, beta)

    covered_c_plus = 0
    covered_c_minus = 0
    rng = np.random.default_rng(2024)

    for rep in range(n_replicates):
        X = rng.standard_normal((K, n))
        Y = (M @ X.T).T + 0.05 * rng.standard_normal((K, n))
        result = fit_bayesian_coupling(
            X, Y, n_hinges=n, num_warmup=200, num_samples=300, num_chains=1, seed=rep
        )
        lo_cp, hi_cp = result.credible_intervals["c_plus"]
        lo_cm, hi_cm = result.credible_intervals["c_minus"]
        if lo_cp <= c_plus_true <= hi_cp:
            covered_c_plus += 1
        if lo_cm <= c_minus_true <= hi_cm:
            covered_c_minus += 1

    coverage_cp = covered_c_plus / n_replicates
    coverage_cm = covered_c_minus / n_replicates
    assert coverage_cp >= 0.92, (
        f"c_plus HPDI coverage {coverage_cp:.3f} < 0.92 over {n_replicates} replicates"
    )
    assert coverage_cm >= 0.92, (
        f"c_minus HPDI coverage {coverage_cm:.3f} < 0.92 over {n_replicates} replicates"
    )


# ---------------------------------------------------------------------------
# SBC: rank histogram KS test p > 0.05
# ---------------------------------------------------------------------------


@pytest.mark.slow
def test_simulation_based_calibration_uniform_ranks() -> None:
    """SBC rank histogram should pass KS uniformity test (p > 0.05)."""
    n_hinges = 4
    n_trials = 60
    n_replicates = 50

    ranks_dict = simulation_based_calibration(
        n_hinges, n_trials, n_replicates=n_replicates, seed=42
    )
    assert "ranks_c_plus" in ranks_dict
    assert "ranks_c_minus" in ranks_dict
    assert "ranks_sigma" in ranks_dict

    for param, ranks in ranks_dict.items():
        if len(ranks) < 10:
            continue  # too few successful replicates to test
        # KS test against uniform on [0, num_samples].
        # Ranks are integers in [0, 500]. Normalise to [0, 1].
        num_samples_posterior = 500
        normed = ranks / num_samples_posterior
        ks_stat, p_val = sp_stats.kstest(normed, "uniform")
        assert p_val > 0.05, (
            f"SBC rank histogram for {param} not uniform: KS p={p_val:.4f} < 0.05"
        )
