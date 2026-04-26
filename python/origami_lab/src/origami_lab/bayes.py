"""Bayesian coupling matrix estimation using numpyro + JAX.

Implements the Schur-compressed reduced parametrisation for the V_4-equivariant
coupling matrix:

    C = c_+ Π_+ + c_- Π_-

where Π_+ and Π_- are the rank-n//2 projectors onto the symmetric (+1) and
anti-symmetric (-1) eigenspaces of the mirror permutation sigma.  This yields
only 3 free parameters (c_plus, c_minus, sigma) instead of n^2.

Observation model:
    y^(k) ~ Normal(C @ x^(k), σ^2 I)

Priors:
    c_plus  ~ Normal(1.0, 0.5)      # expected near 1 for self-fidelity
    c_minus ~ Normal(0.0, 0.5)      # mirror coupling term (expected small)
    sigma   ~ HalfNormal(0.2)       # observation noise

Posterior inference via NUTS (No-U-Turn Sampler) with numpyro.

References:
    Talts et al. (2018) "Validating Bayesian Inference Algorithms with
    Simulation-Based Calibration". arXiv:1804.06788.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

logger = logging.getLogger(__name__)


def _lazy_imports() -> tuple:
    """Lazily import numpyro/jax to avoid startup cost when bayes not used.

    Returns:
        Tuple (jnp, numpyro, dist, NUTS, MCMC, Predictive, rhat, ess).

    Raises:
        ImportError: if numpyro or jax are not installed.
    """
    try:
        import jax.numpy as jnp
        import numpyro
        import numpyro.distributions as dist
        from numpyro.infer import MCMC, NUTS, Predictive
        from numpyro.diagnostics import hpdi, effective_sample_size, split_gelman_rubin
    except ImportError as exc:
        raise ImportError(
            "bayes.py requires numpyro and jax: "
            "install with 'pip install origami-lab[bayes]'"
        ) from exc
    return jnp, numpyro, dist, NUTS, MCMC, Predictive, hpdi, effective_sample_size, split_gelman_rubin


def _build_mirror_projectors(
    n: int,
) -> tuple[NDArray[np.float64], NDArray[np.float64]]:
    """Build the symmetric (Π_+) and anti-symmetric (Π_-) projectors of sigma.

    The mirror permutation sigma reverses the hinge index vector.
    Its matrix representation P_sigma satisfies P_sigma @ v = v[::-1].
    The eigenspaces are:
        Π_+ = (I + P_sigma) / 2   (symmetric under mirror)
        Π_- = (I - P_sigma) / 2   (anti-symmetric under mirror)

    For even n, both projectors have rank n//2.
    For odd n, Π_+ has rank (n+1)//2, Π_- has rank (n-1)//2.

    Args:
        n: Number of hinges.

    Returns:
        (Pi_plus, Pi_minus) each shape (n, n).
    """
    I_n = np.eye(n, dtype=np.float64)
    # Build the mirror permutation matrix P_sigma.
    P_sigma = np.zeros((n, n), dtype=np.float64)
    for i in range(n):
        P_sigma[i, n - 1 - i] = 1.0
    Pi_plus = (I_n + P_sigma) / 2.0
    Pi_minus = (I_n - P_sigma) / 2.0
    return Pi_plus, Pi_minus


@dataclass(frozen=True)
class BayesianCouplingResult:
    """Output of :func:`fit_bayesian_coupling`.

    Attributes:
        posterior_samples: Dict of parameter name → ndarray of samples,
                           shape (num_chains * num_samples,).
        posterior_C_mean: Posterior mean of C, shape (n, n).
        posterior_C_lower: 2.5th percentile of posterior C, shape (n, n).
        posterior_C_upper: 97.5th percentile of posterior C, shape (n, n).
        credible_intervals: Dict mapping param name → (lower, upper) 95% HPDI.
        rhat_max: Maximum R-hat across all parameters (< 1.05 indicates convergence).
        ess_min: Minimum effective sample size across all parameters.
    """

    posterior_samples: dict[str, NDArray[np.float64]]
    posterior_C_mean: NDArray[np.float64]
    posterior_C_lower: NDArray[np.float64]
    posterior_C_upper: NDArray[np.float64]
    credible_intervals: dict[str, tuple[float, float]]
    rhat_max: float
    ess_min: float


def fit_bayesian_coupling(
    intents: NDArray[np.float64],
    responses: NDArray[np.float64],
    n_hinges: int,
    *,
    model: str = "general_v4",
    num_warmup: int = 500,
    num_samples: int = 1000,
    num_chains: int = 2,
    seed: int = 0,
) -> BayesianCouplingResult:
    """Fit a Bayesian coupling model using NUTS.

    The Schur-compressed V_4-equivariant model (``model="general_v4"``)
    parametrises C as:

        C = c_plus * Pi_plus + c_minus * Pi_minus

    where Pi_plus and Pi_minus are the projectors onto the symmetric and
    anti-symmetric eigenspaces of the mirror permutation.

    Args:
        intents: Intent angles shape (K, n_hinges).
        responses: Response angles shape (K, n_hinges).
        n_hinges: Number of hinges.
        model: Model identifier; currently only ``"general_v4"`` is supported.
        num_warmup: Number of NUTS warmup steps per chain (default 500).
        num_samples: Number of posterior samples per chain (default 1000).
        num_chains: Number of independent MCMC chains (default 2).
        seed: JAX random seed (default 0).

    Returns:
        BayesianCouplingResult with posterior samples, credible intervals,
        R-hat diagnostics, and ESS.

    Raises:
        ValueError: if inputs are inconsistent or model is unsupported.
        ImportError: if numpyro or jax are not installed.
    """
    if model != "general_v4":
        raise ValueError(
            f"fit_bayesian_coupling: unsupported model '{model}'; "
            "only 'general_v4' is currently implemented"
        )
    X = np.asarray(intents, dtype=np.float64)
    Y = np.asarray(responses, dtype=np.float64)
    if X.ndim != 2 or Y.ndim != 2:
        raise ValueError("fit_bayesian_coupling: intents and responses must be 2-D")
    if X.shape != Y.shape:
        raise ValueError("fit_bayesian_coupling: intents and responses shapes disagree")
    K, n = X.shape
    if n != n_hinges:
        raise ValueError(
            f"fit_bayesian_coupling: column count {n} does not match n_hinges={n_hinges}"
        )
    if K == 0:
        raise ValueError("fit_bayesian_coupling: at least one trial is required")

    jnp, numpyro, dist, NUTS, MCMC, Predictive, hpdi, ess_fn, rhat_fn = _lazy_imports()
    import jax
    import jax.numpy as jnp  # re-import for use below

    Pi_plus, Pi_minus = _build_mirror_projectors(n_hinges)

    # Convert to JAX arrays.
    X_jax = jnp.array(X)
    Y_jax = jnp.array(Y)
    Pi_plus_jax = jnp.array(Pi_plus)
    Pi_minus_jax = jnp.array(Pi_minus)

    def _model(X_data: jnp.ndarray, Y_data: jnp.ndarray) -> None:
        """numpyro model: Schur-compressed V_4 coupling observation model."""
        c_plus = numpyro.sample("c_plus", dist.Normal(1.0, 0.5))
        c_minus = numpyro.sample("c_minus", dist.Normal(0.0, 0.5))
        sigma = numpyro.sample("sigma", dist.HalfNormal(0.2))

        # Coupling matrix via Schur projectors.
        C = c_plus * Pi_plus_jax + c_minus * Pi_minus_jax  # (n, n)

        # Predicted responses: (K, n) = X_data @ C^T.
        mu = X_data @ C.T  # shape (K, n)

        with numpyro.plate("obs", X_data.shape[0]):
            numpyro.sample(
                "y",
                dist.Normal(mu, sigma).to_event(1),
                obs=Y_data,
            )

    rng_key = jax.random.PRNGKey(seed)
    kernel = NUTS(_model)
    mcmc = MCMC(
        kernel,
        num_warmup=num_warmup,
        num_samples=num_samples,
        num_chains=num_chains,
        progress_bar=False,
    )
    mcmc.run(rng_key, X_jax, Y_jax)

    raw_samples = mcmc.get_samples(group_by_chain=False)

    # Compute diagnostics.
    # R-hat and ESS: group_by_chain=True for diagnostics.
    chained_samples = mcmc.get_samples(group_by_chain=True)
    rhat_values: list[float] = []
    ess_values: list[float] = []
    for param in ("c_plus", "c_minus", "sigma"):
        s = np.array(chained_samples[param])  # (num_chains, num_samples)
        # numpyro diagnostics expect shape (num_chains, num_samples, num_params).
        s_expanded = s[..., None]  # (num_chains, num_samples, 1)
        rhat_arr = np.array(rhat_fn(s_expanded))  # shape (1,)
        ess_arr = np.array(ess_fn(s_expanded))    # shape (1,)
        rhat_val = float(rhat_arr.flat[0])
        ess_val = float(ess_arr.flat[0])
        rhat_values.append(rhat_val)
        ess_values.append(ess_val)
        logger.debug("  %s: R-hat=%.4f, ESS=%.1f", param, rhat_val, ess_val)

    rhat_max = float(max(rhat_values))
    ess_min = float(min(ess_values))

    # Posterior credible intervals (95% HPDI).
    credible_intervals: dict[str, tuple[float, float]] = {}
    for param in ("c_plus", "c_minus", "sigma"):
        s = np.array(raw_samples[param])
        interval = hpdi(s, prob=0.95)
        credible_intervals[param] = (float(interval[0]), float(interval[1]))

    # Posterior distribution of C.
    c_plus_samples = np.array(raw_samples["c_plus"])   # (total_samples,)
    c_minus_samples = np.array(raw_samples["c_minus"])  # (total_samples,)
    total_samples = len(c_plus_samples)

    # Broadcast: C_samples[k] = c_plus[k]*Pi_plus + c_minus[k]*Pi_minus
    # Shape: (total_samples, n, n)
    C_samples = (
        c_plus_samples[:, None, None] * Pi_plus[None, :, :]
        + c_minus_samples[:, None, None] * Pi_minus[None, :, :]
    )

    posterior_C_mean = C_samples.mean(axis=0)
    posterior_C_lower = np.percentile(C_samples, 2.5, axis=0)
    posterior_C_upper = np.percentile(C_samples, 97.5, axis=0)

    # Convert raw_samples to pure numpy.
    posterior_samples_np: dict[str, NDArray[np.float64]] = {
        k: np.array(v, dtype=np.float64) for k, v in raw_samples.items()
    }

    logger.info(
        "fit_bayesian_coupling: R-hat_max=%.4f, ESS_min=%.1f, total_samples=%d",
        rhat_max,
        ess_min,
        total_samples,
    )

    return BayesianCouplingResult(
        posterior_samples=posterior_samples_np,
        posterior_C_mean=posterior_C_mean,
        posterior_C_lower=posterior_C_lower,
        posterior_C_upper=posterior_C_upper,
        credible_intervals=credible_intervals,
        rhat_max=rhat_max,
        ess_min=ess_min,
    )


def simulation_based_calibration(
    n_hinges: int,
    n_trials: int,
    *,
    n_replicates: int = 50,
    seed: int = 0,
) -> dict[str, NDArray[np.float64]]:
    """Simulation-based calibration (SBC) rank histograms.

    For each replicate:
      1. Draw ground-truth parameters from the prior.
      2. Simulate a dataset of n_trials observations.
      3. Run NUTS posterior inference.
      4. Compute the rank of the ground-truth parameter among posterior samples.

    The rank histograms should be uniform under a well-calibrated Bayesian model
    (Talts et al. 2018, KS test p-value > 0.05).

    Args:
        n_hinges: Number of hinges (strip dimension).
        n_trials: Number of observed (intent, response) pairs per replicate.
        n_replicates: Number of SBC replicates (default 50).
        seed: Random seed for reproducibility (default 0).

    Returns:
        Dict with keys 'ranks_c_plus', 'ranks_c_minus', 'ranks_sigma',
        each an ndarray of shape (n_replicates,) with integer ranks in
        [0, num_posterior_samples].

    Raises:
        ImportError: if numpyro or jax are not installed.
    """
    jnp, numpyro, dist, NUTS, MCMC, Predictive, hpdi, ess_fn, rhat_fn = _lazy_imports()
    import jax
    import jax.numpy as jnp  # re-import

    Pi_plus, Pi_minus = _build_mirror_projectors(n_hinges)
    rng = np.random.default_rng(seed)

    ranks: dict[str, list[int]] = {"c_plus": [], "c_minus": [], "sigma": []}

    for rep in range(n_replicates):
        # Sample prior ground truth.
        c_plus_true = float(rng.normal(1.0, 0.5))
        c_minus_true = float(rng.normal(0.0, 0.5))
        sigma_true = abs(float(rng.normal(0.0, 0.2))) + 1e-6  # HalfNormal approx

        C_true = c_plus_true * Pi_plus + c_minus_true * Pi_minus

        # Simulate observations.
        X_sim = rng.standard_normal((n_trials, n_hinges))
        noise = rng.standard_normal((n_trials, n_hinges)) * sigma_true
        Y_sim = (C_true @ X_sim.T).T + noise

        # Run posterior inference with fewer samples for SBC efficiency.
        try:
            result = fit_bayesian_coupling(
                X_sim,
                Y_sim,
                n_hinges,
                num_warmup=200,
                num_samples=500,
                num_chains=1,
                seed=int(rng.integers(0, 2**31)),
            )
        except Exception as exc:
            logger.warning("SBC replicate %d failed: %s", rep, exc)
            continue

        # Compute rank: number of posterior samples less than ground truth.
        for param, true_val in [
            ("c_plus", c_plus_true),
            ("c_minus", c_minus_true),
            ("sigma", sigma_true),
        ]:
            samples = result.posterior_samples[param]
            rank = int(np.sum(samples < true_val))
            ranks[param].append(rank)

        logger.debug("SBC replicate %d/%d complete", rep + 1, n_replicates)

    return {f"ranks_{k}": np.array(v, dtype=np.int64) for k, v in ranks.items()}
