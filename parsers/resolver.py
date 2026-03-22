import logging
from typing import List

from .base import BaseParser
from .pdf_parser import PdfParser
from .csv_parser import CsvParser
from .excel_parser import ExcelParser
from .image_parser import ImageParser
from .text_parser import TextParser
from .word_parser import WordParser
from .fallback_parser import FallbackParser

logger = logging.getLogger(__name__)


class ParserResolver:
    """Holds all registered parsers in priority order and resolves
    the correct one for a given file.

    To add a new file type, just append a new parser instance to the list.
    FallbackParser is always last and catches anything unmatched.
    """

    def __init__(self) -> None:
        self._parsers: List[BaseParser] = [
            PdfParser(),
            CsvParser(),
            ExcelParser(),
            ImageParser(),
            TextParser(),
            WordParser(),
            FallbackParser(),  # must be last
        ]
        logger.info(
            "ParserResolver initialized with %d parsers: %s",
            len(self._parsers),
            [p.__class__.__name__ for p in self._parsers],
        )

    def resolve(self, filename: str, content_type: str) -> BaseParser:
        """Return the first parser that supports the given file."""
        for parser in self._parsers:
            if parser.supports(filename, content_type):
                logger.info(
                    "Resolved parser: %s for file='%s' content_type='%s'",
                    parser.__class__.__name__, filename, content_type,
                )
                return parser

        # Should never reach here because FallbackParser.supports() always returns True
        raise ValueError(
            f"No parser available for file '{filename}' (content_type='{content_type}'). "
            f"Supported formats: PDF, CSV, Excel (.xlsx/.xls), Word (.docx), "
            f"images (PNG/JPG), and plain text (.txt)."
        )

    def register(self, parser: BaseParser, before_fallback: bool = True) -> None:
        """Dynamically register a new parser at runtime.
        By default inserts before the FallbackParser."""
        if before_fallback and isinstance(self._parsers[-1], FallbackParser):
            self._parsers.insert(len(self._parsers) - 1, parser)
        else:
            self._parsers.append(parser)
        logger.info("Registered new parser: %s", parser.__class__.__name__)
