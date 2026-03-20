import io
import logging
from typing import List, Dict, Any

import pandas as pd

from .base import BaseParser
from .dataframe_utils import dataframe_to_questions

logger = logging.getLogger(__name__)


class CsvParser(BaseParser):
    """Parses CSV files with columns:
    questionText, questionType, marks, choice1Text, choice1IsCorrect, ..."""

    SUPPORTED_EXTENSIONS = (".csv",)
    SUPPORTED_CONTENT_TYPES = ("text/csv", "application/vnd.ms-excel")

    def supports(self, filename: str, content_type: str) -> bool:
        return (
            filename.lower().endswith(self.SUPPORTED_EXTENSIONS)
            or content_type in self.SUPPORTED_CONTENT_TYPES
        )

    def parse(self, file_bytes: bytes) -> List[Dict[str, Any]]:
        df = pd.read_csv(io.BytesIO(file_bytes))
        logger.info("CSV loaded: %d rows", len(df))
        return dataframe_to_questions(df)
