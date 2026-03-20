import io
import logging
from typing import List, Dict, Any

from .base import BaseParser
from .text_utils import parse_text_block

logger = logging.getLogger(__name__)


class WordParser(BaseParser):
    """Parses Word (.docx) files by extracting paragraph text."""

    SUPPORTED_EXTENSIONS = (".docx",)
    SUPPORTED_CONTENT_TYPES = (
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )

    def supports(self, filename: str, content_type: str) -> bool:
        return (
            filename.lower().endswith(self.SUPPORTED_EXTENSIONS)
            or content_type in self.SUPPORTED_CONTENT_TYPES
        )

    def parse(self, file_bytes: bytes) -> List[Dict[str, Any]]:
        from docx import Document

        doc = Document(io.BytesIO(file_bytes))
        full_text = "\n".join(para.text for para in doc.paragraphs)
        logger.info("Word document: %d chars extracted", len(full_text))
        return parse_text_block(full_text)
