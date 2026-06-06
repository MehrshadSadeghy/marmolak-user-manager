from datetime import UTC, datetime

from sqlalchemy.orm import Session

from vpn_core.billing_domain.db_model import PaymentMethod as PaymentMethodORM
from vpn_core.billing_domain.db_model import PaymentRequest as PaymentRequestORM
from vpn_core.billing_domain.db_model import Wallet as WalletORM
from vpn_core.billing_domain.db_model import WalletTransaction as WalletTransactionORM
from vpn_core.billing_domain.domain.financial_report import FinancialReport, PurposeBreakdown
from vpn_core.billing_domain.domain.payment_method import PaymentMethod
from vpn_core.billing_domain.domain.payment_request import PaymentPurpose, PaymentRequest, PaymentRequestStatus
from vpn_core.billing_domain.domain.queries import (
    GetPaymentRequestQuery,
    GetWalletQuery,
    ListPaymentRequestsQuery,
)
from vpn_core.billing_domain.domain.wallet import Wallet, WalletTransaction, WalletTransactionType
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
            card_numbers=method.card_numbers,
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
        obj.card_numbers = method.card_numbers
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

    async def get_financial_report(self, start_at: datetime, end_at: datetime) -> FinancialReport:
        start = start_at if start_at.tzinfo else start_at.replace(tzinfo=UTC)
        end = end_at if end_at.tzinfo else end_at.replace(tzinfo=UTC)

        completed = (
            self._session.query(PaymentRequestORM)
            .filter(
                PaymentRequestORM.status == PaymentRequestStatus.completed,
                PaymentRequestORM.updated_at >= start,
                PaymentRequestORM.updated_at < end,
            )
            .all()
        )
        manual_total = sum(item.amount_toman for item in completed)
        by_purpose: dict[str, PurposeBreakdown] = {}
        for purpose in PaymentPurpose:
            items = [item for item in completed if item.purpose == purpose]
            by_purpose[purpose.value] = PurposeBreakdown(
                count=len(items),
                total_toman=sum(item.amount_toman for item in items),
            )

        wallet_debits = (
            self._session.query(WalletTransactionORM)
            .filter(
                WalletTransactionORM.transaction_type == WalletTransactionType.debit,
                WalletTransactionORM.created_at >= start,
                WalletTransactionORM.created_at < end,
            )
            .all()
        )
        wallet_sales_total = sum(item.amount_toman for item in wallet_debits)
        wallet_credits = (
            self._session.query(WalletTransactionORM)
            .filter(
                WalletTransactionORM.transaction_type == WalletTransactionType.credit,
                WalletTransactionORM.reference_type == "payment_request",
                WalletTransactionORM.created_at >= start,
                WalletTransactionORM.created_at < end,
            )
            .all()
        )
        wallet_topups_total = sum(item.amount_toman for item in wallet_credits)

        pending = (
            self._session.query(PaymentRequestORM)
            .filter(PaymentRequestORM.status == PaymentRequestStatus.pending_approval)
            .all()
        )

        return FinancialReport(
            period="custom",
            start_at=start,
            end_at=end,
            total_income_toman=manual_total + wallet_sales_total,
            manual_payments_count=len(completed),
            manual_payments_total_toman=manual_total,
            manual_payments_by_purpose=by_purpose,
            wallet_sales_count=len(wallet_debits),
            wallet_sales_total_toman=wallet_sales_total,
            wallet_topups_count=len(wallet_credits),
            wallet_topups_total_toman=wallet_topups_total,
            pending_approval_count=len(pending),
            pending_approval_total_toman=sum(item.amount_toman for item in pending),
        )
