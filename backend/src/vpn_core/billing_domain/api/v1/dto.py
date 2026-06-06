from pydantic import BaseModel, Field

from vpn_core.billing_domain.domain.payment_method import PaymentMethod
from vpn_core.billing_domain.domain.payment_request import PaymentRequest
from vpn_core.billing_domain.domain.wallet import Wallet, WalletTransaction


class PaymentMethodResponseDTO(BaseModel):
    payment_method: PaymentMethod


class PaymentMethodListResponseDTO(BaseModel):
    payment_methods: list[PaymentMethod]


class CreatePaymentMethodDTO(BaseModel):
    name: str
    instructions: str
    is_active: bool = True
    sort_order: int = 0

    def to_domain(self) -> PaymentMethod:
        return PaymentMethod(
            name=self.name,
            instructions=self.instructions,
            is_active=self.is_active,
            sort_order=self.sort_order,
        )


class UpdatePaymentMethodDTO(BaseModel):
    name: str | None = None
    instructions: str | None = None
    is_active: bool | None = None
    sort_order: int | None = None


class WalletResponseDTO(BaseModel):
    wallet: Wallet


class WalletTransactionListResponseDTO(BaseModel):
    transactions: list[WalletTransaction]


class CreditWalletDTO(BaseModel):
    user_id: int
    amount_toman: int = Field(gt=0)
    description: str = ""


class PaymentRequestListResponseDTO(BaseModel):
    payment_requests: list[PaymentRequest]
