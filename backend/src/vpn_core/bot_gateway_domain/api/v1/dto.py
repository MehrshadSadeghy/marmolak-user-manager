from pydantic import BaseModel, Field

from vpn_core.billing_domain.domain.payment_method import PaymentMethod
from vpn_core.billing_domain.domain.payment_request import PaymentPurpose, PaymentRequest
from vpn_core.commerce_domain.domain.bot_settings import BotSettings
from vpn_core.commerce_domain.domain.service_type import ServiceType
from vpn_core.subscription_domain.domain.plan import Plan
from vpn_core.subscription_domain.domain.subscription import Subscription
from vpn_core.subscription_domain.domain.user import User


class RegisterUserDTO(BaseModel):
    telegram_id: str
    chat_id: str
    username: str | None = None


class UserResponseDTO(BaseModel):
    user: User
    wallet_balance_toman: int


class ServiceTypeListResponseDTO(BaseModel):
    services: list[ServiceType]


class PlanListResponseDTO(BaseModel):
    plans: list[Plan]


class PurchasePreviewDTO(BaseModel):
    plan: Plan
    wallet_balance_toman: int
    price_toman: int
    sufficient_balance: bool
    shortfall_toman: int


class ServiceDeliveryDTO(BaseModel):
    service_type: str
    subscription_id: int
    delivery_type: str
    content: str
    filename: str | None = None


class PurchaseResultDTO(BaseModel):
    subscription: Subscription
    wallet_balance_toman: int
    paid_from_wallet: bool
    payment_request_id: int | None = None
    delivery: ServiceDeliveryDTO | None = None


class InitiatePaymentDTO(BaseModel):
    telegram_id: str
    purpose: PaymentPurpose
    amount_toman: int = 0
    payment_method_id: int | None = None
    plan_id: int | None = None
    subscription_id: int | None = None
    service_type: str | None = None


class SubmitReceiptDTO(BaseModel):
    telegram_id: str
    receipt_file_id: str
    receipt_message_id: int | None = None


class PaymentRequestResponseDTO(BaseModel):
    payment_request: PaymentRequest


class PaymentMethodListResponseDTO(BaseModel):
    payment_methods: list[PaymentMethod]


class UserServiceItemDTO(BaseModel):
    subscription_id: int
    service_type: str
    plan_name: str | None
    status_label: str
    is_active: bool
    remaining_days: int
    remaining_bytes: int
    remaining_data_label: str
    expire_at: str


class UserServicesResponseDTO(BaseModel):
    services: list[UserServiceItemDTO]


class SupportResponseDTO(BaseModel):
    support_username: str | None
    payment_instructions: str


class WalletResponseDTO(BaseModel):
    user_id: int
    balance_toman: int


class PurchaseRequestDTO(BaseModel):
    telegram_id: str
    plan_id: int


class TopupRequestDTO(BaseModel):
    telegram_id: str
    amount_toman: int = Field(gt=0)


class RenewRequestDTO(BaseModel):
    telegram_id: str
    subscription_id: int
    plan_id: int


class AdminPaymentReviewDTO(BaseModel):
    admin_note: str = ""


class PaymentApprovalResponseDTO(BaseModel):
    payment_request_id: int
    wallet_balance_toman: int
    purchase: PurchaseResultDTO | None = None


class PendingPaymentsResponseDTO(BaseModel):
    payments: list[PaymentRequest]
