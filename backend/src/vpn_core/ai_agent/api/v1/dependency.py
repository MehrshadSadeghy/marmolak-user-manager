from fastapi import Request

from raya_trade_app.ai_agent.service import AIService

async def get_ai_service(
        request: Request,
) -> AIService:
    container = request.app.state.container
    return await container.get_ai_service()
