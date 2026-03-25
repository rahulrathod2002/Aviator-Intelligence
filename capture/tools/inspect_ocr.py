from __future__ import annotations

import sys
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.adb_capture.client import AdbClient
from src.ocr.engine import OcrEngine
from src.utils.config import config


def save_image(name: str, image: np.ndarray) -> None:
    out_path = ROOT.parent / name
    cv2.imwrite(str(out_path), image)
    print(f"saved {out_path}")


def main() -> None:
    adb = AdbClient()
    engine = OcrEngine()

    # Capture a raw frame via adb
    frame_bytes = run_capture(adb)
    np_buffer = np.frombuffer(frame_bytes, np.uint8)
    frame = cv2.imdecode(np_buffer, cv2.IMREAD_COLOR)
    if frame is None:
        raise RuntimeError("failed to decode capture frame")

    # Crop ROI and save diagnostic images
    roi = frame[
        config.roi_y : config.roi_y + config.roi_height,
        config.roi_x : config.roi_x + config.roi_width,
    ]
    save_image("aviator_roi.png", roi)

    gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
    _, thresh = cv2.threshold(gray, 160, 255, cv2.THRESH_BINARY)
    save_image("aviator_thresh.png", thresh)

    # Run OCR using the engine
    result = engine.extract(frame_bytes)
    print(f"ocr result: multiplier={result.multiplier} confidence={result.confidence:.3f} raw='{result.raw_text}'")


def run_capture(adb: AdbClient) -> bytes:
    # Use synchronous subprocess via the existing adb client
    import asyncio

    return asyncio.run(adb.capture_frame())


if __name__ == "__main__":
    main()
