from backend.app.core.settings import Settings


def select_llm_model(*, settings: Settings, requires_thinking: bool) -> str:
    match settings.llm_selection_mode:
        case "fixed":
            return settings.llm_model
        case "auto":
            if requires_thinking:
                return settings.llm_thinking_model
            return settings.llm_fast_model
