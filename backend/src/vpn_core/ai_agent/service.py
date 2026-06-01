from raya_trade_app.ai_agent.agent.base import BaseAgent
from raya_trade_app.ai_agent.domain import AiData


class AIService:
    def __init__(self, agent: BaseAgent):
        self._agent = agent

    async def zero_shot_qa(
            self,
            data: AiData,
    ):
        return await self._agent.zero_shot_question_answering(
            data=data,
        )
