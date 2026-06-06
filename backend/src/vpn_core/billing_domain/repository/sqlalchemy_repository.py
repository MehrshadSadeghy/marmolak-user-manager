from sqlalchemy.orm import Session

from vpn_core.billing_domain.db_model import PaymentMethod as PaymentMethodORM
from vpn_core.billing_domain.db_model import PaymentRequest as PaymentRequestORM
from vpn_core.billing_domain.db_model import Wallet as WalletORM
from vpn_core.billing_domain.db_model import WalletTransaction as WalletTransactionORM
from vpn_core.billing_domain.domain.payment_method import PaymentMethod
from vpn_core.billing_domain.domain.payment_request import PaymentRequest
from vpn_core.billing_domain.domain.queries import (
    GetPaymentRequestQuery,
    GetWalletQuery,
    ListPaymentRequestsQuery,
)
from vpn_core.billing_domain.domain.wallet import Wallet, WalletTransaction
from vpn_core.billing_domain.repository.base import BillingRepository


class BillingDBRepository(BillingRepository):
    def __init__(self, session: Session):
        self._session = session

    async def get_or_create_wallet(self, user_id: int) -> Wallet:
        row = self._session.query(WalletORM).filter(WalletORM.user_id == user_id).one_or_none()
        if row:
            return Wallet.model_validate(row)
        row = WalletORM(user_id=user_id, balance_toman=0)
        self._session.add(row)
        self._session.commit()
        self._session.refresh(row)
        return Wallet.model_validate(row)

    async def get_wallet(self, query: GetWalletQuery) -> Wallet | None:
        row = self._session.query(WalletORM).filter(WalletORM.user_id == query.user_id).one_or_none()
        if not row:
            return None
        return Wallet.model_validate(row)

    async def update_wallet(self, wallet: Wallet) -> Wallet:
        row = self._session.get(WalletORM, wallet.id)
        if not row:
            raise ValueError("Wallet not found")
        row.balance_toman = wallet.balance_toman
        self._session.add(row)
        self._session.commit()
        self._session.refresh(row)
        return Wallet.model_validate(row)

    async def create_transaction(self, transaction: WalletTransaction) -> WalletTransaction:
        obj = WalletTransactionORM(
            wallet_id=transaction.wallet_id,
            user_id=transaction.user_id,
            amount_toman=transaction.amount_toman,
            transaction_type=transaction.transaction_type,
            description=transaction.description,
            reference_type=transaction.reference_type,
            reference_id=transaction.reference_id,
        )
        self._session.add(obj)
        self._session.commit()
        self._session.refresh(obj)
        return WalletTransaction.model_validate(obj)

    async def list_transactions(self, user_id: int) -> list[WalletTransaction]:
        rows = (
            self._session.query(WalletTransactionORM)
            .filter(WalletTransactionORM.user_id == user_id)
            .order_by(WalletTransactionORM.created_at.desc())
            .all()
        )
        return [WalletTransaction.model_validate(row) for row in rows]

    async def create_payment_method(self, method: PaymentMethod) -> PaymentMethod:
        obj = PaymentMethodORM(
            name=method.name,
            instructions=method.instructions,
            is_active=method.is_active,
            sort_order=method.sort_order,
        )
        self._session.add(obj)
        self._session.commit()
        self._session.refresh(obj)
        return PaymentMethod.model_validate(obj)

    async def update_payment_method(self, method: PaymentMethod) -> PaymentMethod | None:
        obj = self._session.get(PaymentMethodORM, method.id)
        if not obj:
            return None
        obj.name = method.name
        obj.instructions = method.instructions
        obj.is_active = method.is_active
        obj.sort_order = method.sort_order
        self._session.add(obj)
        self._session.commit()
        self._session.refresh(obj)
        return PaymentMethod.model_validate(obj)

    async def delete_payment_method(self, method_id: int) -> bool:
        obj = self._session.get(PaymentMethodORM, method_id)
        if not obj:
            return False
        self._session.delete(obj)
        self._session.commit()
        return True

    async def get_payment_method(self, method_id: int) -> PaymentMethod | None:
        obj = self._session.get(PaymentMethodORM, method_id)
        if not obj:
            return None
        return PaymentMethod.model_validate(obj)

    async def list_payment_methods(self, active_only: bool = False) -> list[PaymentMethod]:
        query = self._session.query(PaymentMethodORM).order_by(PaymentMethodORM.sort_order)
        if active_only:
            query = query.filter(PaymentMethodORM.is_active.is_(True))
        return [PaymentMethod.model_validate(row) for row in query.all()]

    async def create_payment_request(self, request: PaymentRequest) -> PaymentRequest:
        obj = PaymentRequestORM(
            user_id=request.user_id,
            payment_method_id=request.payment_method_id,
            purpose=request.purpose,
            amount_toman=request.amount_toman,
            plan_id=request.plan_id,
            subscription_id=request.subscription_id,
            service_type=request.service_type,
            status=request.status,
            receipt_file_id=request.receipt_file_id,
            receipt_message_id=request.receipt_message_id,
            admin_note=request.admin_note,
            reviewed_by_telegram_id=request.reviewed_by_telegram_id,
        )
        self._session.add(obj)
        self._session.commit()
        self._session.refresh(obj)
        return PaymentRequest.model_validate(obj)

    async def get_payment_request(self, query: GetPaymentRequestQuery) -> PaymentRequest | None:
        obj = self._session.get(PaymentRequestORM, query.payment_request_id)
        if not obj:
            return None
        return PaymentRequest.model_validate(obj)

    async def update_payment_request(self, request: PaymentRequest) -> PaymentRequest | None:
        obj = self._session.get(PaymentRequestORM, request.id)
        if not obj:
            return None
        obj.payment_method_id = request.payment_method_id
        obj.status = request.status
        obj.receipt_file_id = request.receipt_file_id
        obj.receipt_message_id = request.receipt_message_id
        obj.admin_note = request.admin_note
        obj.reviewed_by_telegram_id = request.reviewed_by_telegram_id
        self._session.add(obj)
        self._session.commit()
        self._session.refresh(obj)
        return PaymentRequest.model_validate(obj)

    async def list_payment_requests(self, query: ListPaymentRequestsQuery) -> list[PaymentRequest]:
        db_query = self._session.query(PaymentRequestORM)
        if query.user_id is not None:
            db_query = db_query.filter(PaymentRequestORM.user_id == query.user_id)
        if query.status is not None:
            db_query = db_query.filter(PaymentRequestORM.status == query.status)
        rows = db_query.order_by(PaymentRequestORM.created_at.desc()).all()
        return [PaymentRequest.model_validate(row) for row in rows]
