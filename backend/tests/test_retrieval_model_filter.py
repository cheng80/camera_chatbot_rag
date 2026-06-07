from backend.app.services.retrieval_model_filter import supported_model_ids


def test_supported_model_ids_keeps_all_models_without_filter() -> None:
    result = supported_model_ids(("DC-TZ99", "DC-ZS99"), ())

    assert result == ("DC-TZ99", "DC-ZS99")


def test_supported_model_ids_limits_to_requested_models() -> None:
    result = supported_model_ids(("DC-TZ99", "DC-ZS99"), ("DC-ZS99",))

    assert result == ("DC-ZS99",)


def test_supported_model_ids_preserves_result_when_filter_does_not_overlap() -> None:
    result = supported_model_ids(("DC-TZ99", "DC-ZS99"), ("DC-G9M2",))

    assert result == ("DC-TZ99", "DC-ZS99")
