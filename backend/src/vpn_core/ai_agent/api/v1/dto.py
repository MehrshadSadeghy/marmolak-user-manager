from pydantic import BaseModel

from raya_trade_app.ai_agent.domain import AiData


class StrategyGeneratorDTO(BaseModel):
    input_prompt: str


class AIDataDTO(BaseModel):
    data: AiData
