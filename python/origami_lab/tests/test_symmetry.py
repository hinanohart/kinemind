"""V_4 symmetry group tests: Reynolds idempotency, group actions, equivariance."""

from __future__ import annotations

import numpy as np
import pytest

from origami_lab.symmetry import (
    GROUP_ELEMENTS,
    SymmetryGroup,
    equivariance_residual,
    group_action,
    group_action_matrix,
    klein_four_strip,
    reynolds_project,
)


def test_klein_four_strip_sigma_perm() -> None:
    """sigma_perm should be the reversal permutation."""
    n = 4
    G = klein_four_strip(n)
    expected = np.zeros((n, n))
    for i in range(n):
        expected[i, n - 1 - i] = 1.0
    assert np.allclose(G.sigma_perm, expected, atol=1e-12)


def test_klein_four_strip_invalid() -> None:
    """Non-positive integer should raise ValueError."""
    with pytest.raises(ValueError):
        klein_four_strip(0)
    with pytest.raises(ValueError):
        klein_four_strip(-1)


def test_group_action_identity() -> None:
    """'e' action is identity."""
    G = klein_four_strip(4)
    v = np.array([1.0, 2.0, 3.0, 4.0])
    result = group_action(G, "e", v)
    assert np.allclose(result, v, atol=1e-12)


def test_group_action_sigma() -> None:
    """'sigma' action reverses the vector."""
    G = klein_four_strip(4)
    v = np.array([1.0, 2.0, 3.0, 4.0])
    result = group_action(G, "sigma", v)
    assert np.allclose(result, v[::-1], atol=1e-12)


def test_group_action_tau() -> None:
    """'tau' action negates the vector."""
    G = klein_four_strip(4)
    v = np.array([1.0, 2.0, 3.0, 4.0])
    result = group_action(G, "tau", v)
    assert np.allclose(result, -v, atol=1e-12)


def test_group_action_sigmatau() -> None:
    """'sigmatau' action reverses and negates."""
    G = klein_four_strip(4)
    v = np.array([1.0, 2.0, 3.0, 4.0])
    result = group_action(G, "sigmatau", v)
    assert np.allclose(result, -v[::-1], atol=1e-12)


def test_group_action_sigma_involutory() -> None:
    """sigma^2 == identity."""
    G = klein_four_strip(5)
    v = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
    assert np.allclose(group_action(G, "sigma", group_action(G, "sigma", v)), v, atol=1e-12)


def test_group_action_tau_involutory() -> None:
    """tau^2 == identity."""
    G = klein_four_strip(5)
    v = np.array([1.0, -2.0, 3.0, -4.0, 5.0])
    assert np.allclose(group_action(G, "tau", group_action(G, "tau", v)), v, atol=1e-12)


def test_group_action_wrong_length_raises() -> None:
    """Wrong length vector should raise ValueError."""
    G = klein_four_strip(4)
    with pytest.raises(ValueError):
        group_action(G, "e", np.array([1.0, 2.0, 3.0]))


def test_reynolds_project_idempotent() -> None:
    """reynolds_project(M) applied twice should equal applied once (idempotency)."""
    rng = np.random.default_rng(0)
    n = 4
    G = klein_four_strip(n)
    M = rng.standard_normal((n, n))
    P = reynolds_project(G, M)
    PP = reynolds_project(G, P)
    assert np.allclose(P, PP, atol=1e-12), f"Max diff = {np.abs(P - PP).max()}"


def test_reynolds_project_identity_matrix() -> None:
    """Reynolds projection of identity should be identity (identity is V_4-invariant)."""
    n = 6
    G = klein_four_strip(n)
    I = np.eye(n)
    P = reynolds_project(G, I)
    assert np.allclose(P, I, atol=1e-12)


def test_reynolds_project_equivariant_output() -> None:
    """Output of reynolds_project should have zero equivariance residual."""
    rng = np.random.default_rng(1)
    n = 5
    G = klein_four_strip(n)
    M = rng.standard_normal((n, n))
    P = reynolds_project(G, M)
    residual = equivariance_residual(G, P)
    assert residual < 1e-10, f"Equivariance residual = {residual}"


def test_equivariance_residual_zero_for_mirror() -> None:
    """Mirror coupling matrix should have zero equivariance residual."""
    from origami_lab.coupling import mirror_coupling_matrix

    n = 6
    G = klein_four_strip(n)
    M = mirror_coupling_matrix(n, 0.4)
    residual = equivariance_residual(G, M)
    assert residual < 1e-10


def test_equivariance_residual_nonzero_for_random() -> None:
    """Random matrix should generally have nonzero equivariance residual."""
    rng = np.random.default_rng(2)
    n = 4
    G = klein_four_strip(n)
    M = rng.standard_normal((n, n))
    residual = equivariance_residual(G, M)
    assert residual > 1e-3


def test_group_action_matrix_is_orthogonal() -> None:
    """Representation matrices of each group element should be orthogonal."""
    G = klein_four_strip(4)
    for g in GROUP_ELEMENTS:
        P = group_action_matrix(G, g)
        assert np.allclose(P @ P.T, np.eye(4), atol=1e-12), (
            f"Group element {g}: P P^T is not identity"
        )


def test_reynolds_project_size_mismatch_raises() -> None:
    """Wrong matrix size should raise ValueError."""
    G = klein_four_strip(4)
    with pytest.raises(ValueError):
        reynolds_project(G, np.eye(5))
