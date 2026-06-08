import re
from typing import Final

SUMMARY_LIMIT: Final = 180
GENERIC_FEATURE_TITLES: Final[frozenset[str]] = frozenset({"Fn", "목차"})
CORRUPT_PDF_TEXT_RE: Final = re.compile(r"[ÐÑî]")
RIGHT_SINGLE_QUOTE: Final = "\N{RIGHT SINGLE QUOTATION MARK}"
RIGHT_DOUBLE_QUOTE: Final = "\N{RIGHT DOUBLE QUOTATION MARK}"
DATE_LIKE_TITLE_RE: Final = re.compile(r"^(?:\d{4}/\d{2}/\d{2}){1,2}$")
TIMECODE_LIKE_TITLE_RE: Final = re.compile(r"^\d+\s*:\s*\d{2,3}\s*:\s*\d{2}$")
PLAYBACK_TIME_SAMPLE_RE: Final = re.compile(
    rf"^\d{{1,2}}:\d{{2}}[{RIGHT_SINGLE_QUOTE}']\d{{2}}[{RIGHT_DOUBLE_QUOTE}\"]$",
)
FILE_NUMBER_SAMPLE_RE: Final = re.compile(r"^\d{3}-\d{4}$")
DIAGRAM_LABEL_RE: Final = re.compile(r"^\([A-Za-z]\)$")
EXPOSURE_SAMPLE_ALLOWED_RE: Final = re.compile(r"^[0-9Ff/+\-.\s]+$")
EXPOSURE_SAMPLE_SIGNAL_RE: Final = re.compile(r"(?:\d+/\d+|F\s?\d)", re.IGNORECASE)
BROKEN_MENU_PREFIX_RE: Final = re.compile(r"^(?:\s*(?:||➔|→)\s*)?(?:\[\s*\]\s*)+")
LEADING_MENU_MARK_RE: Final = re.compile(r"^(?:\s*(?:||||≥|➔|→|●)\s*)+")
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
TOC_BRACKETED_TITLE_DOT_LEADER_RE: Final = re.compile(
    r"^\[([^\[\]]+)\]\s*\.{3,}\s*\d+$",
)
TOC_BRACKETED_PAGE_RE: Final = re.compile(r"\[([^\[\]]+)\]\s*:?\s*(\d+)")
INLINE_BRACKETED_FEATURE_RE: Final = re.compile(r"\[([^\[\]]*[가-힣][^\[\]]*)\]")
TOC_TEXT_DOT_LEADER_RE: Final = re.compile(
    r"(?<!\S)([^\[\].\n][^.\n]{1,80}?)\s*\.{3,}\s*(\d+)",
)
TOC_TEXT_TITLE_DOT_LEADER_RE: Final = re.compile(r"^(.{1,80}?)\s*\.{3,}\s*\d+$")
DASH_LEADER_SUFFIX_RE: Final = re.compile(r"\s*-{3,}\s*$")
SPACE_BEFORE_PUNCTUATION_RE: Final = re.compile(r"\s+([.,:;!?])")
PARENTHESIZED_SPACING_RE: Final = re.compile(r"\(\s*([^)]+?)\s*\)")
BROKEN_KOREAN_SPACING_REPLACEMENTS: Final[tuple[tuple[str, str], ...]] = (
    ("기능 버 튼들", "기능 버튼들"),
    ("새 연 결", "새 연결"),
    ("사 용할", "사용할"),
)


def clean_feature_title(value: str) -> str:
    cleaned = _unwrap_bracketed_selection(_clean_toc_title(_clean_common(value)))
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
    cleaned = cleaned.replace("", " > ")
    cleaned = cleaned.replace("", "")
    cleaned = cleaned.replace("", "")
    cleaned = cleaned.replace("[ ]", "")
    markdown_match = BROKEN_MARKDOWN_PAGE_LINK_RE.fullmatch(cleaned.strip())
    if markdown_match is not None:
        return markdown_match.group(1).strip()
    cleaned = INLINE_MARKDOWN_PAGE_LINK_RE.sub(r"\1", cleaned)
    cleaned = DASH_LEADER_SUFFIX_RE.sub("", cleaned)
    cleaned = TRAILING_BRACKETED_PAGE_REFERENCE_RE.sub("", cleaned)
    cleaned = INTERNAL_PAGE_REFERENCE_RE.sub("", cleaned)
    cleaned = PAREN_PAGE_REFERENCE_RE.sub("", cleaned)
    cleaned = SPACING_RE.sub(" ", cleaned).strip()
    cleaned = _collapse_repeated_display_tokens(cleaned)
    cleaned = _repair_pdf_spacing(cleaned)
    return SPACE_BEFORE_PUNCTUATION_RE.sub(r"\1", cleaned)


def _repair_pdf_spacing(value: str) -> str:
    cleaned = value
    for broken, repaired in BROKEN_KOREAN_SPACING_REPLACEMENTS:
        cleaned = cleaned.replace(broken, repaired)
    return PARENTHESIZED_SPACING_RE.sub(r"(\1)", cleaned)


def _collapse_repeated_display_tokens(value: str) -> str:
    collapsed_tokens = [_collapse_repeated_token(token) for token in value.split()]
    deduplicated: list[str] = []
    for token in collapsed_tokens:
        if deduplicated and deduplicated[-1] == token:
            continue
        deduplicated.append(token)
    return " ".join(deduplicated)


def _collapse_repeated_token(token: str) -> str:
    midpoint, remainder = divmod(len(token), 2)
    if remainder != 0 or midpoint == 0:
        return token
    prefix = token[:midpoint]
    if prefix != token[midpoint:]:
        return token
    if prefix.isdigit():
        return token
    return prefix


def _clean_toc_title(value: str) -> str:
    bracketed_match = TOC_BRACKETED_TITLE_DOT_LEADER_RE.fullmatch(value)
    if bracketed_match is not None:
        return bracketed_match.group(1).strip()
    text_match = TOC_TEXT_TITLE_DOT_LEADER_RE.fullmatch(value)
    if text_match is not None:
        return text_match.group(1).strip()
    return value


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
    if _is_noise_feature_title(value):
        return False
    return any(character.isalnum() for character in value) and len(value) > 1


def _is_noise_feature_title(value: str) -> bool:
    compact = "".join(value.split())
    return (
        value in GENERIC_FEATURE_TITLES
        or CORRUPT_PDF_TEXT_RE.search(value) is not None
        or value.lstrip().startswith(">")
        or value.isdigit()
        or DATE_LIKE_TITLE_RE.fullmatch(compact) is not None
        or TIMECODE_LIKE_TITLE_RE.fullmatch(value) is not None
        or PLAYBACK_TIME_SAMPLE_RE.fullmatch(value) is not None
        or FILE_NUMBER_SAMPLE_RE.fullmatch(value) is not None
        or DIAGRAM_LABEL_RE.fullmatch(value) is not None
        or _is_exposure_sample_title(compact)
    )


def _is_exposure_sample_title(value: str) -> bool:
    return (
        EXPOSURE_SAMPLE_ALLOWED_RE.fullmatch(value) is not None
        and EXPOSURE_SAMPLE_SIGNAL_RE.search(value) is not None
    )


def _feature_title_from_content(content: str) -> str:
    cleaned = clean_summary_text(content)
    first_line = cleaned.splitlines()[0] if cleaned else ""
    if not first_line:
        return ""
    inline_feature_match = INLINE_BRACKETED_FEATURE_RE.search(first_line)
    if inline_feature_match is not None:
        inline_feature = clean_feature_title(inline_feature_match.group(1))
        if _is_meaningful_feature_title(inline_feature):
            return inline_feature
    return clean_feature_title(first_line)


def _clean_toc_dot_leaders(value: str) -> str:
    cleaned = TOC_BRACKETED_DOT_LEADER_RE.sub(r"\1 \2\n", value)
    cleaned = TOC_BRACKETED_PAGE_RE.sub(r"\1 \2\n", cleaned)
    cleaned = TOC_TEXT_DOT_LEADER_RE.sub(r"\1 \2\n", cleaned)
    cleaned = cleaned.replace("≥", "")
    return "\n".join(line.strip() for line in cleaned.splitlines() if line.strip())
