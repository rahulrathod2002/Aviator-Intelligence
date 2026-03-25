from __future__ import annotations

from collections import deque

from backend.analytics.probability import build_probability
from backend.models import Observation, RoundRecord, RoundState, RoundView, Snapshot, SourceStatus, new_round_id
from backend.storage.csv_store import CsvRoundStore


class RoundStateEngine:
    def __init__(self, store: CsvRoundStore, history: list[RoundRecord]) -> None:
        self._store = store
        self._history = deque(history, maxlen=3000)
        self._current_round = RoundView(
            round_id="live-placeholder",
            state=RoundState.WAITING.value,
            multiplier=None,
            timestamp=None,
            source=None,
        )
        latest = history[-1] if history else None
        self._previous_round = (
            RoundView(
                round_id=latest.round_id,
                state=latest.state,
                multiplier=latest.multiplier,
                timestamp=latest.timestamp,
                source=latest.source,
            )
            if latest
            else RoundView(round_id="none", state=RoundState.CRASHED.value, multiplier=None, timestamp=None, source=None)
        )
        self._next_round = build_probability(list(self._history))
        self._last_state = RoundState.WAITING

    def apply(self, observation: Observation, source_status: SourceStatus) -> Snapshot:
        if source_status == SourceStatus.NO_SIGNAL:
            return self.snapshot(source_status, observation)

        if observation.state == RoundState.WAITING:
            if self._last_state == RoundState.CRASHED:
                self._current_round = RoundView(
                    round_id=new_round_id(),
                    state=RoundState.WAITING.value,
                    multiplier=None,
                    timestamp=observation.timestamp.isoformat(),
                    source=observation.source,
                )
            else:
                self._current_round.state = RoundState.WAITING.value
                self._current_round.multiplier = None
                self._current_round.timestamp = observation.timestamp.isoformat()
                self._current_round.source = observation.source

        elif observation.state == RoundState.FLYING:
            if self._current_round.round_id in {"live-placeholder", "none"} or self._last_state == RoundState.CRASHED:
                self._current_round = RoundView(
                    round_id=new_round_id(),
                    state=RoundState.FLYING.value,
                    multiplier=observation.multiplier,
                    timestamp=observation.timestamp.isoformat(),
                    source=observation.source,
                )
            else:
                self._current_round.state = RoundState.FLYING.value
                self._current_round.multiplier = observation.multiplier
                self._current_round.timestamp = observation.timestamp.isoformat()
                self._current_round.source = observation.source

        elif observation.state == RoundState.CRASHED:
            if self._current_round.round_id in {"live-placeholder", "none"}:
                self._current_round = RoundView(
                    round_id=new_round_id(),
                    state=RoundState.CRASHED.value,
                    multiplier=observation.multiplier,
                    timestamp=observation.timestamp.isoformat(),
                    source=observation.source,
                )
            else:
                self._current_round.state = RoundState.CRASHED.value
                self._current_round.multiplier = observation.multiplier
                self._current_round.timestamp = observation.timestamp.isoformat()
                self._current_round.source = observation.source

            if observation.multiplier is not None:
                record = RoundRecord(
                    timestamp=observation.timestamp.isoformat(),
                    round_id=self._current_round.round_id,
                    multiplier=observation.multiplier,
                    state=RoundState.CRASHED.value,
                    source=observation.source,
                )
                if not self._history or self._history[-1].round_id != record.round_id:
                    self._store.append(record)
                    self._history.append(record)
                    self._previous_round = RoundView(
                        round_id=record.round_id,
                        state=record.state,
                        multiplier=record.multiplier,
                        timestamp=record.timestamp,
                        source=record.source,
                    )
                    self._next_round = build_probability(list(self._history))

        self._last_state = observation.state
        return self.snapshot(source_status, observation)

    def snapshot(self, source_status: SourceStatus, observation: Observation | None = None) -> Snapshot:
        confidence = observation.confidence if observation else 0.0
        multiplier = observation.multiplier if observation else self._current_round.multiplier
        state = observation.state.value if observation else self._current_round.state
        return Snapshot(
            status="NO_SIGNAL" if source_status == SourceStatus.NO_SIGNAL else "LIVE",
            source=source_status.value,
            state=state,
            multiplier=multiplier,
            confidence=confidence,
            current_round=self._current_round,
            previous_round=self._previous_round,
            next_round=self._next_round,
            recent_rounds=[
                {
                    "timestamp": record.timestamp,
                    "round_id": record.round_id,
                    "multiplier": record.multiplier,
                    "state": record.state,
                    "source": record.source,
                }
                for record in list(self._history)[-10:]
            ],
            ocr={
                "raw_text": observation.raw_text if observation else "",
                "engine": observation.engine if observation else "unknown",
                "color": observation.color if observation else "unknown",
            },
        )
