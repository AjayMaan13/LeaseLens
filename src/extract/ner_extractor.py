"""Pretrained NER as a candidate generator, not a one-shot answer: it finds
that something is MONEY/ORG/LOC, but has no idea whether a given MONEY span
is the rent, the deposit, or the late fee -- that disambiguation is exactly
what this hybrid does NOT attempt, and is reported honestly as the reason
NER alone is insufficient without fine-tuning we don't have the labels for."""
from transformers import pipeline
from src.extract.base import Extractor
from src.schema import LeaseFields

_ner = pipeline("ner", model="dslim/bert-base-NER", aggregation_strategy="simple")


def _word_boundary_chunks(text: str, target=1500, limit=30000):
    """Split on whitespace near `target` chars, not a raw slice -- a raw cut
    can land mid-word (confirmed: sliced "Landlord" into a dangling "##lord"
    entity), which produces garbage tokens the model then misreads as spans."""
    text = text[:limit]
    chunks, start = [], 0
    while start < len(text):
        end = min(start + target, len(text))
        if end < len(text):
            space = text.rfind(" ", start, end)
            if space > start:
                end = space
        chunks.append(text[start:end])
        start = end
    return chunks


class NERExtractor(Extractor):
    name = "ner_hybrid"

    # Defined terms like "Landlord"/"Tenant" are capitalized throughout lease
    # text and get misread as organization names by a generic NER model --
    # a real limitation, not a bug: filtered here rather than silently kept.
    _STOPWORDS = {"landlord", "tenant", "lessor", "lessee", "guarantor", "exhibit"}

    def extract(self, text: str) -> LeaseFields:
        ents = []
        for chunk in _word_boundary_chunks(text):
            ents += _ner(chunk)
        orgs = [e["word"] for e in ents
                if e["entity_group"] == "ORG" and e["word"].strip('" “”').lower() not in self._STOPWORDS
                and not e["word"].startswith("##")]
        locs = [e["word"] for e in ents if e["entity_group"] == "LOC" and not e["word"].startswith("##")]
        return LeaseFields(
            landlord_name=orgs[0] if orgs else None,
            tenant_name=orgs[1] if len(orgs) > 1 else None,
            property_address=locs[0] if locs else None,
        )
