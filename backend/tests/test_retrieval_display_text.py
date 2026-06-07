from backend.app.services.retrieval_display_text import (
    clean_feature_title,
    clean_summary_text,
    feature_title_from_card,
    feature_title_from_source,
    source_title_from_card,
)


def test_clean_feature_title_removes_broken_menu_icon_prefix() -> None:
    # Given: a PDF-extracted menu heading with broken arrow and empty icon glyphs.
    title = " [ ]  [ ]  [하이브리드 줌(동영상)] 선택"

    # When: the text is cleaned for feature-card display.
    cleaned = clean_feature_title(title)

    # Then: only the user-facing feature label remains.
    assert cleaned == "하이브리드 줌(동영상)"


def test_clean_feature_title_keeps_plain_title_unchanged() -> None:
    # Given: a normal section title.
    title = "제브라 패턴"

    # When: the text is cleaned for feature-card display.
    cleaned = clean_feature_title(title)

    # Then: the title is not rewritten.
    assert cleaned == title


def test_clean_feature_title_removes_broken_bullet_glyph() -> None:
    # Given: a PDF-extracted heading with a broken bullet glyph.
    title = " [크롭 줌(사진)] 사용하기"

    # When: the text is cleaned for feature-card display.
    cleaned = clean_feature_title(title)

    # Then: the broken glyph and action suffix are removed.
    assert cleaned == "크롭 줌(사진)"


def test_clean_feature_title_removes_broken_ge_marker_prefix() -> None:
    # Given: a PDF-extracted heading with a broken list marker.
    title = "≥배터리 팩"

    # When: the text is cleaned for feature-card display.
    cleaned = clean_feature_title(title)

    # Then: the marker is removed from the title prefix.
    assert cleaned == "배터리 팩"


def test_clean_feature_title_removes_spaced_ge_marker_prefix() -> None:
    # Given: a PDF-extracted heading with a spaced broken list marker.
    title = "≥ 하이브리드 줌(사진)/크롭 줌(사진)"

    # When: the text is cleaned for feature-card display.
    cleaned = clean_feature_title(title)

    # Then: the marker is removed and the combined title is preserved.
    assert cleaned == "하이브리드 줌(사진)/크롭 줌(사진)"


def test_clean_feature_title_unwraps_plain_bracketed_title() -> None:
    # Given: a PDF-extracted title wrapped in literal brackets.
    title = "[크롭 줌(사진)]"

    # When: the text is cleaned for feature-card display.
    cleaned = clean_feature_title(title)

    # Then: the display title omits extraction brackets.
    assert cleaned == "크롭 줌(사진)"


def test_clean_feature_title_removes_step_number_and_instruction_suffix() -> None:
    # Given: a PDF-extracted instruction line promoted into a heading.
    title = "2 [하이브리드 줌(사진)]를 설정하십시오."

    # When: the text is cleaned for feature-card display.
    cleaned = clean_feature_title(title)

    # Then: the display title keeps only the feature name.
    assert cleaned == "하이브리드 줌(사진)"


def test_clean_feature_title_removes_menu_path_prefix() -> None:
    # Given: a PDF-extracted menu path promoted into a heading.
    title = "/ > > [초점 피킹] 선택"

    # When: the text is cleaned for feature-card display.
    cleaned = clean_feature_title(title)

    # Then: only the selected feature name remains.
    assert cleaned == "초점 피킹"


def test_clean_feature_title_removes_plain_step_number_prefix() -> None:
    # Given: a PDF-extracted procedure step promoted into a heading.
    title = "4 초점을 조절합니다."

    # When: the text is cleaned for feature-card display.
    cleaned = clean_feature_title(title)

    # Then: the procedure number is not shown as part of the feature title.
    assert cleaned == "초점을 조절합니다."


def test_clean_summary_text_removes_broken_empty_menu_icons() -> None:
    # Given: a summary snippet containing broken PDF menu icon text.
    summary = " [ ]  [ ]  [전기 절약 모드] 선택 후 설정합니다."

    # When: the text is cleaned for summary display.
    cleaned = clean_summary_text(summary)

    # Then: broken icon glyphs are gone while the meaningful Korean text remains.
    assert "" not in cleaned
    assert "[ ]" not in cleaned
    assert "전기 절약 모드" in cleaned


def test_clean_summary_text_removes_pdf_page_cross_reference() -> None:
    # Given: a PDF-extracted snippet containing an internal page reference.
    summary = "[초점 피킹] (l 310)"

    # When: the text is cleaned for summary display.
    cleaned = clean_summary_text(summary)

    # Then: only the user-facing feature label remains.
    assert cleaned == "초점 피킹"


def test_clean_summary_text_removes_split_pdf_page_cross_reference() -> None:
    # Given: a PDF-extracted snippet with a split internal page reference.
    summary = "• [초점 피킹](초점 피킹 235\n)"

    # When: the text is cleaned for summary display.
    cleaned = clean_summary_text(summary)

    # Then: the broken reference punctuation is removed from the summary.
    assert cleaned == "초점 피킹"


def test_clean_summary_text_removes_korean_parenthesized_page_reference() -> None:
    # Given: a PDF-extracted snippet with a Korean internal page reference.
    summary = "포커스 피킹(초점 피킹 235\n)"

    # When: the text is cleaned for summary display.
    cleaned = clean_summary_text(summary)

    # Then: the parenthesized page reference is removed.
    assert cleaned == "포커스 피킹"


def test_clean_summary_text_removes_nested_markdown_page_reference() -> None:
    # Given: a PDF-extracted markdown link whose target contains a page reference.
    summary = "• [하이브리드 줌(사진)]([하이브리드 줌(사진)]: 244)"

    # When: the text is cleaned for summary display.
    cleaned = clean_summary_text(summary)

    # Then: only the link label remains.
    assert cleaned == "하이브리드 줌(사진)"


def test_clean_summary_text_removes_trailing_bracketed_page_reference() -> None:
    # Given: a PDF-extracted label followed by a bracketed page reference.
    summary = "하이브리드 줌(사진)([하이브리드 줌(사진)]: 244)"

    # When: the text is cleaned for summary display.
    cleaned = clean_summary_text(summary)

    # Then: the display text keeps the leading feature label.
    assert cleaned == "하이브리드 줌(사진)"


def test_clean_summary_text_unwraps_dash_bracketed_feature() -> None:
    # Given: a PDF-extracted list item with a dash and bracketed feature.
    summary = "\N{EN DASH} [하이브리드 줌(사진)]"

    # When: the text is cleaned for summary display.
    cleaned = clean_summary_text(summary)

    # Then: only the feature label remains.
    assert cleaned == "하이브리드 줌(사진)"


def test_clean_summary_text_removes_dash_text_prefix() -> None:
    # Given: a PDF-extracted list item where only the leading dash is noise.
    summary = "\N{EN DASH} 초점 피킹"

    # When: the text is cleaned for summary display.
    cleaned = clean_summary_text(summary)

    # Then: the feature text remains without the list marker.
    assert cleaned == "초점 피킹"


def test_clean_summary_text_uses_colon_suffix_after_menu_path() -> None:
    # Given: a PDF-extracted menu path followed by the actual target feature.
    summary = "> > [프록시 기록 설정] > [실시간 LUT(프록시)] 선택: 하이브리드 줌 동영상"

    # When: the text is cleaned for summary display.
    cleaned = clean_summary_text(summary)

    # Then: the display summary keeps the feature target, not the menu path.
    assert cleaned == "하이브리드 줌 동영상"


def test_clean_summary_text_removes_inline_markdown_page_reference() -> None:
    # Given: a PDF-extracted menu list with inline page-reference links.
    summary = (
        "[초점] [AF 사용자 설정(사진)](AF 사용자 설정(사진) 190\n) "
        "[초점 피킹]"
    )

    # When: the text is cleaned for summary display.
    cleaned = clean_summary_text(summary)

    # Then: inline page-reference syntax is removed while labels remain.
    assert cleaned == "[초점] AF 사용자 설정(사진) [초점 피킹]"


def test_clean_summary_text_splits_pdf_toc_dot_leaders() -> None:
    # Given: PDF table-of-contents text compressed into one extracted line.
    summary = (
        "[크롭 줌(사진)] ................ 191 "
        "[하이브리드 줌(사진)]................ 193"
    )

    # When: the text is cleaned for summary display.
    cleaned = clean_summary_text(summary)

    # Then: dot leaders are removed and each entry is split onto its own line.
    assert cleaned == "크롭 줌(사진) 191\n하이브리드 줌(사진) 193"


def test_clean_summary_text_splits_pdf_toc_ge_separators() -> None:
    # Given: PDF table-of-contents text separated by broken greater-than glyphs.
    summary = (
        "[크롭 줌(사진)]: 191 ≥[하이브리드 줌(사진)]: 194 "
        "≥[크롭 줌(동영상)]: 197 ≥[하이브리드 줌(동영상)]: 201"
    )

    # When: the text is cleaned for summary display.
    cleaned = clean_summary_text(summary)

    # Then: each linked table-of-contents item is split onto its own line.
    assert cleaned == (
        "크롭 줌(사진) 191\n"
        "하이브리드 줌(사진) 194\n"
        "크롭 줌(동영상) 197\n"
        "하이브리드 줌(동영상) 201"
    )


def test_feature_title_from_source_promotes_source_title_for_generic_fn() -> None:
    # Given: a generic PDF section label and a precise source title.
    feature_name = "Fn"
    source_title = "하이브리드 줌(동영상)"

    # When: the display feature title is selected.
    title = feature_title_from_source(
        feature_name=feature_name,
        source_title=source_title,
    )

    # Then: the precise user-facing source title replaces the generic label.
    assert title == source_title


def test_feature_title_from_card_uses_content_when_title_is_symbol() -> None:
    # Given: a broken one-character PDF heading and meaningful card content.
    feature_name = "\N{MULTIPLICATION SIGN}"
    source_title = "\N{MULTIPLICATION SIGN}"
    content = "[초점 피킹] (l 310)"

    # When: the display title is selected for the card.
    title = feature_title_from_card(
        feature_name=feature_name,
        source_title=source_title,
        content=content,
    )

    # Then: the feature name is recovered from the content.
    assert title == "초점 피킹"


def test_feature_title_from_card_uses_content_when_title_is_number() -> None:
    # Given: a broken numeric PDF heading and meaningful card content.
    feature_name = "1"
    source_title = "1"
    content = "[초점 피킹] (l 310)"

    # When: the display title is selected for the card.
    title = feature_title_from_card(
        feature_name=feature_name,
        source_title=source_title,
        content=content,
    )

    # Then: the feature name is recovered from the content.
    assert title == "초점 피킹"


def test_feature_title_from_card_uses_content_when_title_is_menu_path() -> None:
    # Given: a PDF menu path was promoted as the section title.
    feature_name = "> > [프록시 기록 설정] > [실시간 LUT(프록시)] 선택"
    source_title = feature_name
    content = f"{feature_name}: 하이브리드 줌 동영상"

    # When: the display title is selected for the card.
    title = feature_title_from_card(
        feature_name=feature_name,
        source_title=source_title,
        content=content,
    )

    # Then: the recovered feature target is used instead of the menu path.
    assert title == "하이브리드 줌 동영상"


def test_source_title_from_card_uses_fallback_when_title_is_number() -> None:
    # Given: a broken numeric source title and a recovered card title.
    source_title = "1"
    fallback_title = "초점 피킹"

    # When: the source title is selected for display.
    title = source_title_from_card(
        source_title=source_title,
        fallback_title=fallback_title,
    )

    # Then: the footer source title does not show the broken number.
    assert title == fallback_title
