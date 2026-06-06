from pydantic import BaseModel


class GetWalletQuery(BaseModel):
    user_id: int


class GetPaymentRequestQuery(BaseModel):
    payment_request_id: int


class ListPaymentRequestsQuery(BaseModel):
    user_id: int | None = None
    status: str | None = None
