"""Pydantic schemas for the OpenAI-compatible public API."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    role: Literal["system", "user", "assistant", "tool"]
    content: str | list[dict[str, Any]] | None = None
    name: str | None = None


class ChatCompletionRequest(BaseModel):
    model: str = "keprix"
    messages: list[ChatMessage]
    stream: bool = False
    temperature: float | None = None
    max_tokens: int | None = None
    tools: list[dict[str, Any]] | None = None


class ChatCompletionChoice(BaseModel):
    index: int
    message: ChatMessage
    finish_reason: Literal["stop", "length", "tool_calls"] = "stop"


class UsageInfo(BaseModel):
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


class ChatCompletionResponse(BaseModel):
    id: str
    object: Literal["chat.completion"] = "chat.completion"
    created: int
    model: str
    choices: list[ChatCompletionChoice]
    usage: UsageInfo


class ModelObject(BaseModel):
    id: str
    object: Literal["model"] = "model"
    created: int
    owned_by: str = "keprix"


class ModelListResponse(BaseModel):
    object: Literal["list"] = "list"
    data: list[ModelObject]


class EmbeddingRequest(BaseModel):
    model: str = "keprix-embed"
    input: str | list[str]


class EmbeddingData(BaseModel):
    object: Literal["embedding"] = "embedding"
    index: int
    embedding: list[float]


class EmbeddingResponse(BaseModel):
    object: Literal["list"] = "list"
    data: list[EmbeddingData]
    model: str
    usage: UsageInfo


class ResponseCreateRequest(BaseModel):
    model: str = "keprix"
    input: str | list[ChatMessage]
    instructions: str | None = None
    stream: bool = False


class ResponseObject(BaseModel):
    id: str
    object: Literal["response"] = "response"
    created: int
    model: str
    output_text: str
    usage: UsageInfo


class CreateApiKeyRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=128)
    workspace_id: str = "default"
    role: str = "developer"
    allowed_models: list[str] = Field(default_factory=list)
    allowed_endpoints: list[str] = Field(default_factory=list)
    monthly_limit: int | None = None
    scopes: dict[str, bool] = Field(default_factory=dict)


class ApiKeyRecord(BaseModel):
    id: str
    name: str
    key_prefix: str
    workspace_id: str
    role: str
    allowed_models: list[str]
    allowed_endpoints: list[str]
    monthly_limit: int | None
    usage_this_month: int
    created_at: str
    revoked: bool = False


class CreateApiKeyResponse(ApiKeyRecord):
    secret: str


class WebhookCreateRequest(BaseModel):
    url: str
    events: list[str] = Field(default_factory=lambda: ["chat.completed"])
    workspace_id: str = "default"


class WebhookRecord(BaseModel):
    id: str
    url: str
    events: list[str]
    workspace_id: str
    created_at: str
    disabled: bool = False
