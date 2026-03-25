from __future__ import annotations

import re
import shutil
from dataclasses import dataclass

import cv2
import easyocr
import numpy as np
import pytesseract

from backend.config import settings
from backend.models import Observation, RoundState, utc_now


MULTIPLIER_PATTERN = re.compile(r"(\d+(?:[\.,]\d{1,2})?)\s*[xX]?")


@dataclass(slots=True)
class OcrPassResult:
    text: str
    confidence: float
    engine: str


class OcrEngine:
    def __init__(self) -> None:
        self._easyocr_reader: easyocr.Reader | None = None
        self._tesseract_available = shutil.which("tesseract") is not None

    def _reader(self) -> easyocr.Reader:
        if self._easyocr_reader is None:
            self._easyocr_reader = easyocr.Reader(["en"], gpu=False)
        return self._easyocr_reader

    def _crop_roi(self, frame: np.ndarray) -> np.ndarray:
        x1 = settings.roi_x
        y1 = settings.roi_y
        x2 = min(frame.shape[1], x1 + settings.roi_width)
        y2 = min(frame.shape[0], y1 + settings.roi_height)
        return frame[y1:y2, x1:x2]

    def _detect_color(self, roi: np.ndarray) -> tuple[str, np.ndarray]:
        hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
        white_mask = cv2.inRange(hsv, np.array([0, 0, 180]), np.array([180, 70, 255]))
        red_mask_a = cv2.inRange(hsv, np.array([0, 90, 80]), np.array([12, 255, 255]))
        red_mask_b = cv2.inRange(hsv, np.array([168, 90, 80]), np.array([180, 255, 255]))
        red_mask = cv2.bitwise_or(red_mask_a, red_mask_b)
        white_pixels = cv2.countNonZero(white_mask)
        red_pixels = cv2.countNonZero(red_mask)
        if red_pixels > 40 and red_pixels >= white_pixels * 0.35:
            return "red", red_mask
        if white_pixels > 50:
            return "white", white_mask
        return "none", white_mask

    def _variants(self, roi: np.ndarray, color_mask: np.ndarray) -> list[np.ndarray]:
        masked = cv2.bitwise_and(roi, roi, mask=color_mask)
        gray = cv2.cvtColor(masked, cv2.COLOR_BGR2GRAY)
        scaled = cv2.resize(gray, None, fx=3, fy=3, interpolation=cv2.INTER_CUBIC)
        blur = cv2.GaussianBlur(scaled, (3, 3), 0)
        _, otsu = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        adaptive = cv2.adaptiveThreshold(blur, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 31, 3)
        return [scaled, otsu, adaptive]

    def _run_easyocr(self, variants: list[np.ndarray]) -> OcrPassResult:
        best = OcrPassResult(text="", confidence=0.0, engine="easyocr")
        reader = self._reader()
        for index, variant in enumerate(variants):
            detections = reader.readtext(variant, detail=1, paragraph=False, allowlist="0123456789.xX")
            if not detections:
                continue
            text = "".join(fragment[1] for fragment in detections)
            confidence = sum(float(fragment[2]) for fragment in detections) / len(detections)
            if confidence >= best.confidence:
                best = OcrPassResult(text=text, confidence=confidence, engine=f"easyocr_pass_{index + 1}")
        return best

    def _run_tesseract(self, variants: list[np.ndarray]) -> OcrPassResult:
        if not self._tesseract_available:
            return OcrPassResult(text="", confidence=0.0, engine="tesseract_unavailable")
        best = OcrPassResult(text="", confidence=0.0, engine="tesseract")
        for index, variant in enumerate(variants):
            data = pytesseract.image_to_data(
                variant,
                config="--psm 7 -c tessedit_char_whitelist=0123456789.xX",
                output_type=pytesseract.Output.DICT,
            )
            texts: list[str] = []
            confidences: list[float] = []
            for raw_text, raw_conf in zip(data.get("text", []), data.get("conf", [])):
                try:
                    confidence = float(raw_conf)
                except (TypeError, ValueError):
                    continue
                if confidence <= 0:
                    continue
                texts.append(raw_text)
                confidences.append(confidence / 100.0)
            if not texts:
                continue
            average_confidence = sum(confidences) / len(confidences)
            if average_confidence >= best.confidence:
                best = OcrPassResult(
                    text="".join(texts),
                    confidence=average_confidence,
                    engine=f"tesseract_pass_{index + 1}",
                )
        return best

    def extract(self, image_bytes: bytes, source: str) -> Observation:
        frame = cv2.imdecode(np.frombuffer(image_bytes, np.uint8), cv2.IMREAD_COLOR)
        if frame is None:
            return Observation(
                timestamp=utc_now(),
                state=RoundState.WAITING,
                multiplier=None,
                confidence=0.0,
                source=source,
            )

        roi = self._crop_roi(frame)
        color, mask = self._detect_color(roi)
        variants = self._variants(roi, mask)
        easy = self._run_easyocr(variants)
        tess = self._run_tesseract(variants)
        best = easy if easy.confidence >= tess.confidence else tess
        cleaned = best.text.replace(" ", "").replace(",", ".")
        match = MULTIPLIER_PATTERN.search(cleaned)

        if not match:
            return Observation(
                timestamp=utc_now(),
                state=RoundState.WAITING,
                multiplier=None,
                confidence=round(max(easy.confidence, tess.confidence) * 0.5, 4),
                source=source,
                raw_text=cleaned,
                color=color,
                engine=best.engine,
            )

        multiplier = min(float(match.group(1)), settings.max_multiplier)
        if multiplier <= 1.01 and color != "red":
            state = RoundState.WAITING
        elif color == "red":
            state = RoundState.CRASHED
        else:
            state = RoundState.FLYING

        return Observation(
            timestamp=utc_now(),
            state=state,
            multiplier=multiplier,
            confidence=round(best.confidence, 4),
            source=source,
            raw_text=cleaned,
            color=color,
            engine=best.engine,
        )
