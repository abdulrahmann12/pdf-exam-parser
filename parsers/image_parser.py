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
        try:
            from PIL import Image
        except ImportError as e:
            raise ValueError(
                "Image parsing requires the 'Pillow' library. Please install it with: pip install Pillow"
            ) from e

        try:
            import pytesseract
        except ImportError as e:
            raise ValueError(
                "Image parsing requires 'pytesseract'. Please install it with: pip install pytesseract "
                "and ensure Tesseract OCR is installed on the system."
            ) from e

        try:
            image = Image.open(io.BytesIO(file_bytes))
        except Exception as e:
            raise ValueError(
                f"Failed to open image: the file appears to be corrupted or is not a valid image. "
                f"({type(e).__name__}: {e})"
            ) from e

        try:
            text = pytesseract.image_to_string(image)
        except pytesseract.TesseractNotFoundError as e:
            raise ValueError(
                "Tesseract OCR engine is not installed or not found in PATH. "
                "Please install Tesseract: https://github.com/tesseract-ocr/tesseract"
            ) from e
        except Exception as e:
            raise ValueError(
                f"OCR processing failed: {type(e).__name__}: {e}. "
                f"The image may be too large, too low-resolution, or in an unsupported format."
            ) from e

        logger.info("OCR extracted %d chars from image", len(text))
        logger.debug("OCR raw text:\n%s", text)

        if not text.strip():
            raise ValueError(
                "OCR could not extract any text from the image. "
                "Ensure the image contains readable text and has sufficient resolution."
            )

        return parse_text_block(text)
