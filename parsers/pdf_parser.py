import io
import logging
from typing import List, Dict, Any

import pdfplumber

from .base import BaseParser
from .text_utils import parse_text_block

logger = logging.getLogger(__name__)


class PdfParser(BaseParser):
    """Parses PDF files using pdfplumber to extract text, then applies the
    standard Q:/Type:/Marks:/Choices: format parser."""

    SUPPORTED_EXTENSIONS = (".pdf",)
    SUPPORTED_CONTENT_TYPES = ("application/pdf",)

    def supports(self, filename: str, content_type: str) -> bool:
        return (
            filename.lower().endswith(self.SUPPORTED_EXTENSIONS)
            or content_type in self.SUPPORTED_CONTENT_TYPES
        )

    def parse(self, file_bytes: bytes) -> List[Dict[str, Any]]:
        try:
            pdf = pdfplumber.open(io.BytesIO(file_bytes))
        except Exception as e:
            raise ValueError(
                f"Failed to open PDF: the file appears to be corrupted or is not a valid PDF document. ({type(e).__name__}: {e})"
            ) from e

        try:
            pages_text = []
            for i, page in enumerate(pdf.pages):
                try:
                    text = page.extract_text()
                    if text:
                        pages_text.append(text)
                except Exception as e:
                    logger.warning("Failed to extract text from PDF page %d: %s", i + 1, e)
            full_text = "\n".join(pages_text)
        finally:
            pdf.close()

        if not full_text.strip():
            raise ValueError(
                "No readable text found in the PDF. The file may contain only images or scanned content. "
                "Try uploading a text-based PDF or use an image format with OCR support."
            )

        logger.info("PDF text extracted (%d chars from %d pages)", len(full_text), len(pages_text))
        return parse_text_block(full_text)
