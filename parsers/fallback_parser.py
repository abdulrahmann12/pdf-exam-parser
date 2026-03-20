import logging
from typing import List, Dict, Any

from .base import BaseParser
from .text_utils import parse_text_block

logger = logging.getLogger(__name__)


class FallbackParser(BaseParser):
    """Last-resort parser that treats any file as plain text.
    Always returns True for supports() — used only when no other parser matches."""

    def supports(self, filename: str, content_type: str) -> bool:
        return True

    def parse(self, file_bytes: bytes) -> List[Dict[str, Any]]:
        logger.warning("FallbackParser invoked — treating file as raw text")
        text = file_bytes.decode("utf-8", errors="replace")
        return parse_text_block(text)
