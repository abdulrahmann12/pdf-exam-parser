import logging
from typing import List, Dict, Any

from .base import BaseParser
from .text_utils import parse_text_block

logger = logging.getLogger(__name__)


class TextParser(BaseParser):
    """Parses plain text (.txt) files using the Q:/Type:/Marks:/Choices: format."""

    SUPPORTED_EXTENSIONS = (".txt",)
    SUPPORTED_CONTENT_TYPES = ("text/plain",)

    def supports(self, filename: str, content_type: str) -> bool:
        return (
            filename.lower().endswith(self.SUPPORTED_EXTENSIONS)
            or content_type in self.SUPPORTED_CONTENT_TYPES
        )

    def parse(self, file_bytes: bytes) -> List[Dict[str, Any]]:
        try:
            text = file_bytes.decode("utf-8")
        except UnicodeDecodeError:
            logger.warning("UTF-8 decoding failed, falling back to latin-1")
            text = file_bytes.decode("latin-1")

        if not text.strip():
            raise ValueError(
                "The text file is empty or contains only whitespace."
            )

        logger.info("Text file: %d chars", len(text))
        return parse_text_block(text)
