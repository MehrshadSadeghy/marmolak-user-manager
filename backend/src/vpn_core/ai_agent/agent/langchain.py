from langchain_core.messages import HumanMessage, SystemMessage

from raya_trade_app.ai_agent.agent.base import BaseAgent
from raya_trade_app.ai_agent.domain import AiData


class LangchainAgent(BaseAgent):
    def __init__(self, model):
        self._model = model

    async def zero_shot_question_answering(self, data: AiData) -> AiData:
        system_msg = SystemMessage(content=data.system_message)
        human_msg = HumanMessage(content=data.input_prompt)

        response = await self._model.ainvoke([system_msg, human_msg])

        return AiData(
            id=data.id,
            system_message=data.system_message,
            input_prompt=data.input_prompt,
            model_output=response.content,
            rate=None,
        )

    async def few_shot_question_answering(self, data, example: AiData):
        pass