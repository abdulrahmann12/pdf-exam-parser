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
        try:
            df = pd.read_csv(io.BytesIO(file_bytes))
        except pd.errors.EmptyDataError as e:
            raise ValueError(
                "The CSV file is empty or contains no parseable data."
            ) from e
        except pd.errors.ParserError as e:
            raise ValueError(
                f"Failed to parse CSV: the file has malformed structure. "
                f"Please check for inconsistent column counts or invalid delimiters. ({e})"
            ) from e
        except Exception as e:
            raise ValueError(
                f"Failed to read CSV file: {type(e).__name__}: {e}"
            ) from e

        if df.empty:
            raise ValueError(
                "The CSV file contains no data rows. Please ensure the file has question data."
            )

        logger.info("CSV loaded: %d rows, columns: %s", len(df), list(df.columns))
        return dataframe_to_questions(df)
