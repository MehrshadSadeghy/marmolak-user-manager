
import json
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.params import Path

from raya_trade_app.strategy.api.v1.dependency import get_strategy_service
from raya_trade_app.strategy.api.v1.dto import (
    StrategyGetResponseDTO,
    StrategyUpsetResponseDTO,
    StrategyRowDTO,
    StrategyUpdateDTO,
)
from raya_trade_app.strategy.db.strategy import Strategy
from raya_trade_app.strategy.service import StrategyService

router = APIRouter(
    prefix="/api/v1/strategy",
    tags=["strategy"],
)


@router.get("/all")
async def get_strategies(
    strategy_service: Annotated[StrategyService, Depends(get_strategy_service)],
) -> StrategyGetResponseDTO:
    strategies = await strategy_service.get_strategies()
    return StrategyGetResponseDTO(strategies=[s for s in strategies])


@router.get("/{strategy_id}")
async def get_strategy(
    strategy_id: Annotated[UUID, Path()],
    strategy_service: Annotated[StrategyService, Depends(get_strategy_service)],
) -> StrategyGetResponseDTO:
    strategy = await strategy_service.get_strategy(strategy_id=strategy_id)
    if not strategy:
        raise HTTPException(status_code=404, detail="Strategy not found")
    return StrategyGetResponseDTO(strategies=[strategy])


@router.post("/create", response_model=StrategyUpsetResponseDTO)
async def create_strategy(
    request: Request,
    strategy_service: Annotated[StrategyService, Depends(get_strategy_service)],
) -> StrategyUpsetResponseDTO:
    try:
        raw = await request.body()
        raw_str = raw.decode("utf-8")

        # اگه کل body یه string escape شده بود، اول parse کن
        try:
            body = json.loads(raw_str)
        except json.JSONDecodeError:
            body = json.loads(json.loads(raw_str))

        # مقدار data رو بررسی کن
        data = body.get("data", {})
        parsed_data = {}
        for key, value in data.items():
            if isinstance(value, str):
                try:
                    parsed_data[key] = json.loads(value)
                except (json.JSONDecodeError, ValueError):
                    parsed_data[key] = value
            else:
                parsed_data[key] = value

        strategy_data = StrategyRowDTO(name=body["name"], data=parsed_data)

    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Invalid request body: {str(e)}")

    await strategy_service.create_strategy(
        strategy_data=Strategy(
            name=strategy_data.name,
            data=strategy_data.data,
        )
    )
    return StrategyUpsetResponseDTO(status="success")


@router.put("/update")
async def update_strategy(
    request: Request,
    strategy_service: Annotated[StrategyService, Depends(get_strategy_service)],
) -> StrategyUpsetResponseDTO:
    try:
        raw = await request.body()
        body = json.loads(raw.decode("utf-8"))

        data = body.get("data", {})
        parsed_data = {}
        for key, value in data.items():
            if isinstance(value, str):
                try:
                    parsed_data[key] = json.loads(value)
                except (json.JSONDecodeError, ValueError):
                    parsed_data[key] = value
            else:
                parsed_data[key] = value

        strategy_data = StrategyUpdateDTO(
            id=body["id"],
            name=body["name"],
            data=parsed_data,
        )

    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Invalid request body: {str(e)}")

    await strategy_service.update_strategy(
        strategy_data=Strategy(
            id=strategy_data.id,
            name=strategy_data.name,
            data=strategy_data.data,
        )
    )
    return StrategyUpsetResponseDTO(status="success")