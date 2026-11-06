"""OCR text extraction module using pytesseract with fail-safe fallbacks."""
from __future__ import annotations

import io
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class OCREngine:
    """Optical Character Recognition wrapper utilizing Tesseract OCR."""

    def __init__(self) -> None:
        self._tesseract_available: Optional[bool] = None

    def is_available(self) -> bool:
        """Check if pytesseract and the underlying Tesseract binary are functional."""
        if self._tesseract_available is not None:
            return self._tesseract_available
        try:
            import pytesseract
            # Test invocation
            pytesseract.get_tesseract_version()
            self._tesseract_available = True
        except Exception as exc:
            logger.info("Tesseract OCR is not installed or not in PATH: %s", exc)
            self._tesseract_available = False
        return self._tesseract_available

    def extract_text_from_image(self, image_data: bytes | io.BytesIO) -> str:
        """Extract text from an image byte stream or PIL Image."""
        if not self.is_available():
            logger.warning("OCR requested but Tesseract is not available in system environment.")
            return ""

        try:
            import pytesseract
            from PIL import Image

            if isinstance(image_data, bytes):
                image = Image.open(io.BytesIO(image_data))
            else:
                image = Image.open(image_data)

            # Optional grayscale enhancement for OCR
            image = image.convert("L")
            text = pytesseract.image_to_string(image)
            return text.strip()
        except Exception as exc:
            logger.error("OCR extraction failed: %s", exc)
            return ""


# Singleton instance
ocr_engine = OCREngine()
