"""Statistics students implement (M2 judge calibration, M4 paired bootstrap).

Rules: a judge is a classifier -- measure it like one. A higher mean is not
"better" until the paired CI of the difference excludes 0.
Reference values to self-check are in tests/test_lab9_stats.py.
"""

from __future__ import annotations

from collections.abc import Sequence
from math import comb

POS = "FAIL"   # the judge's job is to FIND failures, so FAIL is the positive class


def _norm(labels: Sequence[str]) -> list[str]:
    return [str(x).strip().upper() for x in labels]


def confusion(human: Sequence[str], judge: Sequence[str]) -> dict[str, int]:
    """tp/fp/fn/tn with FAIL as positive."""
    h, j = _norm(human), _norm(judge)
    if len(h) != len(j):
        raise ValueError("human and judge labels must have the same length")
    tp = sum(1 for a, b in zip(h, j) if a == POS and b == POS)
    fp = sum(1 for a, b in zip(h, j) if a != POS and b == POS)
    fn = sum(1 for a, b in zip(h, j) if a == POS and b != POS)
    tn = sum(1 for a, b in zip(h, j) if a != POS and b != POS)
    return {"tp": tp, "fp": fp, "fn": fn, "tn": tn}


def precision_recall(human: Sequence[str], judge: Sequence[str]) -> tuple[float, float]:
    """Precision = tp/(tp+fp), recall = tp/(tp+fn); 0.0 when the denominator is 0."""
    cm = confusion(human, judge)
    precision = cm["tp"] / (cm["tp"] + cm["fp"]) if cm["tp"] + cm["fp"] else 0.0
    recall = cm["tp"] / (cm["tp"] + cm["fn"]) if cm["tp"] + cm["fn"] else 0.0
    return precision, recall


def cohen_kappa(human: Sequence[str], judge: Sequence[str]) -> float:
    """kappa = (p_o - p_e) / (1 - p_e). Raise ValueError when undefined (p_e == 1):
    a constant judge has no signal and must FAIL calibration, not pass on a technicality."""
    h, j = _norm(human), _norm(judge)
    if not h:
        raise ValueError("kappa is undefined for an empty sample")
    if len(h) != len(j):
        raise ValueError("human and judge labels must have the same length")
    n = len(h)
    p_o = sum(1 for a, b in zip(h, j) if a == b) / n
    # p_e uses the marginal probability of each rater choosing the positive class.
    human_pos = sum(1 for a in h if a == POS) / n
    judge_pos = sum(1 for b in j if b == POS) / n
    p_e = human_pos * judge_pos + (1 - human_pos) * (1 - judge_pos)
    if p_e == 1.0:
        raise ValueError("kappa is undefined: both raters constant (p_e == 1)")
    return (p_o - p_e) / (1 - p_e)


def rogan_gladen(observed_rate: float, sensitivity: float, specificity: float) -> float:
    """Correct an observed failure rate for judge error; clip to [0, 1]."""
    denominator = sensitivity + specificity - 1
    if denominator == 0:
        return 0.0
    corrected = (observed_rate + specificity - 1) / denominator
    return min(1.0, max(0.0, corrected))


def paired_bootstrap(a: Sequence[float], b: Sequence[float], *, n_resamples: int = 1000,
                     rng: int = 2027, confidence: float = 0.95) -> tuple[float, float, float]:
    """a[i], b[i] = per-item mean over seeds, SAME items, SAME order.
    Return (mean(a)-mean(b), lo, hi) with scipy.stats.bootstrap(paired=True, method="percentile",
    rng=numpy.random.default_rng(rng)). If a == b everywhere return (0.0, 0.0, 0.0)."""
    import numpy as np
    from scipy.stats import bootstrap

    x = np.asarray(list(a), dtype=float)
    y = np.asarray(list(b), dtype=float)
    if x.shape != y.shape:
        raise ValueError("paired bootstrap needs the same number of paired observations")
    if x.size == 0:
        raise ValueError("paired bootstrap needs at least one observation")
    delta = float(x.mean() - y.mean())
    if np.allclose(x, y):
        return (0.0, 0.0, 0.0)
    result = bootstrap(
        (x, y),
        lambda first, second: np.mean(first) - np.mean(second),
        paired=True, vectorized=False, method="percentile",
        n_resamples=n_resamples, confidence_level=confidence,
        rng=np.random.default_rng(rng),
    )
    ci = result.confidence_interval
    return (delta, float(ci.low), float(ci.high))


def _check_pass_k(n: int, c: int, k: int) -> None:
    for name, value in (("n", n), ("c", c), ("k", k)):
        if not isinstance(value, int) or isinstance(value, bool):
            raise ValueError(f"{name} must be an int")
    if n < 1 or k < 1:
        raise ValueError("n and k must be >= 1")
    if k > n:
        raise ValueError("k must be <= n")
    if not 0 <= c <= n:
        raise ValueError("c must satisfy 0 <= c <= n")


def pass_at_k(n: int, c: int, k: int) -> float:
    """Probability that AT LEAST ONE of k trials drawn from n (c of them passing) passes.
    Unbiased estimator (Chen et al. 2021): 1 - C(n-c, k) / C(n, k). Raise ValueError if k > n."""
    _check_pass_k(n, c, k)
    return 1.0 - comb(n - c, k) / comb(n, k)


def pass_hat_k(n: int, c: int, k: int) -> float:
    """pass^k (tau-bench, Yao et al. 2024): probability that ALL k trials drawn from n pass.
    Unbiased estimator: C(c, k) / C(n, k). Raise ValueError if k > n.
    pass^k <= pass@1 <= pass@k; a reliable agent keeps pass^k close to pass@1."""
    _check_pass_k(n, c, k)
    return comb(c, k) / comb(n, k)
