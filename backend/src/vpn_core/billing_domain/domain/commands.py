from pydantic import BaseModel

from vpn_core.billing_domain.domain.payment_request import PaymentPurpose


class CreditWalletCommand(BaseModel):
    user_id: int
    amount_toman: int
    description: str = ""
    reference_type: str | None = None
    reference_id: int | None = None


class DebitWalletCommand(BaseModel):
    user_id: int
    amount_toman: int
    description: str = ""
    reference_type: str | None = None
    reference_id: int | None = None


class CreatePaymentRequestCommand(BaseModel):
    user_id: int
    purpose: PaymentPurpose
    amount_toman: int
    payment_method_id: int | None = None
    plan_id: int | None = None
    subscription_id: int | None = None
    service_type: str | None = None


class SubmitPaymentReceiptCommand(BaseModel):
    payment_request_id: int
    receipt_file_id: str
    receipt_message_id: int | None = None


class ReviewPaymentRequestCommand(BaseModel):
    payment_request_id: int
    reviewer_telegram_id: str
    approve: bool
    admin_note: str = ""
