from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4


class RoundState(str, Enum):
    WAITING = "WAITING"
    FLYING = "FLYING"
    CRASHED = "CRASHED"


class SourceStatus(str, Enum):
    ADB = "Connected via ADB"
    BROWSER = "Connected via Browser"
    NO_SIGNAL = "No Signal"


@dataclass(slots=True)
class FrameEnvelope:
    timestamp: datetime
    image_bytes: bytes
    source: str


@dataclass(slots=True)
class Observation:
    timestamp: datetime
    state: RoundState
    multiplier: float | None
    confidence: float
    source: str
    raw_text: str = ""
    color: str = "unknown"
    engine: str = "unknown"


@dataclass(slots=True)
class RoundRecord:
    timestamp: str
    round_id: str
    multiplier: float
    state: str
    source: str


@dataclass(slots=True)
class RoundView:
    round_id: str
    state: str
    multiplier: float | None
    timestamp: str | None
    source: str | None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class ProbabilityView:
    label: str
    probability_score: float
    confidence: float
    rolling_median: float
    volatility_index: float
    low_streak: int
    high_streak: int
    buckets: dict[str, int]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class Snapshot:
    status: str
    source: str
    state: str
    multiplier: float | None
    confidence: float
    current_round: RoundView
    previous_round: RoundView
    next_round: ProbabilityView
    recent_rounds: list[dict[str, Any]] = field(default_factory=list)
    ocr: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def new_round_id() -> str:
    return uuid4().hex[:12]
