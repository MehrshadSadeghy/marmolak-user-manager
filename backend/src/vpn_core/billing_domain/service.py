from fastapi import HTTPException

from vpn_core.billing_domain.domain.commands import (
    CreatePaymentRequestCommand,
    CreditWalletCommand,
    DebitWalletCommand,
    ReviewPaymentRequestCommand,
    SubmitPaymentReceiptCommand,
)
from vpn_core.billing_domain.domain.payment_method import PaymentMethod
from vpn_core.billing_domain.domain.financial_report import FinancialReport
from vpn_core.billing_domain.domain.payment_request import (
    PaymentRequest,
    PaymentRequestStatus,
)
from vpn_core.billing_domain.domain.queries import (
    GetPaymentRequestQuery,
    GetWalletQuery,
    ListPaymentRequestsQuery,
)
from vpn_core.billing_domain.domain.wallet import Wallet, WalletTransaction, WalletTransactionType
from vpn_core.billing_domain.repository.base import BillingRepository


class BillingService:
    def __init__(self, repository: BillingRepository):
        self._repository = repository

    async def get_wallet(self, user_id: int) -> Wallet:
        return await self._repository.get_or_create_wallet(user_id)

    async def credit_wallet(self, command: CreditWalletCommand) -> Wallet:
        wallet = await self._repository.get_or_create_wallet(command.user_id)
        wallet.balance_toman += command.amount_toman
        wallet = await self._repository.update_wallet(wallet)
        await self._repository.create_transaction(
            WalletTransaction(
                wallet_id=wallet.id,
                user_id=command.user_id,
                amount_toman=command.amount_toman,
                transaction_type=WalletTransactionType.credit,
                description=command.description,
                reference_type=command.reference_type,
                reference_id=command.reference_id,
            )
        )
        return wallet

    async def debit_wallet(self, command: DebitWalletCommand) -> Wallet:
        wallet = await self._repository.get_or_create_wallet(command.user_id)
        if wallet.balance_toman < command.amount_toman:
            raise HTTPException(status_code=400, detail="Insufficient wallet balance")
        wallet.balance_toman -= command.amount_toman
        wallet = await self._repository.update_wallet(wallet)
        await self._repository.create_transaction(
            WalletTransaction(
                wallet_id=wallet.id,
                user_id=command.user_id,
                amount_toman=command.amount_toman,
                transaction_type=WalletTransactionType.debit,
                description=command.description,
                reference_type=command.reference_type,
                reference_id=command.reference_id,
            )
        )
        return wallet

    async def list_transactions(self, user_id: int) -> list[WalletTransaction]:
        return await self._repository.list_transactions(user_id)

    async def create_payment_method(self, method: PaymentMethod) -> PaymentMethod:
        return await self._repository.create_payment_method(method)

    async def update_payment_method(self, method: PaymentMethod) -> PaymentMethod | None:
        return await self._repository.update_payment_method(method)

    async def delete_payment_method(self, method_id: int) -> bool:
        return await self._repository.delete_payment_method(method_id)

    async def get_payment_method(self, method_id: int) -> PaymentMethod | None:
        return await self._repository.get_payment_method(method_id)

    async def list_payment_methods(self, active_only: bool = False) -> list[PaymentMethod]:
        return await self._repository.list_payment_methods(active_only=active_only)

    async def create_payment_request(self, command: CreatePaymentRequestCommand) -> PaymentRequest:
        request = PaymentRequest(
            user_id=command.user_id,
            payment_method_id=command.payment_method_id,
            purpose=command.purpose,
            amount_toman=command.amount_toman,
            plan_id=command.plan_id,
            subscription_id=command.subscription_id,
            service_type=command.service_type,
            status=PaymentRequestStatus.awaiting_receipt,
        )
        return await self._repository.create_payment_request(request)

    async def submit_payment_receipt(self, command: SubmitPaymentReceiptCommand) -> PaymentRequest:
        request = await self._repository.get_payment_request(
            GetPaymentRequestQuery(payment_request_id=command.payment_request_id)
        )
        if not request:
            raise HTTPException(status_code=404, detail="Payment request not found")
        if request.status not in {
            PaymentRequestStatus.awaiting_receipt,
            PaymentRequestStatus.pending_approval,
        }:
            raise HTTPException(status_code=400, detail="Payment request cannot accept receipt")

        request.receipt_file_id = command.receipt_file_id
        request.receipt_message_id = command.receipt_message_id
        request.status = PaymentRequestStatus.pending_approval
        updated = await self._repository.update_payment_request(request)
        if not updated:
            raise HTTPException(status_code=404, detail="Payment request not found")
        return updated

    async def get_payment_request(self, payment_request_id: int) -> PaymentRequest | None:
        return await self._repository.get_payment_request(
            GetPaymentRequestQuery(payment_request_id=payment_request_id)
        )

    async def list_payment_requests(
        self,
        query: ListPaymentRequestsQuery,
    ) -> list[PaymentRequest]:
        return await self._repository.list_payment_requests(query)

    async def get_financial_report(
        self,
        period: str,
        anchor: datetime | None = None,
    ) -> FinancialReport:
        from vpn_core.billing_domain.domain.financial_report import FinancialReport as Report

        start_at, end_at = self._resolve_report_range(period, anchor)
        report = await self._repository.get_financial_report(start_at, end_at)
        return Report(**{**report.model_dump(), "period": period})

    @staticmethod
    def _resolve_report_range(period: str, anchor: datetime | None) -> tuple[datetime, datetime]:
        from datetime import UTC, datetime, timedelta

        now = anchor or datetime.now(UTC)
        if now.tzinfo is None:
            now = now.replace(tzinfo=UTC)

        if period == "daily":
            start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            end = start + timedelta(days=1)
        elif period == "weekly":
            start = (now - timedelta(days=now.weekday())).replace(
                hour=0, minute=0, second=0, microsecond=0
            )
            end = start + timedelta(days=7)
        elif period == "monthly":
            start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            if start.month == 12:
                end = start.replace(year=start.year + 1, month=1)
            else:
                end = start.replace(month=start.month + 1)
        else:
            raise HTTPException(status_code=400, detail="period must be daily, weekly, or monthly")
        return start, end

    async def review_payment_request(self, command: ReviewPaymentRequestCommand) -> PaymentRequest:
        request = await self._repository.get_payment_request(
            GetPaymentRequestQuery(payment_request_id=command.payment_request_id)
        )
        if not request:
            raise HTTPException(status_code=404, detail="Payment request not found")
        if request.status != PaymentRequestStatus.pending_approval:
            raise HTTPException(status_code=400, detail="Payment request is not pending approval")

        request.reviewed_by_telegram_id = command.reviewer_telegram_id
        request.admin_note = command.admin_note
        request.status = (
            PaymentRequestStatus.approved if command.approve else PaymentRequestStatus.rejected
        )
        updated = await self._repository.update_payment_request(request)
        if not updated:
            raise HTTPException(status_code=404, detail="Payment request not found")
        return updated

    async def mark_payment_completed(self, payment_request_id: int) -> PaymentRequest:
        request = await self._repository.get_payment_request(
            GetPaymentRequestQuery(payment_request_id=payment_request_id)
        )
        if not request:
            raise HTTPException(status_code=404, detail="Payment request not found")
        request.status = PaymentRequestStatus.completed
        updated = await self._repository.update_payment_request(request)
        if not updated:
            raise HTTPException(status_code=404, detail="Payment request not found")
        return updated
