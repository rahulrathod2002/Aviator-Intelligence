from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path


@dataclass(slots=True)
class Settings:
    project_root: Path = field(default_factory=lambda: Path(__file__).resolve().parent.parent)
    data_dir: Path = field(init=False)
    rounds_file: Path = field(init=False)
    websocket_host: str = field(default_factory=lambda: os.getenv("AVIATOR_WS_HOST", "0.0.0.0"))
    websocket_port: int = field(default_factory=lambda: int(os.getenv("AVIATOR_WS_PORT", "8765")))
    frame_queue_size: int = field(default_factory=lambda: int(os.getenv("AVIATOR_FRAME_QUEUE", "2")))
    source_poll_interval: float = field(default_factory=lambda: float(os.getenv("AVIATOR_SOURCE_POLL_MS", "120")) / 1000.0)
    browser_url: str = field(
        default_factory=lambda: os.getenv(
            "AVIATOR_BROWSER_URL",
            "https://1wwfqf.life/?p=24r1&sub1=20260223-0530-0776-8b39-e767c8b0867a&sub2=1win1_in_reg",
        )
    )
    browser_width: int = field(default_factory=lambda: int(os.getenv("AVIATOR_BROWSER_WIDTH", "1440")))
    browser_height: int = field(default_factory=lambda: int(os.getenv("AVIATOR_BROWSER_HEIGHT", "960")))
    roi_x: int = field(default_factory=lambda: int(os.getenv("AVIATOR_ROI_X", "40")))
    roi_y: int = field(default_factory=lambda: int(os.getenv("AVIATOR_ROI_Y", "250")))
    roi_width: int = field(default_factory=lambda: int(os.getenv("AVIATOR_ROI_WIDTH", "700")))
    roi_height: int = field(default_factory=lambda: int(os.getenv("AVIATOR_ROI_HEIGHT", "420")))
    max_multiplier: float = field(default_factory=lambda: float(os.getenv("AVIATOR_MAX_MULTIPLIER", "1000")))
    recent_round_limit: int = field(default_factory=lambda: int(os.getenv("AVIATOR_RECENT_LIMIT", "3000")))
    low_streak_threshold: float = field(default_factory=lambda: float(os.getenv("AVIATOR_LOW_STREAK", "2.0")))
    high_streak_threshold: float = field(default_factory=lambda: float(os.getenv("AVIATOR_HIGH_STREAK", "10.0")))

    def __post_init__(self) -> None:
        self.data_dir = self.project_root / "data"
        self.rounds_file = self.data_dir / "rounds.csv"


settings = Settings()
