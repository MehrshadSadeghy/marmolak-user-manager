from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Query

from vpn_core.billing_domain.api.v1.dependency import BillingServiceDep
from vpn_core.billing_domain.api.v1.dto import (
    CreatePaymentMethodDTO,
    CreditWalletDTO,
    PaymentMethodListResponseDTO,
    PaymentMethodResponseDTO,
    PaymentRequestListResponseDTO,
    UpdatePaymentMethodDTO,
    WalletResponseDTO,
    WalletTransactionListResponseDTO,
)
from vpn_core.billing_domain.domain.commands import CreditWalletCommand
from vpn_core.billing_domain.domain.queries import ListPaymentRequestsQuery
from vpn_core.common.auth.bot_api_key import verify_admin_telegram_id, verify_bot_api_key

router = APIRouter(
    prefix="/api/v1/admin/billing",
    tags=["admin-billing"],
    dependencies=[Depends(verify_bot_api_key), Depends(verify_admin_telegram_id)],
)


@router.get("/payment-methods", response_model=PaymentMethodListResponseDTO)
async def list_payment_methods(service: BillingServiceDep) -> PaymentMethodListResponseDTO:
    return PaymentMethodListResponseDTO(payment_methods=await service.list_payment_methods())


@router.post("/payment-methods", response_model=PaymentMethodResponseDTO)
async def create_payment_method(
    body: CreatePaymentMethodDTO,
    service: BillingServiceDep,
) -> PaymentMethodResponseDTO:
    created = await service.create_payment_method(body.to_domain())
    return PaymentMethodResponseDTO(payment_method=created)


@router.patch("/payment-methods/{method_id}", response_model=PaymentMethodResponseDTO)
async def update_payment_method(
    method_id: Annotated[int, Path()],
    body: UpdatePaymentMethodDTO,
    service: BillingServiceDep,
) -> PaymentMethodResponseDTO:
    existing = await service.get_payment_method(method_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Payment method not found")
    if body.name is not None:
        existing.name = body.name
    if body.instructions is not None:
        existing.instructions = body.instructions
    if body.is_active is not None:
        existing.is_active = body.is_active
    if body.sort_order is not None:
        existing.sort_order = body.sort_order
    updated = await service.update_payment_method(existing)
    if not updated:
        raise HTTPException(status_code=404, detail="Payment method not found")
    return PaymentMethodResponseDTO(payment_method=updated)


@router.delete("/payment-methods/{method_id}")
async def delete_payment_method(
    method_id: Annotated[int, Path()],
    service: BillingServiceDep,
) -> dict:
    if not await service.delete_payment_method(method_id):
        raise HTTPException(status_code=404, detail="Payment method not found")
    return {"deleted": True}


@router.get("/wallets/{user_id}", response_model=WalletResponseDTO)
async def get_wallet(user_id: Annotated[int, Path()], service: BillingServiceDep) -> WalletResponseDTO:
    wallet = await service.get_wallet(user_id)
    return WalletResponseDTO(wallet=wallet)


@router.post("/wallets/credit", response_model=WalletResponseDTO)
async def credit_wallet(body: CreditWalletDTO, service: BillingServiceDep) -> WalletResponseDTO:
    wallet = await service.credit_wallet(
        CreditWalletCommand(
            user_id=body.user_id,
            amount_toman=body.amount_toman,
            description=body.description,
            reference_type="admin",
        )
    )
    return WalletResponseDTO(wallet=wallet)


@router.get("/wallets/{user_id}/transactions", response_model=WalletTransactionListResponseDTO)
async def list_wallet_transactions(
    user_id: Annotated[int, Path()],
    service: BillingServiceDep,
) -> WalletTransactionListResponseDTO:
    return WalletTransactionListResponseDTO(transactions=await service.list_transactions(user_id))


@router.get("/payment-requests", response_model=PaymentRequestListResponseDTO)
async def list_payment_requests(
    service: BillingServiceDep,
    status: Annotated[str | None, Query()] = None,
    user_id: Annotated[int | None, Query()] = None,
) -> PaymentRequestListResponseDTO:
    requests = await service.list_payment_requests(
        ListPaymentRequestsQuery(user_id=user_id, status=status)
    )
    return PaymentRequestListResponseDTO(payment_requests=requests)
