import json
from pathlib import Path

from backend.app.indexing.section_documents import SectionDocument
from backend.app.wiki.generator import (
    generate_feature_wiki,
    write_feature_wiki_json,
)
from backend.app.wiki.validator import validate_feature_wiki


def test_generate_feature_wiki_groups_sections_by_canonical_name(
    tmp_path: Path,
) -> None:
    sections_dir = tmp_path / "sections"
    sections_dir.mkdir()
    _write_sections(
        sections_dir / "sample.jsonl",
        (
            _section(
                section_id="sample:section:12:zebra",
                title="제브라 패턴",
                content="제브라 패턴은 휘도 레벨과 과다 노출 표시를 사용합니다.",
                page=12,
            ),
            _section(
                section_id="sample:section:14:zebra",
                title="제브라 패턴",
                content="zebra pattern 표시를 설정합니다.",
                page=14,
            ),
            _section(
                section_id="sample:section:2:toc",
                title="목차",
                content="제브라 패턴........12",
                page=2,
            ),
        ),
    )

    entries = generate_feature_wiki(sections_dir=sections_dir)

    assert len(entries) == 1
    assert entries[0].canonical_name == "제브라 패턴"
    assert entries[0].category == "exposure"
    assert entries[0].source_refs[0].page == 12
    assert "휘도" in entries[0].aliases


def test_generate_feature_wiki_cleans_canonical_label_noise(
    tmp_path: Path,
) -> None:
    sections_dir = tmp_path / "sections"
    sections_dir.mkdir()
    _write_sections(
        sections_dir / "sample.jsonl",
        (
            _section(
                section_id="sample:section:21:tracking_af",
                title="([트래킹 AF]) 설정하기",
                content="트래킹 AF는 움직이는 피사체의 초점을 계속 맞춥니다.",
                page=21,
            ),
            _section(
                section_id="sample:section:22:tracking_af",
                title="[트래킹 AF]",
                content="트래킹 AF 피사체 인식 AF 설정",
                page=22,
            ),
        ),
    )

    entries = generate_feature_wiki(sections_dir=sections_dir)

    assert len(entries) == 1
    assert entries[0].canonical_name == "트래킹 AF"
    assert {source.page for source in entries[0].source_refs} == {21, 22}


def test_generate_feature_wiki_rejects_instruction_like_titles(
    tmp_path: Path,
) -> None:
    sections_dir = tmp_path / "sections"
    sections_dir.mkdir()
    _write_sections(
        sections_dir / "sample.jsonl",
        (
            _section(
                section_id="sample:section:31:photo_style_path",
                title="/ > > [사진 스타일] > [V-Log] 선택",
                content="사진 스타일에서 V-Log를 선택합니다.",
                page=31,
            ),
            _section(
                section_id="sample:section:32:my_color_mode",
                title="( : 마이컬러모드 )",
                content="마이컬러모드의 색상을 설정합니다.",
                page=32,
            ),
            _section(
                section_id="sample:section:33:vlog",
                title="V-Log",
                content="V-Log로 동영상 계조를 기록합니다.",
                page=33,
            ),
        ),
    )

    entries = generate_feature_wiki(sections_dir=sections_dir)

    assert tuple(entry.canonical_name for entry in entries) == ("V-Log",)


def test_write_and_validate_feature_wiki_json(
    tmp_path: Path,
) -> None:
    sections_dir = tmp_path / "sections"
    registry_dir = tmp_path / "registry"
    pages_dir = tmp_path / "pages"
    sections_dir.mkdir()
    registry_dir.mkdir()
    pages_dir.mkdir()
    _write_sections(
        sections_dir / "sample_manual.jsonl",
        (
            _section(
                section_id="sample_manual:section:12:zebra",
                title="제브라 패턴",
                content="제브라 패턴 휘도 레벨",
                page=12,
            ),
        ),
    )
    _write_registry(registry_dir)
    _write_pages(pages_dir)

    entries = generate_feature_wiki(sections_dir=sections_dir)
    output_path = write_feature_wiki_json(
        entries=entries,
        path=tmp_path / "feature_wiki.json",
    )
    report = validate_feature_wiki(
        entries=entries,
        registry_dir=registry_dir,
        pages_dir=pages_dir,
    )

    assert output_path.is_file()
    assert report.entry_count == 1
    assert report.invalid_source_ref_count == 0


def _write_sections(path: Path, sections: tuple[SectionDocument, ...]) -> None:
    _ = path.write_text(
        "\n".join(section.model_dump_json() for section in sections) + "\n",
        encoding="utf-8",
    )


def _section(
    *,
    section_id: str,
    title: str,
    content: str,
    page: int,
) -> SectionDocument:
    return SectionDocument(
        section_id=section_id,
        document_id="sample_manual",
        model_ids=("DC-G9M2",),
        page_start=page,
        page_end=page,
        section_title=title,
        content=content,
        source_chunk_ids=(f"sample_manual:chunk:{page}",),
        source_hash="0" * 64,
    )


def _write_registry(registry_dir: Path) -> None:
    _ = (registry_dir / "documents.json").write_text(
        json.dumps(
            [
                {
                    "document_id": "sample_manual",
                    "title": "Sample Manual",
                    "filename": "sample.pdf",
                    "model_ids": ["DC-G9M2"],
                    "language": "ko",
                    "document_type": "full_manual",
                },
            ],
        )
        + "\n",
        encoding="utf-8",
    )
    _ = (registry_dir / "models.json").write_text(
        json.dumps(
            [
                {
                    "model_id": "DC-G9M2",
                    "display_name": "LUMIX G9II",
                    "product_line": "G",
                },
            ],
        )
        + "\n",
        encoding="utf-8",
    )


def _write_pages(pages_dir: Path) -> None:
    _ = (pages_dir / "sample_manual.jsonl").write_text(
        json.dumps(
            {
                "document_id": "sample_manual",
                "model_ids": ["DC-G9M2"],
                "page": 12,
                "text": "제브라 패턴",
                "char_count": 6,
            },
        )
        + "\n",
        encoding="utf-8",
    )
