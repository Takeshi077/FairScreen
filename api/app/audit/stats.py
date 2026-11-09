from __future__ import annotations

import hashlib
import math
from collections.abc import Sequence

import numpy as np
from numpy.typing import ArrayLike
from statsmodels.stats.multitest import multipletests


def stable_seed(*parts: object) -> int:
    payload = "|".join(str(part) for part in parts).encode("utf-8")
    return int.from_bytes(hashlib.sha256(payload).digest()[:8], "big") % (2**32)


def mean_gap(values: ArrayLike) -> float:
    array = np.asarray(values, dtype=float)
    if array.size == 0:
        return 0.0
    return float(array.mean())


def bootstrap_ci(
    values: ArrayLike,
    n_resamples: int = 10_000,
    seed: int = 2026,
    confidence: float = 0.95,
) -> tuple[float, float]:
    array = np.asarray(values, dtype=float)
    if array.size == 0:
        return (math.nan, math.nan)
    if array.size == 1:
        return (float(array[0]), float(array[0]))
    rng = np.random.default_rng(seed)
    indices = rng.integers(0, array.size, size=(n_resamples, array.size))
    means = array[indices].mean(axis=1)
    alpha = (1.0 - confidence) / 2.0
    return (float(np.quantile(means, alpha)), float(np.quantile(means, 1.0 - alpha)))


def paired_permutation_test(
    values: ArrayLike,
    n_resamples: int = 10_000,
    seed: int = 2026,
) -> float:
    array = np.asarray(values, dtype=float)
    if array.size == 0:
        return 1.0
    observed = abs(float(array.mean()))
    if observed == 0.0:
        return 1.0
    rng = np.random.default_rng(seed)
    signs = rng.choice(np.array([-1.0, 1.0]), size=(n_resamples, array.size))
    permuted = np.abs((signs * array).mean(axis=1))
    exceed = int(np.count_nonzero(permuted >= observed - 1e-12))
    return (exceed + 1) / (n_resamples + 1)


def cohen_dz(values: ArrayLike) -> float:
    array = np.asarray(values, dtype=float)
    if array.size < 2:
        return 0.0
    deviation = float(array.std(ddof=1))
    if deviation == 0.0:
        return 0.0
    return float(array.mean() / deviation)


def holm_adjust(p_values: Sequence[float]) -> list[float]:
    if not p_values:
        return []
    adjusted = multipletests(list(p_values), method="holm")[1]
    return [float(value) for value in adjusted]


def shortlist_ratio(rate_a: float, rate_b: float) -> float | None:
    if rate_b == 0.0:
        return None
    return float(rate_a / rate_b)


def repeat_noise_floor(values_by_repeat: Sequence[Sequence[float]]) -> float:
    variances: list[float] = []
    for values in values_by_repeat:
        if len(values) >= 2:
            variances.append(float(np.var(np.asarray(values, dtype=float), ddof=1)))
    if not variances:
        return 0.0
    return float(1.96 * math.sqrt(sum(variances) / len(variances)))


def pairwise_accuracy(
    scores: Sequence[float], tiers: Sequence[int]
) -> tuple[float, float, int]:
    score_array = np.asarray(scores, dtype=float)
    tier_array = np.asarray(tiers, dtype=float)
    if score_array.size != tier_array.size or score_array.size < 2:
        return (0.5, 0.5, 0)
    row, col = np.triu_indices(score_array.size, k=1)
    score_diff = score_array[row] - score_array[col]
    tier_diff = tier_array[row] - tier_array[col]
    relevant = tier_diff != 0
    n_pairs = int(np.count_nonzero(relevant))
    if n_pairs == 0:
        return (0.5, 0.5, 0)
    score_diff = score_diff[relevant]
    tier_diff = tier_diff[relevant]
    correct = ((score_diff > 0) & (tier_diff > 0)) | ((score_diff < 0) & (tier_diff < 0))
    ties = score_diff == 0
    accuracy = float((np.count_nonzero(correct) + 0.5 * np.count_nonzero(ties)) / n_pairs)
    return (accuracy, accuracy, n_pairs)


def bootstrap_reduction(
    baseline_values: ArrayLike,
    mitigation_values: ArrayLike,
    n_resamples: int = 10_000,
    seed: int = 2026,
    confidence: float = 0.95,
) -> tuple[float, float, float]:
    baseline = np.asarray(baseline_values, dtype=float)
    mitigation = np.asarray(mitigation_values, dtype=float)
    if baseline.size != mitigation.size or baseline.size == 0:
        return (0.0, math.nan, math.nan)
    reduction = abs(float(baseline.mean())) - abs(float(mitigation.mean()))
    if baseline.size == 1:
        return (reduction, reduction, reduction)
    rng = np.random.default_rng(seed)
    indices = rng.integers(0, baseline.size, size=(n_resamples, baseline.size))
    base_means = np.abs(baseline[indices].mean(axis=1))
    mit_means = np.abs(mitigation[indices].mean(axis=1))
    reduced = base_means - mit_means
    alpha = (1.0 - confidence) / 2.0
    return (
        float(reduction),
        float(np.quantile(reduced, alpha)),
        float(np.quantile(reduced, 1.0 - alpha)),
    )
