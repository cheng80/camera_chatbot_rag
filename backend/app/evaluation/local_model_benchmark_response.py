from typing import ClassVar

from pydantic import BaseModel, ConfigDict, Field


class ChatCompletionMessage(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True, extra="ignore")

    content: str = ""


class ChatCompletionChoice(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True, extra="ignore")

    message: ChatCompletionMessage


class ChatCompletionUsage(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True, extra="ignore")

    prompt_tokens: int = Field(default=0, ge=0)
    completion_tokens: int = Field(default=0, ge=0)
    total_tokens: int = Field(default=0, ge=0)


class ChatCompletionResponse(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True, extra="ignore")

    choices: tuple[ChatCompletionChoice, ...]
    usage: ChatCompletionUsage = Field(default_factory=ChatCompletionUsage)

    def first_content(self) -> str:
        if not self.choices:
            return ""
        return self.choices[0].message.content
