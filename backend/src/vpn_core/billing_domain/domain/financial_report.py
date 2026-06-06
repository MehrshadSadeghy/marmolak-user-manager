from datetime import datetime

from pydantic import BaseModel


class PurposeBreakdown(BaseModel):
    count: int
    total_toman: int


class FinancialReport(BaseModel):
    period: str
    start_at: datetime
    end_at: datetime
    total_income_toman: int
    manual_payments_count: int
    manual_payments_total_toman: int
    manual_payments_by_purpose: dict[str, PurposeBreakdown]
    wallet_sales_count: int
    wallet_sales_total_toman: int
    wallet_topups_count: int
    wallet_topups_total_toman: int
    pending_approval_count: int
    pending_approval_total_toman: int
