def supported_model_ids(
    result_model_ids: tuple[str, ...],
    requested_model_ids: tuple[str, ...],
) -> tuple[str, ...]:
    if not requested_model_ids:
        return result_model_ids
    matched = tuple(
        model_id for model_id in result_model_ids if model_id in requested_model_ids
    )
    return matched or result_model_ids
