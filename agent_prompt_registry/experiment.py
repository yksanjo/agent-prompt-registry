"""Experiment analysis utilities."""

import math
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple


@dataclass
class ExperimentResult:
    """Results from an A/B experiment."""
    variant_a: str
    variant_b: str
    a_trials: int
    a_successes: int
    b_trials: int
    b_successes: int
    winner: Optional[str]
    confidence: float
    lift: float  # percentage improvement

    @property
    def a_rate(self) -> float:
        return self.a_successes / self.a_trials if self.a_trials > 0 else 0

    @property
    def b_rate(self) -> float:
        return self.b_successes / self.b_trials if self.b_trials > 0 else 0


def calculate_significance(
    a_trials: int,
    a_successes: int,
    b_trials: int,
    b_successes: int,
    confidence_level: float = 0.95
) -> Tuple[bool, float, Optional[str]]:
    """Calculate statistical significance using two-proportion z-test.

    Args:
        a_trials: Number of trials for variant A
        a_successes: Number of successes for variant A
        b_trials: Number of trials for variant B
        b_successes: Number of successes for variant B
        confidence_level: Required confidence level (default 0.95)

    Returns:
        Tuple of (is_significant, confidence, winner)
    """
    if a_trials < 30 or b_trials < 30:
        return False, 0.0, None

    p_a = a_successes / a_trials
    p_b = b_successes / b_trials

    # Pooled proportion
    p_pool = (a_successes + b_successes) / (a_trials + b_trials)

    # Standard error
    se = math.sqrt(p_pool * (1 - p_pool) * (1/a_trials + 1/b_trials))

    if se == 0:
        return False, 0.0, None

    # Z-score
    z = (p_a - p_b) / se

    # Two-tailed p-value using approximation
    # Using standard normal distribution approximation
    p_value = 2 * (1 - _normal_cdf(abs(z)))

    confidence = 1 - p_value
    is_significant = confidence >= confidence_level

    winner = None
    if is_significant:
        winner = "a" if p_a > p_b else "b"

    return is_significant, confidence, winner


def _normal_cdf(x: float) -> float:
    """Approximate standard normal CDF."""
    # Approximation using error function
    return 0.5 * (1 + math.erf(x / math.sqrt(2)))


def calculate_sample_size(
    baseline_rate: float,
    minimum_detectable_effect: float,
    confidence_level: float = 0.95,
    power: float = 0.80
) -> int:
    """Calculate required sample size per variant.

    Args:
        baseline_rate: Expected baseline conversion rate
        minimum_detectable_effect: Minimum relative improvement to detect
        confidence_level: Required confidence level
        power: Statistical power

    Returns:
        Required sample size per variant
    """
    # Z-scores for confidence and power
    z_alpha = _inverse_normal_cdf(1 - (1 - confidence_level) / 2)
    z_beta = _inverse_normal_cdf(power)

    p1 = baseline_rate
    p2 = baseline_rate * (1 + minimum_detectable_effect)

    # Pooled variance
    p_avg = (p1 + p2) / 2

    numerator = (z_alpha * math.sqrt(2 * p_avg * (1 - p_avg)) +
                 z_beta * math.sqrt(p1 * (1 - p1) + p2 * (1 - p2))) ** 2
    denominator = (p2 - p1) ** 2

    return int(math.ceil(numerator / denominator))


def _inverse_normal_cdf(p: float) -> float:
    """Approximate inverse standard normal CDF (probit function)."""
    # Rational approximation
    if p <= 0:
        return float('-inf')
    if p >= 1:
        return float('inf')

    if p < 0.5:
        return -_inverse_normal_cdf(1 - p)

    t = math.sqrt(-2 * math.log(1 - p))

    # Coefficients for rational approximation
    c0, c1, c2 = 2.515517, 0.802853, 0.010328
    d1, d2, d3 = 1.432788, 0.189269, 0.001308

    return t - (c0 + c1*t + c2*t*t) / (1 + d1*t + d2*t*t + d3*t*t*t)


def analyze_experiment(
    results: Dict[str, Dict[str, int]],
    confidence_level: float = 0.95
) -> ExperimentResult:
    """Analyze experiment results.

    Args:
        results: Dict with variant names as keys and {trials, successes} as values
        confidence_level: Required confidence level

    Returns:
        ExperimentResult object
    """
    variants = list(results.keys())
    if len(variants) != 2:
        raise ValueError("Experiment analysis requires exactly 2 variants")

    a, b = variants
    a_data = results[a]
    b_data = results[b]

    is_sig, confidence, winner_code = calculate_significance(
        a_data["trials"], a_data["successes"],
        b_data["trials"], b_data["successes"],
        confidence_level
    )

    winner = None
    if winner_code == "a":
        winner = a
    elif winner_code == "b":
        winner = b

    # Calculate lift
    a_rate = a_data["successes"] / a_data["trials"] if a_data["trials"] > 0 else 0
    b_rate = b_data["successes"] / b_data["trials"] if b_data["trials"] > 0 else 0

    if a_rate > 0:
        lift = ((b_rate - a_rate) / a_rate) * 100
    else:
        lift = 0

    return ExperimentResult(
        variant_a=a,
        variant_b=b,
        a_trials=a_data["trials"],
        a_successes=a_data["successes"],
        b_trials=b_data["trials"],
        b_successes=b_data["successes"],
        winner=winner,
        confidence=round(confidence, 4),
        lift=round(lift, 2)
    )
