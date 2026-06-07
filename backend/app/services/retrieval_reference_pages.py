import re
from dataclasses import dataclass
from typing import Final

from backend.app.indexing.fts_index import FtsSearchResult
from backend.app.schemas.search import NormalizedQuery
from backend.app.services.korean_text_normalization import (
    normalize_korean_compound_aliases,
)

REFERENCE_PATTERN: Final = re.compile(
    r"\s*\[?(?P<label>[^\]\n:]+)\]?\s*:\s*(?P<page>\d{1,4})",
)
TERM_PATTERN: Final = re.compile(r"[0-9A-Za-z가-힣.]{2,}")


@dataclass(frozen=True, slots=True)
class ReferencedPage:
    page: int
    label: str


def referenced_page_for_query(
    *,
    result: FtsSearchResult,
    normalized_query: NormalizedQuery,
) -> ReferencedPage | None:
    query_text = normalized_query.search_query or " ".join(normalized_query.terms)
    query_terms = _terms(query_text)
    if not query_terms:
        return None
    for referenced_page in _referenced_pages(result.content):
        label_terms = _terms(referenced_page.label)
        if query_terms.issubset(label_terms) or label_terms.issubset(query_terms):
            return referenced_page
    return None


def _referenced_pages(content: str) -> tuple[ReferencedPage, ...]:
    return tuple(
        ReferencedPage(
            page=int(match.group("page")),
            label=normalize_korean_compound_aliases(match.group("label")),
        )
        for match in REFERENCE_PATTERN.finditer(content)
    )


def _terms(value: str) -> set[str]:
    normalized = normalize_korean_compound_aliases(value).casefold()
    return {match.group(0) for match in TERM_PATTERN.finditer(normalized)}
