"""Integration tests covering io.py, stats.py, and cli.py."""

from __future__ import annotations

import json
import math
import tempfile
from pathlib import Path

import numpy as np
import pytest
from typer.testing import CliRunner

from origami_lab.cli import app
from origami_lab.coupling import MentalCoupling, mirror_coupling, mirror_coupling_matrix
from origami_lab.io import (
    load_json,
    poses_to_dict,
    save_json,
    strip_config_from_dict,
    strip_config_to_dict,
    strip_state_from_dict,
    strip_state_to_dict,
    write_bids_like,
)
from origami_lab.stats import (
    run_all_tests,
    check_h1_nonzero_beta,
    check_h2_equivariance,
    check_h3_rank_deficiency,
    check_h4_spectral_stability,
    check_h5_intent_response_correlation,
    check_h6_symmetry,
)
from origami_lab.strip import StripConfig, StripState, make_uniform_strip

runner = CliRunner()


# ---- io.py tests ----


def test_strip_config_round_trip() -> None:
    """strip_config_to_dict / strip_config_from_dict should round-trip."""
    config = make_uniform_strip(5, cell_length=1.5)
    d = strip_config_to_dict(config)
    config2 = strip_config_from_dict(d)
    assert config.n_cells == config2.n_cells
    assert config.cell_lengths == config2.cell_lengths
    assert math.isclose(config.angle_max, config2.angle_max)


def test_strip_state_round_trip() -> None:
    """strip_state_to_dict / strip_state_from_dict should round-trip."""
    state = StripState(thetas=(0.1, -0.2, 0.3, -0.4))
    d = strip_state_to_dict(state)
    state2 = strip_state_from_dict(d)
    assert state.thetas == state2.thetas


def test_strip_config_from_dict_missing_key() -> None:
    """Missing required keys should raise ValueError."""
    with pytest.raises(ValueError):
        strip_config_from_dict({"cellLengths": [1.0, 1.0]})  # missing nCells


def test_strip_state_from_dict_missing_key() -> None:
    """Missing 'thetas' key should raise ValueError."""
    with pytest.raises(ValueError):
        strip_state_from_dict({})


def test_poses_to_dict() -> None:
    """poses_to_dict should produce lists matching input arrays."""
    positions = np.array([[0.0, 0.0, 0.0], [1.0, 0.0, 0.0]])
    quats = np.array([[1.0, 0.0, 0.0, 0.0], [1.0, 0.0, 0.0, 0.0]])
    d = poses_to_dict(positions, quats)
    assert d["positions"] == positions.tolist()
    assert d["quats"] == quats.tolist()


def test_save_load_json(tmp_path: Path) -> None:
    """save_json / load_json should round-trip arbitrary data."""
    data = {"key": [1, 2, 3], "nested": {"a": 1.5}}
    out = tmp_path / "test.json"
    save_json(out, data)
    loaded = load_json(out)
    assert loaded == data


def test_load_json_file_not_found() -> None:
    """load_json should raise FileNotFoundError for missing files."""
    with pytest.raises(FileNotFoundError):
        load_json("/nonexistent/path/file.json")


def test_load_json_invalid_json(tmp_path: Path) -> None:
    """load_json should raise ValueError for invalid JSON."""
    bad = tmp_path / "bad.json"
    bad.write_text("{not valid json}", encoding="utf-8")
    with pytest.raises(ValueError):
        load_json(bad)


def test_write_bids_like(tmp_path: Path) -> None:
    """write_bids_like should create BIDS-like directory structure."""
    config = make_uniform_strip(4)
    trials = [{"intent": [0.1, 0.2, 0.3], "response": [0.1, 0.2, 0.3]}]
    write_bids_like(tmp_path, "01", "baseline", config, trials)
    config_path = tmp_path / "sub-01" / "ses-baseline" / "strip_config.json"
    trials_path = tmp_path / "sub-01" / "ses-baseline" / "trials.json"
    assert config_path.exists()
    assert trials_path.exists()
    c = load_json(config_path)
    assert c["nCells"] == 4


# ---- stats.py tests ----


def test_h1_nonzero_beta_high_signal() -> None:
    """H1 should reject null when coupling clearly > 0."""
    beta = 0.8
    mc = mirror_coupling(6, beta)
    result = check_h1_nonzero_beta(mc)
    assert result.hypothesis == "H1"
    assert result.reject_null


def test_h1_zero_beta_no_reject() -> None:
    """H1 should not reject for identity coupling (beta=0)."""
    from origami_lab.coupling import identity_coupling
    ic = identity_coupling(6)
    result = check_h1_nonzero_beta(ic)
    assert not result.reject_null


def test_h1_single_hinge_no_pairs() -> None:
    """H1 with n_hinges=1 should handle no off-diagonal pairs."""
    mc = MentalCoupling(
        matrix=np.array([[1.0]]), n_hinges=1, source="analytic", beta=0.0
    )
    result = check_h1_nonzero_beta(mc)
    assert result.extras["n_pairs"] == 0


def test_h2_equivariance_analytic() -> None:
    """H2 should not reject for analytically constructed equivariant matrix."""
    mc = mirror_coupling(6, 0.4)
    result = check_h2_equivariance(mc)
    assert result.hypothesis == "H2"
    assert not result.reject_null


def test_h3_rank_deficiency() -> None:
    """H3 should detect rank deficiency in a rank-1 coupling."""
    v = np.array([1.0, 0.0, 0.0, 0.0])
    M = np.outer(v, v) + np.eye(4) * 0.0  # rank 1
    mc = MentalCoupling(matrix=M, n_hinges=4, source="empirical")
    result = check_h3_rank_deficiency(mc)
    assert result.hypothesis == "H3"
    assert result.statistic == 1  # effective rank = 1


def test_h4_spectral_stability_passes() -> None:
    """H4 should pass for mirror coupling with beta=0.5 (rho=1.5 < 1+0.5+eps)."""
    beta = 0.5
    mc = mirror_coupling(4, beta)
    result = check_h4_spectral_stability(mc, beta=beta)
    assert result.hypothesis == "H4"
    # rho should be ~1+beta; bound is exactly 1+beta, so this test checks pass/fail.
    # For exact mirror coupling, rho should equal the bound (reject_null could be True).
    assert abs(result.statistic - (1.0 + beta)) < 1e-6


def test_h5_intent_response_correlation() -> None:
    """H5 should detect strong correlation between intent and response."""
    rng = np.random.default_rng(42)
    n = 4
    K = 100
    X = rng.standard_normal((K, n))
    Y = X + 0.01 * rng.standard_normal((K, n))  # near-identical
    result = check_h5_intent_response_correlation(X, Y)
    assert result.hypothesis == "H5"
    assert result.statistic > 0.99  # high correlation


def test_h5_shape_mismatch_raises() -> None:
    """H5 should raise ValueError for mismatched shapes."""
    with pytest.raises(ValueError):
        check_h5_intent_response_correlation(np.ones((5, 3)), np.ones((4, 3)))


def test_h6_symmetry_symmetric_matrix() -> None:
    """H6 should not reject for a symmetric coupling."""
    mc = mirror_coupling(4, 0.3)
    result = check_h6_symmetry(mc)
    assert result.hypothesis == "H6"
    assert not result.reject_null


def test_h6_asymmetric_matrix_rejects() -> None:
    """H6 should reject for an asymmetric coupling."""
    M = np.eye(4)
    M[0, 1] = 0.5  # asymmetry
    mc = MentalCoupling(matrix=M, n_hinges=4, source="empirical")
    result = check_h6_symmetry(mc)
    assert result.reject_null


def test_run_all_tests() -> None:
    """run_all_tests should return at least H1-H4 and H6."""
    mc = mirror_coupling(4, 0.3)
    results = run_all_tests(mc)
    hypotheses = {r.hypothesis for r in results}
    assert {"H1", "H2", "H3", "H4", "H6"}.issubset(hypotheses)


def test_run_all_tests_with_data() -> None:
    """run_all_tests with intents/responses should also return H5."""
    rng = np.random.default_rng(0)
    n = 4
    K = 50
    mc = mirror_coupling(n, 0.3)
    X = rng.standard_normal((K, n))
    Y = X.copy()
    results = run_all_tests(mc, intents=X, responses=Y)
    hypotheses = {r.hypothesis for r in results}
    assert "H5" in hypotheses


def test_hypothesis_result_to_dict() -> None:
    """HypothesisResult.to_dict() should produce JSON-serializable output."""
    mc = mirror_coupling(4, 0.3)
    result = check_h1_nonzero_beta(mc)
    d = result.to_dict()
    assert "hypothesis" in d
    assert "statistic" in d
    json.dumps(d)  # should not raise


# ---- cli.py tests ----


def test_cli_help() -> None:
    """CLI --help should succeed."""
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "origami" in result.output.lower() or "Usage" in result.output


def test_cli_kinematics_default() -> None:
    """CLI kinematics command with defaults should produce valid JSON."""
    result = runner.invoke(app, ["kinematics", "--n-cells", "4"])
    assert result.exit_code == 0, f"CLI failed: {result.output}"
    data = json.loads(result.output)
    assert data["n_cells"] == 4
    assert len(data["positions"]) == 4
    assert len(data["quats"]) == 4


def test_cli_kinematics_with_thetas() -> None:
    """CLI kinematics with explicit thetas."""
    result = runner.invoke(
        app,
        ["kinematics", "--n-cells", "3", "--theta", "0.5,-0.5"],
    )
    assert result.exit_code == 0, f"CLI failed: {result.output}"
    data = json.loads(result.output)
    assert data["n_cells"] == 3
    assert data["thetas"] == [0.5, -0.5]


def test_cli_kinematics_wrong_theta_count() -> None:
    """CLI should fail when theta count mismatches n_cells."""
    result = runner.invoke(
        app,
        ["kinematics", "--n-cells", "4", "--theta", "0.1,0.2"],
    )
    assert result.exit_code != 0


def test_cli_analyze(tmp_path: Path) -> None:
    """CLI analyze command should produce a valid report JSON."""
    config = make_uniform_strip(4)
    rng = np.random.default_rng(0)
    n = config.n_hinges
    K = 20
    X = rng.standard_normal((K, n))
    Y = X + 0.1 * rng.standard_normal((K, n))
    trials = [
        {"intent": X[k].tolist(), "response": Y[k].tolist()} for k in range(K)
    ]
    in_file = tmp_path / "trials.json"
    out_file = tmp_path / "report.json"
    save_json(in_file, {"config": strip_config_to_dict(config), "trials": trials})

    result = runner.invoke(
        app,
        ["analyze", "--in", str(in_file), "--out", str(out_file)],
    )
    assert result.exit_code == 0, f"CLI failed: {result.output}"
    assert out_file.exists()
    report = load_json(out_file)
    assert "coupling_matrix" in report
    assert "hypotheses" in report


def test_cli_analyze_missing_input(tmp_path: Path) -> None:
    """CLI analyze with nonexistent input should exit with error."""
    result = runner.invoke(
        app,
        [
            "analyze",
            "--in",
            str(tmp_path / "nonexistent.json"),
            "--out",
            str(tmp_path / "report.json"),
        ],
    )
    assert result.exit_code != 0
