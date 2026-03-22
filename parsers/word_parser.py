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
        try:
            from docx import Document
        except ImportError as e:
            raise ValueError(
                "Word document parsing requires the 'python-docx' library. "
                "Please install it with: pip install python-docx"
            ) from e

        try:
            doc = Document(io.BytesIO(file_bytes))
        except Exception as e:
            raise ValueError(
                f"Failed to open Word document: the file appears to be corrupted or is not a valid .docx file. "
                f"({type(e).__name__}: {e})"
            ) from e

        full_text = "\n".join(para.text for para in doc.paragraphs)
        logger.info("Word document: %d chars extracted", len(full_text))

        if not full_text.strip():
            raise ValueError(
                "No readable text found in the Word document. "
                "The file may be empty or contain only non-text elements (images, tables)."
            )

        return parse_text_block(full_text)
