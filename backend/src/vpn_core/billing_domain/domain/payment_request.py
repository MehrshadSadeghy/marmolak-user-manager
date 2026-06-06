import enum
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class PaymentPurpose(str, enum.Enum):
    purchase = "purchase"
    renewal = "renewal"
    topup = "topup"


class PaymentRequestStatus(str, enum.Enum):
    awaiting_receipt = "awaiting_receipt"
    pending_approval = "pending_approval"
    approved = "approved"
    rejected = "rejected"
    completed = "completed"


class PaymentRequest(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int | None = None
    user_id: int
    payment_method_id: int | None = None
    purpose: PaymentPurpose
    amount_toman: int
    plan_id: int | None = None
    subscription_id: int | None = None
    service_type: str | None = None
    status: PaymentRequestStatus = PaymentRequestStatus.awaiting_receipt
    receipt_file_id: str | None = None
    receipt_message_id: int | None = None
    admin_note: str = ""
    reviewed_by_telegram_id: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
