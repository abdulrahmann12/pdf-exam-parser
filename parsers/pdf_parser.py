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
        with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
            full_text = "\n".join(
                page.extract_text() for page in pdf.pages if page.extract_text()
            )
        logger.info("PDF text extracted (%d chars)", len(full_text))
        return parse_text_block(full_text)
