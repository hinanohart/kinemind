"""Tests for power analysis module (H1 Monte Carlo simulation)."""

from __future__ import annotations

import math

import pytest

from origami_lab.power import (
    PowerResult,
    _wilson_ci,
    power_curve_h1,
    power_h1_lmm,
)


# ---------------------------------------------------------------------------
# Wilson CI helper
# ---------------------------------------------------------------------------


class TestWilsonCi:
    def test_all_successes(self) -> None:
        lo, hi = _wilson_ci(100, 100)
        assert lo > 0.9
        assert hi <= 1.0

    def test_no_successes(self) -> None:
        lo, hi = _wilson_ci(0, 100)
        assert lo >= 0.0
        assert hi < 0.1

    def test_half_successes_contains_half(self) -> None:
        lo, hi = _wilson_ci(50, 100)
        assert lo < 0.5 < hi

    def test_zero_n_returns_full_interval(self) -> None:
        lo, hi = _wilson_ci(0, 0)
        assert lo == 0.0
        assert hi == 1.0

    def test_bounds_in_unit_interval(self) -> None:
        for k in range(0, 101, 10):
            lo, hi = _wilson_ci(k, 100)
            assert 0.0 <= lo <= hi <= 1.0


# ---------------------------------------------------------------------------
# power_h1_lmm — basic contract
# ---------------------------------------------------------------------------


class TestPowerH1Lmm:
    def test_returns_power_result(self) -> None:
        result = power_h1_lmm(n_subjects=20, n_replicates=10, seed=42)
        assert isinstance(result, PowerResult)

    def test_hypothesis_id(self) -> None:
        result = power_h1_lmm(n_subjects=20, n_replicates=10, seed=0)
        assert result.hypothesis_id == "H1"

    def test_power_in_unit_interval(self) -> None:
        result = power_h1_lmm(n_subjects=20, n_replicates=20, seed=1)
        assert 0.0 <= result.power <= 1.0

    def test_ci_contains_power(self) -> None:
        result = power_h1_lmm(n_subjects=30, n_replicates=20, seed=2)
        lo, hi = result.confidence_interval
        assert lo <= result.power <= hi

    def test_n_replicates_recorded(self) -> None:
        result = power_h1_lmm(n_subjects=20, n_replicates=15, seed=3)
        assert result.n_replicates == 15

    def test_effect_size_recorded(self) -> None:
        result = power_h1_lmm(n_subjects=20, n_replicates=10, beta_logn=0.50, seed=4)
        assert math.isclose(result.effect_size, 0.50)

    def test_larger_effect_higher_power(self) -> None:
        """Larger beta_logN should yield higher (or equal) power at same N."""
        small = power_h1_lmm(n_subjects=60, n_replicates=50, beta_logn=0.10, seed=99)
        large = power_h1_lmm(n_subjects=60, n_replicates=50, beta_logn=0.60, seed=99)
        # Allow a small margin for Monte Carlo variance
        assert large.power >= small.power - 0.10

    def test_zero_n_subjects_raises(self) -> None:
        with pytest.raises(ValueError, match="n_subjects must be positive"):
            power_h1_lmm(n_subjects=0, n_replicates=10)

    def test_zero_replicates_raises(self) -> None:
        with pytest.raises(ValueError, match="n_replicates must be positive"):
            power_h1_lmm(n_subjects=10, n_replicates=0)

    def test_invalid_alpha_raises(self) -> None:
        with pytest.raises(ValueError, match="alpha must be in"):
            power_h1_lmm(n_subjects=10, n_replicates=5, alpha=1.5)

    def test_summary_line_contains_n(self) -> None:
        result = power_h1_lmm(n_subjects=42, n_replicates=10, seed=5)
        assert "42" in result.summary_line()

    def test_reproducible_with_same_seed(self) -> None:
        r1 = power_h1_lmm(n_subjects=30, n_replicates=20, seed=77)
        r2 = power_h1_lmm(n_subjects=30, n_replicates=20, seed=77)
        assert r1.power == r2.power


# ---------------------------------------------------------------------------
# power_curve_h1
# ---------------------------------------------------------------------------


class TestPowerCurveH1:
    def test_returns_dict_with_all_sizes(self) -> None:
        sizes = [20, 40, 60]
        results = power_curve_h1(sample_sizes=sizes, n_replicates=10, seed=0)
        assert set(results.keys()) == set(sizes)

    def test_all_results_are_power_results(self) -> None:
        results = power_curve_h1(sample_sizes=[20, 40], n_replicates=10, seed=1)
        for r in results.values():
            assert isinstance(r, PowerResult)

    def test_empty_sample_sizes_raises(self) -> None:
        with pytest.raises(ValueError, match="must not be empty"):
            power_curve_h1(sample_sizes=[], n_replicates=10)

    def test_non_positive_sample_size_raises(self) -> None:
        with pytest.raises(ValueError, match="must be positive"):
            power_curve_h1(sample_sizes=[0, 20], n_replicates=10)

    def test_monotone_tendency_large_n(self) -> None:
        """Power should generally increase with N (allow Monte Carlo noise)."""
        results = power_curve_h1(
            sample_sizes=[30, 80, 160],
            beta_logn=0.40,
            n_replicates=80,
            seed=42,
        )
        powers = [results[n].power for n in [30, 80, 160]]
        # Not strictly monotone due to MC variance; allow one inversion
        inversions = sum(1 for a, b in zip(powers, powers[1:]) if a > b + 0.10)
        assert inversions == 0, f"Power curve not roughly monotone: {powers}"

    def test_duplicates_deduplicated(self) -> None:
        """Duplicate sizes should appear only once in output."""
        results = power_curve_h1(sample_sizes=[30, 30, 60], n_replicates=10, seed=0)
        assert len(results) == 2
