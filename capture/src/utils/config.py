from dataclasses import dataclass


@dataclass(slots=True)
class Config:
    device_id: str | None = None
    poll_interval_ms: int = 100 # Faster polling for 99.99% accuracy
    ocr_engine: str = "ensemble"
    roi_x: int = 40
    roi_y: int = 260
    roi_width: int = 640
    roi_height: int = 380
    confidence_threshold: float = 0.7 # Lower slightly as we now have two-pass validation
    max_multiplier: float = 500.0
    ws_host: str = "0.0.0.0"
    ws_port: int = 8765
    auto_roi_on_miss: bool = True
    auto_roi_cooldown_sec: int = 5
    auto_roi_scan_sec: int = 10
    smoothing_window: int = 5
    
    # Color thresholds (HSV)
    white_v_min: int = 190 # Higher value for white
    red_s_min: int = 100 # High saturation for red
    red_v_min: int = 100 # High value for red


config = Config()
