from __future__ import annotations

import csv
from pathlib import Path
from typing import Iterable

from backend.config import settings
from backend.models import RoundRecord


class CsvRoundStore:
    fieldnames = ["timestamp", "round_id", "multiplier", "state", "source"]

    def __init__(self, path: Path | None = None) -> None:
        self._path = path or settings.rounds_file
        self._path.parent.mkdir(parents=True, exist_ok=True)
        if not self._path.exists():
            with self._path.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(handle, fieldnames=self.fieldnames)
                writer.writeheader()

    def load_recent(self, limit: int | None = None) -> list[RoundRecord]:
        limit = limit or settings.recent_round_limit
        with self._path.open("r", newline="", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            rows = [self._parse_row(row) for row in reader if row.get("timestamp")]
        rows.sort(key=lambda row: row.timestamp, reverse=True)
        trimmed = rows[:limit]
        self._rewrite(trimmed)
        return list(reversed(trimmed))

    def append(self, record: RoundRecord) -> None:
        with self._path.open("a", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=self.fieldnames)
            writer.writerow(
                {
                    "timestamp": record.timestamp,
                    "round_id": record.round_id,
                    "multiplier": record.multiplier,
                    "state": record.state,
                    "source": record.source,
                }
            )

    def _rewrite(self, rows: Iterable[RoundRecord]) -> None:
        with self._path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=self.fieldnames)
            writer.writeheader()
            for row in sorted(rows, key=lambda item: item.timestamp):
                writer.writerow(
                    {
                        "timestamp": row.timestamp,
                        "round_id": row.round_id,
                        "multiplier": row.multiplier,
                        "state": row.state,
                        "source": row.source,
                    }
                )

    @staticmethod
    def _parse_row(row: dict[str, str]) -> RoundRecord:
        return RoundRecord(
            timestamp=row["timestamp"],
            round_id=row["round_id"],
            multiplier=float(row["multiplier"]),
            state=row["state"],
            source=row["source"],
        )
