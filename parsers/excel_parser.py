import io
import logging
from typing import List, Dict, Any

import pandas as pd

from .base import BaseParser
from .dataframe_utils import dataframe_to_questions

logger = logging.getLogger(__name__)


class ExcelParser(BaseParser):
    """Parses Excel (.xlsx, .xls) files. Same column layout as CsvParser."""

    SUPPORTED_EXTENSIONS = (".xlsx", ".xls")
    SUPPORTED_CONTENT_TYPES = (
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "application/vnd.ms-excel",
    )

    def supports(self, filename: str, content_type: str) -> bool:
        # Avoid claiming .csv files that share the vnd.ms-excel content type
        if filename.lower().endswith(".csv"):
            return False
        return (
            filename.lower().endswith(self.SUPPORTED_EXTENSIONS)
            or content_type in self.SUPPORTED_CONTENT_TYPES
        )

    def parse(self, file_bytes: bytes) -> List[Dict[str, Any]]:
        df = pd.read_excel(io.BytesIO(file_bytes))
        logger.info("Excel loaded: %d rows", len(df))
        return dataframe_to_questions(df)
