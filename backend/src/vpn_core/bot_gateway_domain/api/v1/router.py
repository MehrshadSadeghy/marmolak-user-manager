from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Query

from vpn_core.bot_gateway_domain.api.v1.dependency import BotGatewayServiceDep
from vpn_core.bot_gateway_domain.api.v1.pasarguard_dependency import PasarguardPanelServiceDep
from vpn_core.bot_gateway_domain.api.v1.dto import (
    AdminPaymentReviewDTO,
    AdminOpenVpnServerListResponseDTO,
    AdminOpenVpnServerSummaryDTO,
    AdminV2RayServerListResponseDTO,
    AdminV2RayServerSummaryDTO,
    OpenVpnServerListResponseDTO,
    OpenVpnServerSummaryDTO,
    V2RayServerListResponseDTO,
    V2RayServerSummaryDTO,
    ApplyOpenVpnEndpointDTO,
    ApplyOpenVpnEndpointResponseDTO,
    ApplyV2RayInboundConfigResponseDTO,
    PatchV2RayInboundConfigDTO,
    V2RayInboundConfigDTO,
    V2RayInboundConfigResponseDTO,
    ConfigTrafficLookupDTO,
    ConfigTrafficStatusDTO,
    InitiatePaymentDTO,
    PaymentApprovalResponseDTO,
    PaymentMethodListResponseDTO,
    PaymentRequestResponseDTO,
    PendingPaymentsResponseDTO,
    PasarguardConnectDTO,
    PasarguardConnectionResponseDTO,
    PasarguardPanelAppDTO,
    PasarguardPanelLinkDTO,
    PasarguardPanelSettingsDTO,
    PasarguardSubscriptionInfoDTO,
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
    UserAccessStatusDTO,
    WalletResponseDTO,
    ClientSubscriptionUrlResponseDTO,
)
from vpn_core.bot_gateway_domain.service import BotGatewayService
from vpn_core.common.auth.bot_api_key import verify_admin_telegram_id, verify_bot_api_key

router = APIRouter(prefix="/api/v1/bot", tags=["bot"], dependencies=[Depends(verify_bot_api_key)])


def _service_delivery_dto(delivery) -> ServiceDeliveryDTO:
    password = delivery.password if delivery.includes_password else None
    return ServiceDeliveryDTO(
        service_type=delivery.service_type,
        subscription_id=delivery.subscription_id,
        delivery_type=delivery.delivery_type,
        content=delivery.content,
        filename=delivery.filename,
        config_id=delivery.config_id,
        username=delivery.username,
        password=password,
        includes_password=delivery.includes_password,
        server_host=delivery.server_host,
        server_port=delivery.server_port,
        server_proto=delivery.server_proto,
        expire_at=delivery.expire_at,
        traffic_limit_bytes=delivery.traffic_limit_bytes,
        traffic_used_bytes=delivery.traffic_used_bytes,
        remaining_bytes=delivery.remaining_bytes,
        remaining_days=delivery.remaining_days,
        auth_mode=delivery.auth_mode,
    )


def _purchase_result_dto(result) -> PurchaseResultDTO:
    delivery = _service_delivery_dto(result.delivery) if result.delivery else None
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
    telegram_id: Annotated[str | None, Query()] = None,
) -> PlanListResponseDTO:
    user_id = None
    if telegram_id:
        user = await gateway.get_user_by_telegram(telegram_id)
        if user:
            user_id = user.id
    return PlanListResponseDTO(plans=await gateway.list_plans(service_type, user_id=user_id))


@router.get("/users/{telegram_id}/access", response_model=UserAccessStatusDTO)
async def get_user_access(
    telegram_id: Annotated[str, Path()],
    service: BotGatewayServiceDep,
) -> UserAccessStatusDTO:
    user = await service.get_user_by_telegram(telegram_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    status = await service.get_user_access_status(user.id)
    return UserAccessStatusDTO(**status)


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
    preview = await service.preview_purchase(user.id, body.plan_id, server_id=body.server_id)
    return PurchasePreviewDTO(
        plan=preview.plan,
        wallet_balance_toman=preview.wallet_balance_toman,
        price_toman=preview.price_toman,
        sufficient_balance=preview.sufficient_balance,
        shortfall_toman=preview.shortfall_toman,
        original_price_toman=preview.original_price_toman,
        discount_percent=preview.discount_percent,
    )


@router.post("/purchase", response_model=PurchaseResultDTO)
async def purchase(body: PurchaseRequestDTO, service: BotGatewayServiceDep) -> PurchaseResultDTO:
    user = await service.get_user_by_telegram(body.telegram_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    result = await service.purchase_with_wallet(user.id, body.plan_id, server_id=body.server_id)
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
    subscription_url = None
    if any(item.subscription.service_type == "v2ray" and item.is_active for item in summaries):
        try:
            subscription_url = await service.get_client_subscription_url(user.id)
        except HTTPException:
            subscription_url = None
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
                "config_ids": item.config_ids,
                "migratable_config_ids": item.migratable_config_ids,
                "finalizable_config_ids": item.finalizable_config_ids,
                "password_config_ids": item.password_config_ids,
            }
        )
    return UserServicesResponseDTO(services=items, subscription_url=subscription_url)


@router.get(
    "/users/{telegram_id}/subscription-url",
    response_model=ClientSubscriptionUrlResponseDTO,
)
async def get_client_subscription_url(
    telegram_id: Annotated[str, Path()],
    service: BotGatewayServiceDep,
) -> ClientSubscriptionUrlResponseDTO:
    user = await service.get_user_by_telegram(telegram_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    subscription_url = await service.get_client_subscription_url(user.id)
    return ClientSubscriptionUrlResponseDTO(subscription_url=subscription_url)


@router.get(
    "/users/{telegram_id}/subscriptions/{subscription_id}/delivery",
    response_model=ServiceDeliveryDTO,
)
async def get_subscription_delivery(
    telegram_id: Annotated[str, Path()],
    subscription_id: Annotated[int, Path()],
    service: BotGatewayServiceDep,
) -> ServiceDeliveryDTO:
    user = await service.get_user_by_telegram(telegram_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    delivery = await service.get_subscription_delivery(user.id, subscription_id)
    return _service_delivery_dto(delivery)


@router.get(
    "/users/{telegram_id}/openvpn/configs/{config_id}/delivery",
    response_model=ServiceDeliveryDTO,
)
async def get_openvpn_config_delivery(
    telegram_id: Annotated[str, Path()],
    config_id: Annotated[str, Path()],
    service: BotGatewayServiceDep,
) -> ServiceDeliveryDTO:
    user = await service.get_user_by_telegram(telegram_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    delivery = await service.get_openvpn_config_delivery(user.id, config_id)
    return _service_delivery_dto(delivery)


@router.get(
    "/users/{telegram_id}/openvpn/configs/{config_id}/credentials",
    response_model=ServiceDeliveryDTO,
)
async def get_openvpn_credential_view(
    telegram_id: Annotated[str, Path()],
    config_id: Annotated[str, Path()],
    service: BotGatewayServiceDep,
) -> ServiceDeliveryDTO:
    user = await service.get_user_by_telegram(telegram_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    delivery = await service.get_openvpn_credential_view(user.id, config_id)
    return _service_delivery_dto(delivery)


@router.post(
    "/users/{telegram_id}/openvpn/configs/{config_id}/credentials/rotate",
    response_model=ServiceDeliveryDTO,
)
async def rotate_openvpn_credentials(
    telegram_id: Annotated[str, Path()],
    config_id: Annotated[str, Path()],
    service: BotGatewayServiceDep,
) -> ServiceDeliveryDTO:
    user = await service.get_user_by_telegram(telegram_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    delivery = await service.rotate_openvpn_credentials(user.id, config_id)
    return _service_delivery_dto(delivery)


@router.post(
    "/users/{telegram_id}/openvpn/configs/{config_id}/credentials/migrate",
    response_model=ServiceDeliveryDTO,
)
async def migrate_openvpn_credentials(
    telegram_id: Annotated[str, Path()],
    config_id: Annotated[str, Path()],
    service: BotGatewayServiceDep,
) -> ServiceDeliveryDTO:
    user = await service.get_user_by_telegram(telegram_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    delivery = await service.migrate_openvpn_credentials(user.id, config_id)
    return _service_delivery_dto(delivery)


@router.post(
    "/users/{telegram_id}/openvpn/configs/{config_id}/credentials/finalize",
    response_model=ServiceDeliveryDTO,
)
async def finalize_openvpn_auth_migration(
    telegram_id: Annotated[str, Path()],
    config_id: Annotated[str, Path()],
    service: BotGatewayServiceDep,
) -> ServiceDeliveryDTO:
    user = await service.get_user_by_telegram(telegram_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    delivery = await service.finalize_openvpn_auth_migration(user.id, config_id)
    return _service_delivery_dto(delivery)


@router.post("/openvpn/config-traffic", response_model=ConfigTrafficStatusDTO)
async def get_openvpn_config_traffic(
    body: ConfigTrafficLookupDTO,
    service: BotGatewayServiceDep,
) -> ConfigTrafficStatusDTO:
    user = await service.get_user_by_telegram(body.telegram_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    summary = await service.get_openvpn_config_traffic(user.id, body.config_id)
    return ConfigTrafficStatusDTO(
        config_id=summary.config_id,
        subscription_id=summary.subscription_id,
        status_label=summary.status_label,
        is_active=summary.is_active,
        remaining_days=summary.remaining_days,
        traffic_used_bytes=summary.traffic_used_bytes,
        traffic_limit_bytes=summary.traffic_limit_bytes,
        used_data_label=BotGatewayService.format_bytes(summary.traffic_used_bytes),
        limit_data_label=BotGatewayService.format_bytes(summary.traffic_limit_bytes),
        remaining_bytes=summary.remaining_bytes,
        remaining_data_label=BotGatewayService.format_bytes(summary.remaining_bytes),
        expire_at=summary.expire_at.isoformat(),
    )


def _pasarguard_connection_dto(payload: dict) -> PasarguardConnectionResponseDTO:
    link = payload["link"]
    info = payload.get("info")
    return PasarguardConnectionResponseDTO(
        link=PasarguardPanelLinkDTO(
            panel_username=link.panel_username,
            subscription_url=link.subscription_url,
            subscription_token=link.subscription_token,
        ),
        info=PasarguardSubscriptionInfoDTO(**info) if info else None,
        apps=[PasarguardPanelAppDTO(**app) for app in payload.get("apps") or []],
        error=payload.get("error"),
    )


@router.get("/pasarguard/panel", response_model=PasarguardPanelSettingsDTO)
async def get_pasarguard_panel_settings(
    service: PasarguardPanelServiceDep,
) -> PasarguardPanelSettingsDTO:
    settings = service.get_panel_settings()
    return PasarguardPanelSettingsDTO(**settings)


@router.post("/pasarguard/connect", response_model=PasarguardConnectionResponseDTO)
async def connect_pasarguard_panel(
    body: PasarguardConnectDTO,
    gateway: BotGatewayServiceDep,
    panel_service: PasarguardPanelServiceDep,
) -> PasarguardConnectionResponseDTO:
    user = await gateway.get_user_by_telegram(body.telegram_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    result = await panel_service.connect_user_panel(user.id, body.subscription_input)
    return _pasarguard_connection_dto(result)


@router.get("/pasarguard/users/{telegram_id}/connection", response_model=PasarguardConnectionResponseDTO)
async def get_pasarguard_connection(
    telegram_id: Annotated[str, Path()],
    gateway: BotGatewayServiceDep,
    panel_service: PasarguardPanelServiceDep,
) -> PasarguardConnectionResponseDTO:
    user = await gateway.get_user_by_telegram(telegram_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    result = await panel_service.get_user_connection(user.id)
    if not result:
        raise HTTPException(status_code=404, detail="PasarGuard panel is not connected")
    return _pasarguard_connection_dto(result)


@router.get(
    "/pasarguard/users/{telegram_id}/openvpn-delivery",
    response_model=ServiceDeliveryDTO,
)
async def get_pasarguard_openvpn_delivery(
    telegram_id: Annotated[str, Path()],
    gateway: BotGatewayServiceDep,
) -> ServiceDeliveryDTO:
    user = await gateway.get_user_by_telegram(telegram_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    delivery = await gateway.get_first_openvpn_delivery(user.id)
    return _service_delivery_dto(delivery)


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
        user_telegram_id=result.user_telegram_id,
        user_chat_id=result.user_chat_id,
        purpose=result.purpose,
    )


def _openvpn_server_summary_dto(item: dict) -> OpenVpnServerSummaryDTO:
    server = item["server"]
    return OpenVpnServerSummaryDTO(
        id=server.id,
        name=server.name,
        vpn_host=server.openvpn.vpn_host or server.connection.host,
        vpn_port=server.openvpn.vpn_port,
        vpn_proto=server.openvpn.vpn_proto,
        status=server.status.value,
        max_users=item["max_users"],
        current_users=item["current_users"],
        is_full=item["is_full"],
        remaining_slots=item["remaining_slots"],
    )


@router.get("/openvpn/servers", response_model=OpenVpnServerListResponseDTO)
async def list_openvpn_servers_for_purchase(
    service: BotGatewayServiceDep,
) -> OpenVpnServerListResponseDTO:
    servers = await service.list_openvpn_servers()
    return OpenVpnServerListResponseDTO(
        servers=[_openvpn_server_summary_dto(item) for item in servers]
    )


def _v2ray_server_summary_dto(item: dict) -> V2RayServerSummaryDTO:
    server = item["server"]
    return V2RayServerSummaryDTO(
        id=server.id,
        name=server.name,
        vpn_host=server.v2ray.vpn_host or server.connection.host,
        vpn_port=server.v2ray.vpn_port,
        ws_path=server.v2ray.ws_path,
        network=server.v2ray.network,
        security=server.v2ray.security,
        status=server.status.value,
        max_users=item["max_users"],
        current_users=item["current_users"],
        is_full=item["is_full"],
        remaining_slots=item["remaining_slots"],
    )


@router.get("/v2ray/servers", response_model=V2RayServerListResponseDTO)
async def list_v2ray_servers_for_purchase(
    service: BotGatewayServiceDep,
) -> V2RayServerListResponseDTO:
    servers = await service.list_v2ray_servers()
    return V2RayServerListResponseDTO(
        servers=[_v2ray_server_summary_dto(item) for item in servers]
    )


@router.get(
    "/users/{telegram_id}/v2ray/configs/{config_id}/delivery",
    response_model=ServiceDeliveryDTO,
)
async def get_v2ray_config_delivery(
    telegram_id: Annotated[str, Path()],
    config_id: Annotated[str, Path()],
    service: BotGatewayServiceDep,
) -> ServiceDeliveryDTO:
    user = await service.get_user_by_telegram(telegram_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    delivery = await service.get_v2ray_config_delivery(user.id, config_id)
    return _service_delivery_dto(delivery)


@admin_router.get("/servers/openvpn", response_model=AdminOpenVpnServerListResponseDTO)
async def list_openvpn_servers(service: BotGatewayServiceDep) -> AdminOpenVpnServerListResponseDTO:
    servers = await service.list_openvpn_servers()
    return AdminOpenVpnServerListResponseDTO(
        servers=[
            AdminOpenVpnServerSummaryDTO(**_openvpn_server_summary_dto(item).model_dump())
            for item in servers
        ]
    )


@admin_router.get("/servers/v2ray", response_model=AdminV2RayServerListResponseDTO)
async def list_v2ray_servers_admin(service: BotGatewayServiceDep) -> AdminV2RayServerListResponseDTO:
    servers = await service.list_v2ray_servers()
    return AdminV2RayServerListResponseDTO(
        servers=[
            AdminV2RayServerSummaryDTO(**_v2ray_server_summary_dto(item).model_dump())
            for item in servers
        ]
    )


@admin_router.post(
    "/servers/{server_id}/openvpn-endpoint",
    response_model=ApplyOpenVpnEndpointResponseDTO,
)
async def apply_openvpn_endpoint(
    server_id: Annotated[int, Path()],
    body: ApplyOpenVpnEndpointDTO,
    service: BotGatewayServiceDep,
) -> ApplyOpenVpnEndpointResponseDTO:
    proto = body.proto.lower()
    if proto not in ("udp", "tcp"):
        raise HTTPException(status_code=400, detail="proto must be udp or tcp")
    result = await service.apply_openvpn_endpoint(server_id, body.port, proto)
    running = result.get("openvpn_running", False)
    message = (
        f"OpenVPN endpoint updated to {proto.upper()}/{result['port']}."
        if running
        else f"Settings saved but OpenVPN service is not running on {proto.upper()}/{result['port']}."
    )
    return ApplyOpenVpnEndpointResponseDTO(
        server_id=result["server_id"],
        server_name=result["server_name"],
        port=result["port"],
        proto=result["proto"],
        previous_port=result["previous_port"],
        previous_proto=result["previous_proto"],
        openvpn_running=running,
        server_conf_updated=result.get("server_conf_updated", False),
        firewall_rule_added=result.get("firewall_rule_added", False),
        env_file_updated=result.get("env_file_updated", False),
        message=message,
    )


def _v2ray_inbound_config_dto(data: dict) -> V2RayInboundConfigDTO:
    return V2RayInboundConfigDTO(
        inbound_tag=data["inbound_tag"],
        listen=data["listen"],
        port=data["port"],
        protocol=data["protocol"],
        network=data["network"],
        security=data["security"],
        server_host=data["server_host"],
        ws_path=data.get("ws_path"),
        grpc_service_name=data.get("grpc_service_name"),
        tcp_header_type=data.get("tcp_header_type"),
        sni=data.get("sni"),
        fingerprint=data.get("fingerprint"),
        enable_udp=data.get("enable_udp", False),
        shadowsocks_method=data.get("shadowsocks_method", "aes-256-gcm"),
    )


@admin_router.get(
    "/servers/{server_id}/v2ray/inbound-config",
    response_model=V2RayInboundConfigResponseDTO,
)
async def get_v2ray_inbound_config_admin(
    server_id: Annotated[int, Path()],
    service: BotGatewayServiceDep,
) -> V2RayInboundConfigResponseDTO:
    result = await service.get_v2ray_inbound_config(server_id)
    return V2RayInboundConfigResponseDTO(
        server_id=result["server_id"],
        server_name=result["server_name"],
        **_v2ray_inbound_config_dto(result).model_dump(),
    )


@admin_router.patch(
    "/servers/{server_id}/v2ray/inbound-config",
    response_model=ApplyV2RayInboundConfigResponseDTO,
)
async def patch_v2ray_inbound_config_admin(
    server_id: Annotated[int, Path()],
    body: PatchV2RayInboundConfigDTO,
    service: BotGatewayServiceDep,
) -> ApplyV2RayInboundConfigResponseDTO:
    if not body.model_dump(exclude_unset=True):
        raise HTTPException(status_code=400, detail="At least one field is required")
    result = await service.patch_v2ray_inbound_config(
        server_id,
        body.model_dump(exclude_unset=True),
    )
    previous = result.get("previous")
    message = (
        f"V2Ray inbound updated to {result.get('protocol')} "
        f"{result.get('network')}+{result.get('security')} on port {result.get('port')}."
    )
    return ApplyV2RayInboundConfigResponseDTO(
        server_id=result["server_id"],
        server_name=result["server_name"],
        inbound_tag=result.get("inbound_tag", ""),
        listen=result.get("listen", ""),
        port=int(result.get("port") or 0),
        protocol=str(result.get("protocol") or ""),
        network=str(result.get("network") or ""),
        security=str(result.get("security") or ""),
        server_host=str(result.get("server_host") or ""),
        xray_config_updated=bool(result.get("xray_config_updated")),
        env_file_updated=bool(result.get("env_file_updated")),
        xray_reloaded=bool(result.get("xray_reloaded")),
        previous=_v2ray_inbound_config_dto(previous) if previous else None,
        message=message,
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
