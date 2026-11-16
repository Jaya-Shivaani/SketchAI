"""
Anti-Cheat OCR Service
Uses lightweight RapidOCR (ONNX Runtime) to detect handwritten text on the drawing canvas.
Flags and penalizes players who write the secret word or letters instead of sketching!
"""

import logging
import difflib
from typing import Dict, Any, List, Tuple, Optional
from PIL import Image, ImageDraw
import numpy as np

logger = logging.getLogger("uvicorn.error")

class AntiCheatService:
    def __init__(self):
        self.ocr = None
        self._init_ocr()

    def _init_ocr(self):
        try:
            from rapidocr_onnxruntime import RapidOCR
            self.ocr = RapidOCR()
            logger.info("AntiCheatService: RapidOCR ONNX model loaded successfully.")
        except Exception as e:
            logger.warning("AntiCheatService: RapidOCR could not be loaded: %s", e)
            self.ocr = None

    def render_strokes(
        self,
        strokes_data: List[Dict[str, Any]],
        width: int = 800,
        height: int = 450,
        stroke_width: int = 6
    ) -> Image.Image:
        """Renders raw stroke dicts onto a clean white bitmap for OCR processing."""
        img = Image.new("RGB", (width, height), (255, 255, 255))
        draw = ImageDraw.Draw(img)

        for stroke in strokes_data:
            if stroke.get("tool") == "eraser":
                continue
            pts = stroke.get("points", [])
            if len(pts) >= 2:
                flat_pts = []
                for p in pts:
                    flat_pts.extend([p[0], p[1]])
                draw.line(flat_pts, fill=(0, 0, 0), width=stroke_width, joint="round")
            elif len(pts) == 1:
                x, y = pts[0][0], pts[0][1]
                draw.ellipse([x - 3, y - 3, x + 3, y + 3], fill=(0, 0, 0))

        return img

    def detect_written_text(self, strokes_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Runs OCR inference on the rendered stroke canvas. Returns detected words and bboxes."""
        if not self.ocr or not strokes_data or len(strokes_data) < 2:
            return []

        try:
            img = self.render_strokes(strokes_data)
            arr = np.array(img)
            result, _ = self.ocr(arr)
            if not result:
                return []

            detected = []
            for item in result:
                # item format: [bbox, text, confidence]
                bbox, text, conf = item[0], str(item[1]).strip(), float(item[2])
                if len(text) > 0 and conf >= 0.40:
                    detected.append({
                        "text": text,
                        "confidence": round(conf, 3),
                        "bbox": bbox
                    })
            return detected
        except Exception as e:
            logger.error("AntiCheatService: Error during OCR inference: %s", e)
            return []

    def check_spoiler_cheating(
        self,
        strokes_data: List[Dict[str, Any]],
        secret_word: str
    ) -> Tuple[bool, Optional[str], float]:
        """
        Checks whether the drawer wrote the secret word (or significant parts of it)
        on the canvas. Returns (is_cheating, detected_word, confidence).
        """
        if not secret_word or not strokes_data:
            return False, None, 0.0

        secret_clean = "".join(c for c in secret_word.lower() if c.isalnum())
        if not secret_clean:
            return False, None, 0.0

        detections = self.detect_written_text(strokes_data)
        if not detections:
            return False, None, 0.0

        for item in detections:
            detected_raw = item["text"]
            detected_clean = "".join(c for c in detected_raw.lower() if c.isalnum())
            if not detected_clean:
                continue

            # 1. Exact full match (e.g. "Airplane" found in "airplane")
            if secret_clean in detected_clean or detected_clean == secret_clean:
                return True, detected_raw, item["confidence"]

            # 2. High Levenshtein sequence similarity (>= 70%) for words with len >= 3
            sim = difflib.SequenceMatcher(None, detected_clean, secret_clean).ratio()
            if sim >= 0.70 and len(detected_clean) >= 2:
                return True, detected_raw, round(sim, 3)

            # 3. Substring of secret word (e.g. "plane" in "airplane", len >= 3)
            if len(detected_clean) >= 3 and detected_clean in secret_clean:
                return True, detected_raw, round(len(detected_clean) / len(secret_clean), 3)

        return False, None, 0.0


anti_cheat_service = AntiCheatService()

