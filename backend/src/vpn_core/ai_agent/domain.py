import uuid
from uuid import UUID

from langchain_core.messages import SystemMessage
from pydantic import BaseModel, Field


class AiData(BaseModel):
    id: UUID = Field(default_factory=uuid.uuid4)
    system_message: str
    input_prompt: str
    model_output: str | None
    rate: float | None
