from datetime import datetime

from pydantic import BaseModel

from vpn_core.traffic_monitoring_domain.domain.connection_log import ConnectionEvent
from vpn_core.traffic_monitoring_domain.domain.quota_signal import QuotaSignalType


class ListTrafficSamplesQuery(BaseModel):
    uuid: str | None = None
    server_id: int | None = None


class ListTrafficAggregationsQuery(BaseModel):
    uuid: str | None = None
    subscription_id: int | None = None
    server_id: int | None = None


class ListUsageHistoryQuery(BaseModel):
    user_id: int | None = None
    subscription_id: int | None = None
    server_id: int | None = None
    since: datetime | None = None


class GetLatestRealtimeSnapshotQuery(BaseModel):
    server_id: int


class ListRealtimeSnapshotsQuery(BaseModel):
    server_id: int | None = None


class ListConnectionLogsQuery(BaseModel):
    uuid: str | None = None
    server_id: int | None = None
    subscription_id: int | None = None
    event: ConnectionEvent | None = None


class ListHealthMetricsQuery(BaseModel):
    server_id: int | None = None
    since: datetime | None = None


class ListQuotaSignalsQuery(BaseModel):
    user_id: int | None = None
    subscription_id: int | None = None
    signal_type: QuotaSignalType | None = None
    acknowledged: bool | None = None
