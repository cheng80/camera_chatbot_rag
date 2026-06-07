from typing import Final

SUBJECT_STRIP_CHARS: Final = "[]() "


def subject_prefixed_answer(
    *,
    subject: str,
    answer_text: str,
    needs_more_context: bool,
) -> str:
    answer = " ".join(answer_text.split()).strip()
    clean_subject = _clean_subject(subject)
    if needs_more_context or not clean_subject or clean_subject in answer:
        return answer
    return f"{clean_subject}: {answer}"


def _clean_subject(subject: str) -> str:
    return " ".join(subject.split()).strip(SUBJECT_STRIP_CHARS)
