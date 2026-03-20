from abc import ABC, abstractmethod
from typing import List, Dict, Any


class BaseParser(ABC):
    """Base class for all file parsers. Each parser handles one file type."""

    @abstractmethod
    def supports(self, filename: str, content_type: str) -> bool:
        """Return True if this parser can handle the given file."""
        ...

    @abstractmethod
    def parse(self, file_bytes: bytes) -> List[Dict[str, Any]]:
        """Parse the file bytes and return a list of question dicts."""
        ...
