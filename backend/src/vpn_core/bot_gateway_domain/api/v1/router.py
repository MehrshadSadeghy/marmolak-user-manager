from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path

from vpn_core.bot_gateway_domain.api.v1.dependency import BotGatewayServiceDep
from vpn_core.bot_gateway_domain.api.v1.dto import (
    AdminPaymentReviewDTO,
    InitiatePaymentDTO,
    PaymentApprovalResponseDTO,
    PaymentMethodListResponseDTO,
    PaymentRequestResponseDTO,
    PendingPaymentsResponseDTO,
    PlanListResponseDTO,
    PurchasePreviewDTO,
    PurchaseRequestDTO,
    PurchaseResultDTO,
    RegisterUserDTO,
    RenewRequestDTO,
    ServiceDeliveryDTO,
    ServiceTypeListResponseDTO,
    SubmitReceiptDTO,
    SupportResponseDTO,
    TopupRequestDTO,
    UserResponseDTO,
    UserServicesResponseDTO,
    WalletResponseDTO,
)
from vpn_core.bot_gateway_domain.service import BotGatewayService
from vpn_core.common.auth.bot_api_key import verify_admin_telegram_id, verify_bot_api_key

router = APIRouter(prefix="/api/v1/bot", tags=["bot"], dependencies=[Depends(verify_bot_api_key)])


def _purchase_result_dto(result) -> PurchaseResultDTO:
    delivery = None
    if result.delivery:
        delivery = ServiceDeliveryDTO(
            service_type=result.delivery.service_type,
            subscription_id=result.delivery.subscription_id,
            delivery_type=result.delivery.delivery_type,
            content=result.delivery.content,
            filename=result.delivery.filename,
        )
    return PurchaseResultDTO(
        subscription=result.subscription,
        wallet_balance_toman=result.wallet_balance_toman,
        paid_from_wallet=result.paid_from_wallet,
        payment_request_id=result.payment_request_id,
        delivery=delivery,
    )


@router.post("/users/register", response_model=UserResponseDTO)
async def register_user(body: RegisterUserDTO, service: BotGatewayServiceDep) -> UserResponseDTO:
    user = await service.register_user(
        telegram_id=body.telegram_id,
        chat_id=body.chat_id,
        username=body.username,
    )
    balance = await service.get_wallet_balance(user.id)
    return UserResponseDTO(user=user, wallet_balance_toman=balance)


@router.get("/users/by-telegram/{telegram_id}", response_model=UserResponseDTO)
async def get_user_by_telegram(
    telegram_id: Annotated[str, Path()],
    service: BotGatewayServiceDep,
) -> UserResponseDTO:
    user = await service.get_user_by_telegram(telegram_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    balance = await service.get_wallet_balance(user.id)
    return UserResponseDTO(user=user, wallet_balance_toman=balance)


@router.get("/services", response_model=ServiceTypeListResponseDTO)
async def list_services(service: BotGatewayServiceDep) -> ServiceTypeListResponseDTO:
    return ServiceTypeListResponseDTO(services=await service.list_enabled_services())


@router.get("/services/{service_type}/plans", response_model=PlanListResponseDTO)
async def list_service_plans(
    service_type: Annotated[str, Path()],
    gateway: BotGatewayServiceDep,
) -> PlanListResponseDTO:
    return PlanListResponseDTO(plans=await gateway.list_plans(service_type))


@router.get("/users/{telegram_id}/wallet", response_model=WalletResponseDTO)
async def get_wallet(
    telegram_id: Annotated[str, Path()],
    service: BotGatewayServiceDep,
) -> WalletResponseDTO:
    user = await service.get_user_by_telegram(telegram_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    balance = await service.get_wallet_balance(user.id)
    return WalletResponseDTO(user_id=user.id, balance_toman=balance)


@router.post("/purchase/preview", response_model=PurchasePreviewDTO)
async def preview_purchase(body: PurchaseRequestDTO, service: BotGatewayServiceDep) -> PurchasePreviewDTO:
    user = await service.get_user_by_telegram(body.telegram_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    preview = await service.preview_purchase(user.id, body.plan_id)
    return PurchasePreviewDTO(
        plan=preview.plan,
        wallet_balance_toman=preview.wallet_balance_toman,
        price_toman=preview.price_toman,
        sufficient_balance=preview.sufficient_balance,
        shortfall_toman=preview.shortfall_toman,
    )


@router.post("/purchase", response_model=PurchaseResultDTO)
async def purchase(body: PurchaseRequestDTO, service: BotGatewayServiceDep) -> PurchaseResultDTO:
    user = await service.get_user_by_telegram(body.telegram_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    result = await service.purchase_with_wallet(user.id, body.plan_id)
    return _purchase_result_dto(result)


@router.post("/renew", response_model=PurchaseResultDTO)
async def renew(body: RenewRequestDTO, service: BotGatewayServiceDep) -> PurchaseResultDTO:
    user = await service.get_user_by_telegram(body.telegram_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    result = await service.renew_with_wallet(user.id, body.subscription_id, body.plan_id)
    return _purchase_result_dto(result)


@router.post("/payments/initiate", response_model=PaymentRequestResponseDTO)
async def initiate_payment(body: InitiatePaymentDTO, service: BotGatewayServiceDep) -> PaymentRequestResponseDTO:
    user = await service.get_user_by_telegram(body.telegram_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    request = await service.initiate_payment(
        user_id=user.id,
        purpose=body.purpose,
        amount_toman=body.amount_toman,
        payment_method_id=body.payment_method_id,
        plan_id=body.plan_id,
        subscription_id=body.subscription_id,
        service_type=body.service_type,
    )
    return PaymentRequestResponseDTO(payment_request=request)


@router.post("/payments/{payment_request_id}/receipt", response_model=PaymentRequestResponseDTO)
async def submit_receipt(
    payment_request_id: Annotated[int, Path()],
    body: SubmitReceiptDTO,
    service: BotGatewayServiceDep,
) -> PaymentRequestResponseDTO:
    user = await service.get_user_by_telegram(body.telegram_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    request = await service.submit_payment_receipt(
        payment_request_id,
        body.receipt_file_id,
        body.receipt_message_id,
    )
    if request.user_id != user.id:
        raise HTTPException(status_code=403, detail="Payment request does not belong to user")
    return PaymentRequestResponseDTO(payment_request=request)


@router.get("/payment-methods", response_model=PaymentMethodListResponseDTO)
async def list_payment_methods(service: BotGatewayServiceDep) -> PaymentMethodListResponseDTO:
    return PaymentMethodListResponseDTO(payment_methods=await service.list_payment_methods())


@router.get("/users/{telegram_id}/services", response_model=UserServicesResponseDTO)
async def list_user_services(
    telegram_id: Annotated[str, Path()],
    service: BotGatewayServiceDep,
) -> UserServicesResponseDTO:
    user = await service.get_user_by_telegram(telegram_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    summaries = await service.list_user_services(user.id)
    items = []
    for item in summaries:
        items.append(
            {
                "subscription_id": item.subscription.id,
                "service_type": item.subscription.service_type,
                "plan_name": item.plan.name if item.plan else None,
                "status_label": item.status_label,
                "is_active": item.is_active,
                "remaining_days": item.remaining_days,
                "remaining_bytes": item.remaining_bytes,
                "remaining_data_label": BotGatewayService.format_bytes(item.remaining_bytes),
                "expire_at": item.subscription.expire_at.isoformat(),
            }
        )
    return UserServicesResponseDTO(services=items)


@router.get("/support", response_model=SupportResponseDTO)
async def get_support(service: BotGatewayServiceDep) -> SupportResponseDTO:
    settings = await service.get_support_info()
    return SupportResponseDTO(
        support_username=settings.support_username,
        payment_instructions=settings.payment_instructions,
    )


@router.post("/wallet/topup/initiate", response_model=PaymentRequestResponseDTO)
async def initiate_topup(body: TopupRequestDTO, service: BotGatewayServiceDep) -> PaymentRequestResponseDTO:
    from vpn_core.billing_domain.domain.payment_request import PaymentPurpose

    user = await service.get_user_by_telegram(body.telegram_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    request = await service.initiate_payment(
        user_id=user.id,
        purpose=PaymentPurpose.topup,
        amount_toman=body.amount_toman,
    )
    return PaymentRequestResponseDTO(payment_request=request)



@router.get("/users/{telegram_id}/payments/active", response_model=PaymentRequestResponseDTO)
async def get_active_payment(
    telegram_id: Annotated[str, Path()],
    service: BotGatewayServiceDep,
) -> PaymentRequestResponseDTO:
    from vpn_core.billing_domain.domain.payment_request import PaymentRequestStatus
    from vpn_core.billing_domain.domain.queries import ListPaymentRequestsQuery

    user = await service.get_user_by_telegram(telegram_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    request = await service.get_active_payment_request(user.id)
    if not request:
        raise HTTPException(status_code=404, detail="No active payment request")
    return PaymentRequestResponseDTO(payment_request=request)
    raise HTTPException(status_code=404, detail="No active payment request")

admin_router = APIRouter(
    prefix="/api/v1/admin/bot",
    tags=["admin-bot"],
    dependencies=[Depends(verify_bot_api_key), Depends(verify_admin_telegram_id)],
)


@admin_router.get("/payments/pending", response_model=PendingPaymentsResponseDTO)
async def list_pending_payments(service: BotGatewayServiceDep) -> PendingPaymentsResponseDTO:
    return PendingPaymentsResponseDTO(payments=await service.list_pending_payments())


@admin_router.post("/payments/{payment_request_id}/approve", response_model=PaymentApprovalResponseDTO)
async def approve_payment(
    payment_request_id: Annotated[int, Path()],
    body: AdminPaymentReviewDTO,
    service: BotGatewayServiceDep,
    admin_telegram_id: Annotated[str, Depends(verify_admin_telegram_id)],
) -> PaymentApprovalResponseDTO:
    result = await service.approve_payment(payment_request_id, admin_telegram_id, body.admin_note)
    purchase = _purchase_result_dto(result.purchase) if result.purchase else None
    return PaymentApprovalResponseDTO(
        payment_request_id=result.payment_request_id,
        wallet_balance_toman=result.wallet_balance_toman,
        purchase=purchase,
    )


@admin_router.post("/payments/{payment_request_id}/reject", response_model=PaymentRequestResponseDTO)
async def reject_payment(
    payment_request_id: Annotated[int, Path()],
    body: AdminPaymentReviewDTO,
    service: BotGatewayServiceDep,
    admin_telegram_id: Annotated[str, Depends(verify_admin_telegram_id)],
) -> PaymentRequestResponseDTO:
    request = await service.reject_payment(payment_request_id, admin_telegram_id, body.admin_note)
    return PaymentRequestResponseDTO(payment_request=request)
