from __future__ import annotations

import math

import pytest

from app.audit.stats import (
    bootstrap_ci,
    bootstrap_reduction,
    cohen_dz,
    holm_adjust,
    mean_gap,
    paired_permutation_test,
    pairwise_accuracy,
    repeat_noise_floor,
    shortlist_ratio,
    stable_seed,
)


def test_mean_gap() -> None:
    assert mean_gap([2.0, 4.0]) == pytest.approx(3.0)
    assert mean_gap([]) == 0.0


def test_bootstrap_ci_constant_values() -> None:
    low, high = bootstrap_ci([1.0, 1.0, 1.0], n_resamples=200, seed=1)
    assert low == pytest.approx(1.0)
    assert high == pytest.approx(1.0)


def test_bootstrap_ci_is_deterministic() -> None:
    values = [-0.6, -0.4, -0.5, -0.7, -0.45]
    assert bootstrap_ci(values, n_resamples=500, seed=42) == bootstrap_ci(
        values, n_resamples=500, seed=42
    )


def test_paired_permutation_detects_consistent_gap() -> None:
    values = [-0.5, -0.55, -0.45, -0.52, -0.48, -0.51, -0.49, -0.53]
    assert paired_permutation_test(values, n_resamples=500, seed=7) < 0.05


def test_paired_permutation_accepts_null() -> None:
    values = [-0.2, 0.1, 0.05, -0.1, 0.15, -0.05]
    assert paired_permutation_test(values, n_resamples=500, seed=7) > 0.05


def test_cohen_dz() -> None:
    assert cohen_dz([1.0, 2.0, 3.0]) == pytest.approx(2.0)
    assert cohen_dz([1.0, 1.0, 1.0]) == 0.0


def test_holm_adjust_known_values() -> None:
    adjusted = holm_adjust([0.01, 0.04, 0.03])
    assert adjusted == pytest.approx([0.03, 0.06, 0.06])


def test_shortlist_ratio() -> None:
    assert shortlist_ratio(0.6, 0.8) == pytest.approx(0.75)
    assert shortlist_ratio(0.2, 0.0) is None


def test_repeat_noise_floor_known_values() -> None:
    floor = repeat_noise_floor([[1.0, 2.0, 3.0], [1.0, 2.0, 3.0]])
    assert floor == pytest.approx(1.96)
    assert repeat_noise_floor([[5.0]]) == 0.0


def test_pairwise_accuracy_known_orders() -> None:
    accuracy, auc, n_pairs = pairwise_accuracy([1.0, 2.0, 3.0], [1, 2, 3])
    assert accuracy == pytest.approx(1.0)
    assert auc == pytest.approx(1.0)
    assert n_pairs == 3

    accuracy, _, _ = pairwise_accuracy([3.0, 2.0, 1.0], [1, 2, 3])
    assert accuracy == pytest.approx(0.0)

    accuracy, _, _ = pairwise_accuracy([5.0, 5.0, 5.0], [1, 2, 3])
    assert accuracy == pytest.approx(0.5)


def test_pairwise_accuracy_ignores_same_tier_pairs() -> None:
    accuracy, _, n_pairs = pairwise_accuracy([1.0, 2.0, 3.0], [1, 1, 1])
    assert accuracy == 0.5
    assert n_pairs == 0


def test_bootstrap_reduction_known_values() -> None:
    baseline = [-0.5, -0.5, -0.5, -0.5]
    mitigated = [0.0, 0.0, 0.0, 0.0]
    reduction, low, high = bootstrap_reduction(baseline, mitigated, n_resamples=200, seed=3)
    assert reduction == pytest.approx(0.5)
    assert low == pytest.approx(0.5)
    assert high == pytest.approx(0.5)


def test_bootstrap_reduction_returns_nan_for_mismatch() -> None:
    reduction, low, high = bootstrap_reduction([-0.5], [-0.5, -0.5], seed=1)
    assert reduction == 0.0
    assert math.isnan(low)
    assert math.isnan(high)


def test_stable_seed_is_stable_and_differs() -> None:
    assert stable_seed("run", "model", "gender") == stable_seed("run", "model", "gender")
    assert stable_seed("run", "model", "gender") != stable_seed("run", "model", "origin")
