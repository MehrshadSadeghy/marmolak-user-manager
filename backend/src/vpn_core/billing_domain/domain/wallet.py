import enum
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class Wallet(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int | None = None
    user_id: int
    balance_toman: int = 0
    created_at: datetime | None = None
    updated_at: datetime | None = None


class WalletTransactionType(str, enum.Enum):
    credit = "credit"
    debit = "debit"


class WalletTransaction(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int | None = None
    wallet_id: int
    user_id: int
    amount_toman: int
    transaction_type: WalletTransactionType
    description: str = ""
    reference_type: str | None = None
    reference_id: int | None = None
    created_at: datetime | None = None
