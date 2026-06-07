import re
from typing import Final

SUMMARY_LIMIT: Final = 180
GENERIC_FEATURE_TITLES: Final[frozenset[str]] = frozenset({"Fn", "목차"})
CORRUPT_PDF_TEXT_RE: Final = re.compile(r"[ÐÑî]")
BROKEN_MENU_PREFIX_RE: Final = re.compile(r"^(?:\s*(?:|➔|→)\s*)?(?:\[\s*\]\s*)+")
LEADING_MENU_MARK_RE: Final = re.compile(r"^(?:\s*(?:|||≥|➔|→)\s*)+")
SPACING_RE: Final = re.compile(r"\s+")
BRACKETED_ACTION_RE: Final = re.compile(r"^\[([^\[\]]+)\]\s*(?:선택|사용하기)$")
MENU_PATH_ACTION_RE: Final = re.compile(
    r"^/?\s*(?:>\s*)+\[([^\[\]]+)\]\s*(?:선택|사용하기)?$",
)
MENU_PATH_COLON_SUFFIX_RE: Final = re.compile(
    r"^/?\s*(?:>\s*)+\[[^\[\]]+\](?:\s*>\s*\[[^\[\]]+\])*\s*(?:선택|사용하기)?\s*:\s*(.+)$",
)
PLAIN_STEP_NUMBER_RE: Final = re.compile(r"^\d+\s+(.+)$")
NUMBERED_BRACKETED_INSTRUCTION_RE: Final = re.compile(
    r"^\d+\s+\[([^\[\]]+)\](?:를|을)?\s*.+$",
)
BRACKETED_TITLE_RE: Final = re.compile(r"^\[([^\[\]]+)\]$")
BULLET_BRACKETED_TITLE_RE: Final = re.compile(r"^\s*[•*-]\s*\[([^\[\]]+)\]\s*$")
DASH_BRACKETED_TITLE_RE: Final = re.compile(
    r"^\s*[-\N{EN DASH}]\s*\[([^\[\]]+)\]\s*$",
)
DASH_TEXT_PREFIX_RE: Final = re.compile(r"^\s*[-\N{EN DASH}]\s*(?=\S)(.+)$")
INTERNAL_PAGE_REFERENCE_RE: Final = re.compile(r"\s*\(\s*[lI]\s*\d+\s*\)")
PAREN_PAGE_REFERENCE_RE: Final = re.compile(r"\s*\([^\)]*?\d+\s*\)")
BROKEN_MARKDOWN_PAGE_LINK_RE: Final = re.compile(
    r"^\s*[•*-]?\s*\[([^\[\]]+)\]\s*\(.*?\d+\s*\)\s*$",
)
INLINE_MARKDOWN_PAGE_LINK_RE: Final = re.compile(r"\[([^\[\]]+)\]\s*\(.*?\d+\s*\)")
TRAILING_BRACKETED_PAGE_REFERENCE_RE: Final = re.compile(
    r"\s*\(\s*\[[^\]]+\]\s*:?\s*\d+\s*\)\s*$",
)
TOC_BRACKETED_DOT_LEADER_RE: Final = re.compile(
    r"\[([^\[\]]+)\]\s*\.{3,}\s*(\d+)",
)
TOC_BRACKETED_PAGE_RE: Final = re.compile(r"\[([^\[\]]+)\]\s*:?\s*(\d+)")
TOC_TEXT_DOT_LEADER_RE: Final = re.compile(
    r"(?<!\S)([^\[\].\n][^.\n]{1,80}?)\s*\.{3,}\s*(\d+)",
)
SPACE_BEFORE_PUNCTUATION_RE: Final = re.compile(r"\s+([.,:;!?])")
PARENTHESIZED_SPACING_RE: Final = re.compile(r"\(\s*([^)]+?)\s*\)")
BROKEN_KOREAN_SPACING_REPLACEMENTS: Final[tuple[tuple[str, str], ...]] = (
    ("기능 버 튼들", "기능 버튼들"),
    ("새 연 결", "새 연결"),
    ("사 용할", "사용할"),
)


def clean_feature_title(value: str) -> str:
    cleaned = _unwrap_bracketed_selection(_clean_common(value))
    return cleaned or value.strip()


def clean_summary_text(value: str) -> str:
    return _clean_toc_dot_leaders(
        _unwrap_broken_markdown_page_link(
            _unwrap_bracketed_selection(_clean_common(value)),
        ),
    )


def feature_title_from_source(*, feature_name: str, source_title: str) -> str:
    cleaned_feature_name = clean_feature_title(feature_name)
    cleaned_source_title = clean_feature_title(source_title)
    if cleaned_feature_name in GENERIC_FEATURE_TITLES:
        return cleaned_source_title
    return cleaned_feature_name


def feature_title_from_card(
    *,
    feature_name: str,
    source_title: str,
    content: str,
) -> str:
    cleaned_feature_name = clean_feature_title(feature_name)
    if _is_meaningful_feature_title(cleaned_feature_name):
        return cleaned_feature_name

    cleaned_source_title = clean_feature_title(source_title)
    if _is_meaningful_feature_title(cleaned_source_title):
        return cleaned_source_title

    content_title = _feature_title_from_content(content)
    if content_title:
        return content_title
    return cleaned_feature_name or cleaned_source_title or "기능"


def source_title_from_card(*, source_title: str, fallback_title: str) -> str:
    cleaned_source_title = clean_feature_title(source_title)
    if _is_meaningful_feature_title(cleaned_source_title):
        return cleaned_source_title
    return fallback_title


def summary_text(content: str) -> str:
    normalized = clean_summary_text(content)
    if len(normalized) <= SUMMARY_LIMIT:
        return normalized
    return f"{normalized[:SUMMARY_LIMIT]}..."


def _clean_common(value: str) -> str:
    cleaned = value
    previous: str | None = None
    while previous != cleaned:
        previous = cleaned
        cleaned = LEADING_MENU_MARK_RE.sub("", cleaned)
        cleaned = BROKEN_MENU_PREFIX_RE.sub("", cleaned)
    cleaned = cleaned.replace("", " > ")
    cleaned = cleaned.replace("", "")
    cleaned = cleaned.replace("", "")
    cleaned = cleaned.replace("[ ]", "")
    markdown_match = BROKEN_MARKDOWN_PAGE_LINK_RE.fullmatch(cleaned.strip())
    if markdown_match is not None:
        return markdown_match.group(1).strip()
    cleaned = INLINE_MARKDOWN_PAGE_LINK_RE.sub(r"\1", cleaned)
    cleaned = TRAILING_BRACKETED_PAGE_REFERENCE_RE.sub("", cleaned)
    cleaned = INTERNAL_PAGE_REFERENCE_RE.sub("", cleaned)
    cleaned = PAREN_PAGE_REFERENCE_RE.sub("", cleaned)
    cleaned = SPACING_RE.sub(" ", cleaned).strip()
    cleaned = _repair_pdf_spacing(cleaned)
    return SPACE_BEFORE_PUNCTUATION_RE.sub(r"\1", cleaned)


def _repair_pdf_spacing(value: str) -> str:
    cleaned = value
    for broken, repaired in BROKEN_KOREAN_SPACING_REPLACEMENTS:
        cleaned = cleaned.replace(broken, repaired)
    return PARENTHESIZED_SPACING_RE.sub(r"(\1)", cleaned)


def _unwrap_bracketed_selection(value: str) -> str:
    menu_suffix_match = MENU_PATH_COLON_SUFFIX_RE.fullmatch(value)
    if menu_suffix_match is not None:
        return menu_suffix_match.group(1).strip()

    match = (
        BRACKETED_ACTION_RE.fullmatch(value)
        or MENU_PATH_ACTION_RE.fullmatch(value)
        or NUMBERED_BRACKETED_INSTRUCTION_RE.fullmatch(value)
        or BRACKETED_TITLE_RE.fullmatch(value)
        or BULLET_BRACKETED_TITLE_RE.fullmatch(value)
        or DASH_BRACKETED_TITLE_RE.fullmatch(value)
    )
    if match is None:
        numbered_match = PLAIN_STEP_NUMBER_RE.fullmatch(value)
        if numbered_match is not None:
            return numbered_match.group(1).strip()
        dash_text_match = DASH_TEXT_PREFIX_RE.fullmatch(value)
        if dash_text_match is not None:
            return dash_text_match.group(1).strip()
        return value
    return match.group(1).strip()


def _unwrap_broken_markdown_page_link(value: str) -> str:
    match = BROKEN_MARKDOWN_PAGE_LINK_RE.fullmatch(value)
    if match is None:
        return value
    return match.group(1).strip()


def _is_meaningful_feature_title(value: str) -> bool:
    if value in GENERIC_FEATURE_TITLES:
        return False
    if CORRUPT_PDF_TEXT_RE.search(value) is not None:
        return False
    if value.lstrip().startswith(">"):
        return False
    if value.isdigit():
        return False
    return any(character.isalnum() for character in value) and len(value) > 1


def _feature_title_from_content(content: str) -> str:
    cleaned = clean_summary_text(content)
    first_line = cleaned.splitlines()[0] if cleaned else ""
    if not first_line:
        return ""
    return clean_feature_title(first_line)


def _clean_toc_dot_leaders(value: str) -> str:
    cleaned = TOC_BRACKETED_DOT_LEADER_RE.sub(r"\1 \2\n", value)
    cleaned = TOC_BRACKETED_PAGE_RE.sub(r"\1 \2\n", cleaned)
    cleaned = TOC_TEXT_DOT_LEADER_RE.sub(r"\1 \2\n", cleaned)
    cleaned = cleaned.replace("≥", "")
    return "\n".join(line.strip() for line in cleaned.splitlines() if line.strip())
