from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable

import cv2
import easyocr
import numpy as np
import pytesseract
import shutil

from src.utils.config import config
from src.utils.logger import logger


MULTIPLIER_PATTERN = re.compile(r"(\d+(?:\.\d{1,2})?)\s*[xX]?", re.IGNORECASE)


@dataclass(slots=True)
class OcrResult:
    multiplier: float | None
    confidence: float
    raw_text: str
    round_state: str
    engine: str = "none"
    color: str = "white" # "white" for flying, "red" for crashed


class OcrEngine:
    def __init__(self) -> None:
        self._easyocr_reader: easyocr.Reader | None = None
        self._tesseract_available = shutil.which("tesseract") is not None
        if not self._tesseract_available:
            logger.warning("Tesseract OCR not found in PATH")

    def _get_easyocr_reader(self) -> easyocr.Reader:
        if self._easyocr_reader is None:
            import torch
            use_gpu = torch.cuda.is_available()
            self._easyocr_reader = easyocr.Reader(["en"], gpu=use_gpu)
            logger.info("EasyOCR initialized (GPU=%s)", use_gpu)
        return self._easyocr_reader

    def _get_color_and_mask(self, roi: np.ndarray) -> tuple[str, np.ndarray]:
        """Detects if text is predominantly white (flying) or red (crashed)."""
        hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
        
        # High-precision White Mask (Flying)
        lower_white = np.array([0, 0, 160]) # Lower slightly
        upper_white = np.array([180, 60, 255])
        mask_white = cv2.inRange(hsv, lower_white, upper_white)
        
        # High-precision Red Mask (Crashed)
        # Red is complex in HSV, spanning 0-10 and 170-180
        lower_red1 = np.array([0, 50, 50]) # Lower thresholds
        upper_red1 = np.array([15, 255, 255])
        lower_red2 = np.array([165, 50, 50])
        upper_red2 = np.array([180, 255, 255])
        mask_red1 = cv2.inRange(hsv, lower_red1, upper_red1)
        mask_red2 = cv2.inRange(hsv, lower_red2, upper_red2)
        mask_red = cv2.bitwise_or(mask_red1, mask_red2)
        
        # Count pixels
        white_pixels = cv2.countNonZero(mask_white)
        red_pixels = cv2.countNonZero(mask_red)
        
        # Decide color
        if red_pixels > 40 and red_pixels > (white_pixels * 0.4):
            return "red", mask_red
        
        if white_pixels > 30:
            return "white", mask_white
            
        return "none", mask_white

    def _preprocess_variants(self, roi: np.ndarray) -> list[tuple[np.ndarray, str, str]]:
        variants = []
        color, color_mask = self._get_color_and_mask(roi)
        
        if color == "none":
            # Fallback to general grayscale if no specific color detected
            gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
            scaled = cv2.resize(gray, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
            variants.append((scaled, "fallback_gray", "white"))
            return variants

        # Primary variant: Color Segmented + Thresholded
        res = cv2.bitwise_and(roi, roi, mask=color_mask)
        gray = cv2.cvtColor(res, cv2.COLOR_BGR2GRAY)
        scaled = cv2.resize(gray, None, fx=3, fy=3, interpolation=cv2.INTER_CUBIC) # 3x scale for higher precision
        _, thresh = cv2.threshold(scaled, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        
        # Morphological cleanup
        kernel = np.ones((2,2), np.uint8)
        thresh = cv2.dilate(thresh, kernel, iterations=1)
        thresh = cv2.erode(thresh, kernel, iterations=1)
        
        variants.append((thresh, f"precision_{color}", color))
        
        # Secondary variant: Color mask only
        variants.append((scaled, f"scaled_{color}", color))

        return variants

    def _parse_text(self, text: str, confidence: float, engine: str, color: str) -> OcrResult:
        cleaned = text.strip().replace(" ", "").replace(",", ".").lower()
        match = MULTIPLIER_PATTERN.search(cleaned)
        
        state = "resolved" if color == "red" else "flying"
        
        if not match:
            return OcrResult(multiplier=None, confidence=confidence, raw_text=cleaned, round_state="pending", engine=engine, color=color)
        
        return OcrResult(
            multiplier=float(match.group(1)),
            confidence=confidence,
            raw_text=f"{match.group(1)}x",
            round_state=state,
            engine=engine,
            color=color
        )

    def _run_easyocr(self, images: list[tuple[np.ndarray, str, str]]) -> OcrResult:
        best = OcrResult(multiplier=None, confidence=0.0, raw_text="", round_state="pending", engine="easyocr")
        reader = self._get_easyocr_reader()
        for img, name, color in images:
            detections = reader.readtext(img, detail=1, paragraph=False, allowlist="0123456789.xX")
            if not detections:
                continue
            text = "".join(fragment[1] for fragment in detections)
            conf = sum(fragment[2] for fragment in detections) / len(detections)
            parsed = self._parse_text(text, conf, f"easyocr_{name}", color)
            if parsed.multiplier and (parsed.confidence > best.confidence or (parsed.color == "red" and best.color == "white")):
                best = parsed
        return best

    def _run_tesseract(self, images: list[tuple[np.ndarray, str, str]]) -> OcrResult:
        if not self._tesseract_available:
            return OcrResult(multiplier=None, confidence=0.0, raw_text="", round_state="pending", engine="tesseract_unavailable")
        
        best = OcrResult(multiplier=None, confidence=0.0, raw_text="", round_state="pending", engine="tesseract")
        for img, name, color in images:
            data = pytesseract.image_to_data(img, config="--psm 7 -c tessedit_char_whitelist=0123456789.xX", output_type=pytesseract.Output.DICT)
            texts = [data['text'][i] for i in range(len(data['text'])) if int(data['conf'][i]) > 0]
            confs = [int(data['conf'][i]) / 100.0 for i in range(len(data['conf'])) if int(data['conf'][i]) > 0]
            if not texts: continue
            text = "".join(texts)
            conf = sum(confs) / len(confs)
            parsed = self._parse_text(text, conf, f"tesseract_{name}", color)
            if parsed.multiplier and (parsed.confidence > best.confidence or (parsed.color == "red" and best.color == "white")):
                best = parsed
        return best

    def extract(self, image_bytes: bytes) -> OcrResult:
        np_buffer = np.frombuffer(image_bytes, np.uint8)
        frame = cv2.imdecode(np_buffer, cv2.IMREAD_COLOR)
        if frame is None:
            return OcrResult(multiplier=None, confidence=0.0, raw_text="", round_state="error")

        roi = frame[
            config.roi_y : config.roi_y + config.roi_height,
            config.roi_x : config.roi_x + config.roi_width,
        ]

        variants = self._preprocess_variants(roi)
        
        # Ensemble approach: Run both and take the one with higher confidence
        e_result = self._run_easyocr(variants)
        t_result = self._run_tesseract(variants)
        
        # If they agree, boost confidence
        if e_result.multiplier and t_result.multiplier:
            if abs(e_result.multiplier - t_result.multiplier) < 0.01:
                e_result.confidence = min(1.0, e_result.confidence + 0.1)
                return e_result

        return e_result if e_result.confidence >= t_result.confidence else t_result

    def locate_multiplier_roi(self, image_bytes: bytes) -> tuple[int, int, int, int] | None:
        # Same as before but with slightly better logic
        reader = self._get_easyocr_reader()
        np_buffer = np.frombuffer(image_bytes, np.uint8)
        frame = cv2.imdecode(np_buffer, cv2.IMREAD_COLOR)
        if frame is None:
            return None
        
        # Detect ROI by searching for anything that looks like a multiplier
        detections = reader.readtext(frame, detail=1, paragraph=False, allowlist="0123456789.xX")
        for bbox, text, confidence in detections:
            if confidence > 0.5 and MULTIPLIER_PATTERN.search(text.replace(" ", "")):
                xs = [p[0] for p in bbox]
                ys = [p[1] for p in bbox]
                x1, y1, x2, y2 = int(min(xs)), int(min(ys)), int(max(xs)), int(max(ys))
                # Add padding
                pad = 20
                return (
                    max(0, x1 - pad),
                    max(0, y1 - pad),
                    min(frame.shape[1] - x1, (x2 - x1) + 2 * pad),
                    min(frame.shape[0] - y1, (y2 - y1) + 2 * pad)
                )
        return None


def parsed_multiplier(text: str) -> bool:
    return bool(MULTIPLIER_PATTERN.search(text.replace(" ", "")))
