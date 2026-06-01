from typing import Annotated

from fastapi import APIRouter, Body, Depends

from raya_trade_app.ai_agent.api.v1.dependency import get_ai_service
from raya_trade_app.ai_agent.api.v1.dto import StrategyGeneratorDTO, AIDataDTO
from raya_trade_app.ai_agent.domain import AiData
from raya_trade_app.ai_agent.service import AIService

router = APIRouter(
    prefix="/api/v1",
    tags=["ai"],
)


@router.post("/strategy/generator")
async def strategy_generator(
    body: Annotated[StrategyGeneratorDTO, Body()],
    ai_agent_service: Annotated[AIService, Depends(get_ai_service)],
) -> AIDataDTO:
    data = await ai_agent_service.zero_shot_qa(
        AiData(
            system_message="""You are a professional Forex trading strategy parser. Your sole purpose is to extract trading strategy information from user input and return it as STRICTLY VALID JSON matching the schema below.

# CRITICAL RULES — DO NOT VIOLATE:
1. Your output MUST be a single valid JSON object — nothing else.
2. NEVER include markdown code blocks (no ```), explanations, or any text outside JSON.
3. ALL extracted strategy output MUST be converted into MQ5 (MetaTrader 5 Expert Advisor code format).
4. The final output MUST be wrapped in this structure exactly:
{
  "text": "MQ5_CODE_HERE"
}
5. Inside "text", you must return ONLY valid MQ5 code as plain text.
6. DO NOT use \n, backslashes, or escape characters.
7. DO NOT include JSON inside MQ5. MQ5 must be pure code.
8. If a field is missing, use default MQ5-safe values or omit logic in code.
9. Never output explanations or anything except the final JSON object.

# OUTPUT FORMAT (STRICT):
{
  "text": "MQ5 code generated from strategy"
}

# IMPORTANT:
- The MQ5 code must represent the trading strategy as a MetaTrader 5 Expert Advisor.
- No JSON schema output is allowed anymore.
- No prose, no markdown, no formatting.

# EXAMPLE OUTPUT:
{
  "text": "void OnTick(){ if(RSI<30) Buy(); if(RSI>70) Sell(); }"
}"""
            ,
            input_prompt=body.input_prompt,
            model_output=None,
            rate=None,
        )
    )
    return AIDataDTO(data=data)

