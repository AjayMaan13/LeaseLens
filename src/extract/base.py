"""Common interface every extraction system implements, so evaluation code
in Phase 5 can treat regex/NER/LLM identically regardless of internals."""
from src.schema import LeaseFields


class Extractor:
    name = "base"

    def extract(self, text: str) -> LeaseFields:
        raise NotImplementedError
