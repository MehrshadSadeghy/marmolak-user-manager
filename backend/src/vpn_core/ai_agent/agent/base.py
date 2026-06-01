from abc import ABC, abstractmethod

from langchain.chat_models import init_chat_model
from langchain_core.messages import SystemMessage

from raya_trade_app.ai_agent.domain import AiData
from raya_trade_app.strategy.db.strategy import Strategy




class BaseAgent(ABC):
    @abstractmethod
    async def   zero_shot_question_answering(self, data: AiData) -> Strategy:
        pass

    @abstractmethod
    async def few_shot_question_answering(self, data: Strategy, example: AiData, ) -> Strategy:
        pass


