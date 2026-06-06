from abc import ABC, abstractmethod

from vpn_core.billing_domain.domain.commands import (
    CreatePaymentRequestCommand,
    CreditWalletCommand,
    DebitWalletCommand,
    ReviewPaymentRequestCommand,
    SubmitPaymentReceiptCommand,
)
from vpn_core.billing_domain.domain.payment_method import PaymentMethod
from vpn_core.billing_domain.domain.payment_request import PaymentRequest
from vpn_core.billing_domain.domain.queries import (
    GetPaymentRequestQuery,
    GetWalletQuery,
    ListPaymentRequestsQuery,
)
from vpn_core.billing_domain.domain.wallet import Wallet, WalletTransaction


class BillingRepository(ABC):
    @abstractmethod
    async def get_or_create_wallet(self, user_id: int) -> Wallet:
        pass

    @abstractmethod
    async def get_wallet(self, query: GetWalletQuery) -> Wallet | None:
        pass

    @abstractmethod
    async def update_wallet(self, wallet: Wallet) -> Wallet:
        pass

    @abstractmethod
    async def create_transaction(self, transaction: WalletTransaction) -> WalletTransaction:
        pass

    @abstractmethod
    async def list_transactions(self, user_id: int) -> list[WalletTransaction]:
        pass

    @abstractmethod
    async def create_payment_method(self, method: PaymentMethod) -> PaymentMethod:
        pass

    @abstractmethod
    async def update_payment_method(self, method: PaymentMethod) -> PaymentMethod | None:
        pass

    @abstractmethod
    async def delete_payment_method(self, method_id: int) -> bool:
        pass

    @abstractmethod
    async def get_payment_method(self, method_id: int) -> PaymentMethod | None:
        pass

    @abstractmethod
    async def list_payment_methods(self, active_only: bool = False) -> list[PaymentMethod]:
        pass

    @abstractmethod
    async def create_payment_request(self, request: PaymentRequest) -> PaymentRequest:
        pass

    @abstractmethod
    async def get_payment_request(self, query: GetPaymentRequestQuery) -> PaymentRequest | None:
        pass

    @abstractmethod
    async def update_payment_request(self, request: PaymentRequest) -> PaymentRequest | None:
        pass

    @abstractmethod
    async def list_payment_requests(self, query: ListPaymentRequestsQuery) -> list[PaymentRequest]:
        pass
