from __future__ import annotations

from statistics import median
from typing import Callable, Sequence

from backend.config import settings
from backend.models import ProbabilityView, RoundRecord


def _stddev(values: Sequence[float]) -> float:
    if len(values) < 2:
        return 0.0
    avg = sum(values) / len(values)
    variance = sum((value - avg) ** 2 for value in values) / len(values)
    return variance ** 0.5


def _streak(values: Sequence[float], predicate: Callable[[float], bool]) -> int:
    count = 0
    for value in reversed(values):
        if not predicate(value):
            break
        count += 1
    return count


def _buckets(values: Sequence[float]) -> dict[str, int]:
    result = {"lt_2x": 0, "2x_to_5x": 0, "5x_to_10x": 0, "gte_10x": 0}
    for value in values:
        if value < 2:
            result["lt_2x"] += 1
        elif value < 5:
            result["2x_to_5x"] += 1
        elif value < 10:
            result["5x_to_10x"] += 1
        else:
            result["gte_10x"] += 1
    return result


def build_probability(records: Sequence[RoundRecord]) -> ProbabilityView:
    values = [record.multiplier for record in records if record.state == "CRASHED"]
    if not values:
        return ProbabilityView(
            label="Insufficient history",
            probability_score=0.0,
            confidence=0.0,
            rolling_median=0.0,
            volatility_index=0.0,
            low_streak=0,
            high_streak=0,
            buckets=_buckets([]),
        )

    window = values[-300:]
    rolling_median = round(median(window), 2)
    volatility_index = round(_stddev(window), 2)
    low_streak = _streak(window, lambda value: value < settings.low_streak_threshold)
    high_streak = _streak(window, lambda value: value >= settings.high_streak_threshold)
    buckets = _buckets(window)

    base_probability = sum(1 for value in window if value >= 2.0) / len(window)
    volatility_penalty = min(0.25, volatility_index / 40)
    low_streak_adjustment = min(0.12, low_streak * 0.015)
    high_streak_adjustment = min(0.10, high_streak * 0.01)
    probability_score = max(
        0.02,
        min(0.98, base_probability + low_streak_adjustment - high_streak_adjustment - volatility_penalty),
    )

    sample_factor = min(1.0, len(window) / 300)
    confidence = max(0.05, min(0.99, 0.45 + sample_factor * 0.35 + max(0.0, 0.2 - volatility_penalty)))

    if probability_score >= 0.67:
        label = "Higher-than-baseline probability of a 2x+ follow-up"
    elif probability_score <= 0.4:
        label = "Lower-than-baseline probability of a 2x+ follow-up"
    else:
        label = "Balanced probability profile"

    return ProbabilityView(
        label=label,
        probability_score=round(probability_score, 4),
        confidence=round(confidence, 4),
        rolling_median=rolling_median,
        volatility_index=volatility_index,
        low_streak=low_streak,
        high_streak=high_streak,
        buckets=buckets,
    )
