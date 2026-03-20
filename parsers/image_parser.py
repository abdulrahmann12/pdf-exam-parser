import io
import logging
from typing import List, Dict, Any

from .base import BaseParser
from .text_utils import parse_text_block

logger = logging.getLogger(__name__)


class ImageParser(BaseParser):
    """Parses image files (PNG, JPG, JPEG) via OCR using pytesseract."""

    SUPPORTED_EXTENSIONS = (".png", ".jpg", ".jpeg")
    SUPPORTED_CONTENT_TYPES = ("image/png", "image/jpeg", "image/jpg")

    def supports(self, filename: str, content_type: str) -> bool:
        return (
            filename.lower().endswith(self.SUPPORTED_EXTENSIONS)
            or content_type in self.SUPPORTED_CONTENT_TYPES
        )

    def parse(self, file_bytes: bytes) -> List[Dict[str, Any]]:
        from PIL import Image
        import pytesseract

        image = Image.open(io.BytesIO(file_bytes))
        text = pytesseract.image_to_string(image)
        logger.info("OCR extracted %d chars from image", len(text))
        return parse_text_block(text)
