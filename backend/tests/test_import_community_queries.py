from pathlib import Path

from backend.app.evaluation.import_community_queries import (
    extract_community_query_candidates,
    write_community_query_candidates,
)


def test_extract_community_query_candidates_filters_titles(tmp_path: Path) -> None:
    raw_path = tmp_path / "naver.txt"
    _ = raw_path.write_text(
        """201652

[S9]충전기 문의드립니다댓글수[6]새 게시글 있음
파주남멤버등급 : 일반회원
2026.06.06.\t41\t0
201629
[루믹스s9] 실시간 노출 미리보기가 S모드에서 안됩니다.???댓글수[2]새 게시글 있음
거칠은청년멤버등급 : 일반회원
2026.06.06.\t75\t1""",
        encoding="utf-8",
    )

    candidates = extract_community_query_candidates(raw_path)

    assert len(candidates) == 2
    assert candidates[0].query == "[S9]충전기 문의드립니다"
    assert candidates[0].category == "lens_accessory"
    assert candidates[0].include_for_labeling is False
    expected_query = "[루믹스s9] 실시간 노출 미리보기가 S모드에서 안됩니다.???"
    assert candidates[1].query == expected_query
    assert candidates[1].category == "camera_feature"
    assert candidates[1].include_for_labeling is True
    assert candidates[1].model_mentions == ("S9",)


def test_write_community_query_candidates_writes_json(tmp_path: Path) -> None:
    raw_path = tmp_path / "naver.txt"
    _ = raw_path.write_text(
        """201487
여행용렌즈 질문드려요~댓글수[11]
루믹스냐소니냐멤버등급 : 일반회원
2026.05.31.\t143\t1""",
        encoding="utf-8",
    )
    candidates = extract_community_query_candidates(raw_path)

    output_path = write_community_query_candidates(
        candidates=candidates,
        path=tmp_path / "community_query_candidates.json",
    )

    assert output_path.is_file()


def test_extract_community_query_candidates_keeps_manual_feature_titles(
    tmp_path: Path,
) -> None:
    raw_path = tmp_path / "naver.txt"
    _ = raw_path.write_text(
        """201123
S9 커스텀(C3) 저장 방법 문의
테스터멤버등급 : 일반회원
2026.05.10.\t100\t0
201124
레시피는 4개까지만 등록 가능한가요??
테스터멤버등급 : 일반회원
2026.05.10.\t100\t0""",
        encoding="utf-8",
    )

    candidates = extract_community_query_candidates(raw_path)

    assert candidates[0].category == "camera_feature"
    assert candidates[0].include_for_labeling is True
    assert candidates[1].category == "camera_feature"
    assert candidates[1].include_for_labeling is True


def test_extract_community_query_candidates_stops_at_next_post_id(
    tmp_path: Path,
) -> None:
    raw_path = tmp_path / "naver.txt"
    _ = raw_path.write_text(
        """198498
FLOW 무선연결 끊김...?
박심백
198497
[S5M2] MP4 24p 설정 질문
테스터멤버등급 : 일반회원
2026.01.01.\t10\t0""",
        encoding="utf-8",
    )

    candidates = extract_community_query_candidates(raw_path)

    assert len(candidates) == 2
    assert candidates[0].query == "FLOW 무선연결 끊김...?"
    assert candidates[1].query == "[S5M2] MP4 24p 설정 질문"


def test_extract_community_query_candidates_rejects_truncated_post_id(
    tmp_path: Path,
) -> None:
    raw_path = tmp_path / "naver.txt"
    _ = raw_path.write_text(
        """01654
파나소닉 S9 괜찮을까요?
작성자멤버등급 : 일반회원
2026.06.06.\t135\t0
201653
S5M2X 배터리 방전이 너무 빠른거 같은데 정상일까요?
작성자멤버등급 : 일반회원
2026.06.06.\t20\t0""",
        encoding="utf-8",
    )

    candidates = extract_community_query_candidates(raw_path)

    assert len(candidates) == 1
    assert candidates[0].post_id == "201653"
    assert candidates[0].model_mentions == ("S5M2X",)
