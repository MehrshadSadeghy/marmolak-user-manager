from datetime import datetime

from pydantic import BaseModel, Field

from vpn_core.traffic_monitoring_domain.domain.commands import (
    AcknowledgeQuotaSignalCommand,
    AggregateTrafficCommand,
    CollectTrafficCommand,
    EmitQuotaSignalCommand,
)
from vpn_core.traffic_monitoring_domain.domain.connection_log import (
    ConnectionEvent,
    ConnectionLog,
)
from vpn_core.traffic_monitoring_domain.domain.health_metric import HealthMetric
from vpn_core.traffic_monitoring_domain.domain.queries import (
    GetLatestRealtimeSnapshotQuery,
    ListConnectionLogsQuery,
    ListHealthMetricsQuery,
    ListQuotaSignalsQuery,
    ListRealtimeSnapshotsQuery,
    ListTrafficAggregationsQuery,
    ListTrafficSamplesQuery,
    ListUsageHistoryQuery,
)
from vpn_core.traffic_monitoring_domain.domain.quota_signal import QuotaSignal, QuotaSignalType
from vpn_core.traffic_monitoring_domain.domain.realtime_snapshot import RealtimeSnapshot
from vpn_core.traffic_monitoring_domain.domain.traffic_aggregation import TrafficAggregation
from vpn_core.traffic_monitoring_domain.domain.traffic_sample import ConnectionType, TrafficSample
from vpn_core.traffic_monitoring_domain.domain.usage_history import UsageHistory


class CollectTrafficDTO(BaseModel):
    uuid: str = Field(..., max_length=64)
    server_id: int
    upload_bytes: int = Field(default=0, ge=0)
    download_bytes: int = Field(default=0, ge=0)
    connection_type: ConnectionType = ConnectionType.unknown
    recorded_at: datetime | None = None

    def to_domain(self) -> CollectTrafficCommand:
        return CollectTrafficCommand(
            uuid=self.uuid,
            server_id=self.server_id,
            upload_bytes=self.upload_bytes,
            download_bytes=self.download_bytes,
            connection_type=self.connection_type,
            recorded_at=self.recorded_at,
        )


class AggregateTrafficDTO(BaseModel):
    uuid: str = Field(..., max_length=64)
    subscription_id: int | None = None
    server_id: int | None = None
    period_start: datetime | None = None
    period_end: datetime | None = None

    def to_domain(self) -> AggregateTrafficCommand:
        return AggregateTrafficCommand(
            uuid=self.uuid,
            subscription_id=self.subscription_id,
            server_id=self.server_id,
            period_start=self.period_start,
            period_end=self.period_end,
        )


class CreateUsageHistoryDTO(BaseModel):
    user_id: int
    subscription_id: int
    server_id: int | None = None
    used_bytes: int = Field(default=0, ge=0)
    recorded_at: datetime | None = None

    def to_domain(self) -> UsageHistory:
        return UsageHistory(
            user_id=self.user_id,
            subscription_id=self.subscription_id,
            server_id=self.server_id,
            used_bytes=self.used_bytes,
            recorded_at=self.recorded_at,
        )


class CreateRealtimeSnapshotDTO(BaseModel):
    server_id: int
    active_users: int = Field(default=0, ge=0)
    bandwidth_mbps: float = Field(default=0.0, ge=0.0)
    upload_bps: int = Field(default=0, ge=0)
    download_bps: int = Field(default=0, ge=0)
    recorded_at: datetime | None = None

    def to_domain(self) -> RealtimeSnapshot:
        return RealtimeSnapshot(
            server_id=self.server_id,
            active_users=self.active_users,
            bandwidth_mbps=self.bandwidth_mbps,
            upload_bps=self.upload_bps,
            download_bps=self.download_bps,
            recorded_at=self.recorded_at,
        )


class CreateConnectionLogDTO(BaseModel):
    uuid: str = Field(..., max_length=64)
    server_id: int
    event: ConnectionEvent
    user_id: int | None = None
    subscription_id: int | None = None
    connection_type: ConnectionType = ConnectionType.unknown
    recorded_at: datetime | None = None

    def to_domain(self) -> ConnectionLog:
        return ConnectionLog(
            uuid=self.uuid,
            server_id=self.server_id,
            event=self.event,
            user_id=self.user_id,
            subscription_id=self.subscription_id,
            connection_type=self.connection_type,
            recorded_at=self.recorded_at,
        )


class CreateHealthMetricDTO(BaseModel):
    server_id: int
    cpu_usage: float = Field(default=0.0, ge=0.0, le=100.0)
    ram_usage: float = Field(default=0.0, ge=0.0, le=100.0)
    disk_usage: float = Field(default=0.0, ge=0.0, le=100.0)
    latency_ms: float = Field(default=0.0, ge=0.0)
    recorded_at: datetime | None = None

    def to_domain(self) -> HealthMetric:
        return HealthMetric(
            server_id=self.server_id,
            cpu_usage=self.cpu_usage,
            ram_usage=self.ram_usage,
            disk_usage=self.disk_usage,
            latency_ms=self.latency_ms,
            recorded_at=self.recorded_at,
        )


class EmitQuotaSignalDTO(BaseModel):
    user_id: int
    subscription_id: int
    uuid: str = Field(..., max_length=64)
    used_bytes: int = Field(..., ge=0)
    limit_bytes: int = Field(..., ge=0)
    approaching_threshold: float = Field(default=0.9, ge=0.0, le=1.0)

    def to_domain(self) -> EmitQuotaSignalCommand:
        return EmitQuotaSignalCommand(
            user_id=self.user_id,
            subscription_id=self.subscription_id,
            uuid=self.uuid,
            used_bytes=self.used_bytes,
            limit_bytes=self.limit_bytes,
            approaching_threshold=self.approaching_threshold,
        )


class TrafficSampleResponseDTO(BaseModel):
    traffic_sample: TrafficSample


class TrafficSampleListResponseDTO(BaseModel):
    traffic_samples: list[TrafficSample]


class TrafficAggregationResponseDTO(BaseModel):
    traffic_aggregation: TrafficAggregation


class TrafficAggregationListResponseDTO(BaseModel):
    traffic_aggregations: list[TrafficAggregation]


class UsageHistoryResponseDTO(BaseModel):
    usage_history: UsageHistory


class UsageHistoryListResponseDTO(BaseModel):
    usage_history: list[UsageHistory]


class RealtimeSnapshotResponseDTO(BaseModel):
    realtime_snapshot: RealtimeSnapshot


class RealtimeSnapshotListResponseDTO(BaseModel):
    realtime_snapshots: list[RealtimeSnapshot]


class ConnectionLogResponseDTO(BaseModel):
    connection_log: ConnectionLog


class ConnectionLogListResponseDTO(BaseModel):
    connection_logs: list[ConnectionLog]


class HealthMetricResponseDTO(BaseModel):
    health_metric: HealthMetric


class HealthMetricListResponseDTO(BaseModel):
    health_metrics: list[HealthMetric]


class QuotaSignalResponseDTO(BaseModel):
    quota_signal: QuotaSignal


class QuotaSignalListResponseDTO(BaseModel):
    quota_signals: list[QuotaSignal]


class ListTrafficSamplesQueryDTO(BaseModel):
    uuid: str | None = None
    server_id: int | None = None

    def to_domain(self) -> ListTrafficSamplesQuery:
        return ListTrafficSamplesQuery(uuid=self.uuid, server_id=self.server_id)


class ListTrafficAggregationsQueryDTO(BaseModel):
    uuid: str | None = None
    subscription_id: int | None = None
    server_id: int | None = None

    def to_domain(self) -> ListTrafficAggregationsQuery:
        return ListTrafficAggregationsQuery(
            uuid=self.uuid,
            subscription_id=self.subscription_id,
            server_id=self.server_id,
        )


class ListUsageHistoryQueryDTO(BaseModel):
    user_id: int | None = None
    subscription_id: int | None = None
    server_id: int | None = None
    since: datetime | None = None

    def to_domain(self) -> ListUsageHistoryQuery:
        return ListUsageHistoryQuery(
            user_id=self.user_id,
            subscription_id=self.subscription_id,
            server_id=self.server_id,
            since=self.since,
        )


class GetLatestRealtimeSnapshotQueryDTO(BaseModel):
    server_id: int

    def to_domain(self) -> GetLatestRealtimeSnapshotQuery:
        return GetLatestRealtimeSnapshotQuery(server_id=self.server_id)


class ListRealtimeSnapshotsQueryDTO(BaseModel):
    server_id: int | None = None

    def to_domain(self) -> ListRealtimeSnapshotsQuery:
        return ListRealtimeSnapshotsQuery(server_id=self.server_id)


class ListConnectionLogsQueryDTO(BaseModel):
    uuid: str | None = None
    server_id: int | None = None
    subscription_id: int | None = None
    event: ConnectionEvent | None = None

    def to_domain(self) -> ListConnectionLogsQuery:
        return ListConnectionLogsQuery(
            uuid=self.uuid,
            server_id=self.server_id,
            subscription_id=self.subscription_id,
            event=self.event,
        )


class ListHealthMetricsQueryDTO(BaseModel):
    server_id: int | None = None
    since: datetime | None = None

    def to_domain(self) -> ListHealthMetricsQuery:
        return ListHealthMetricsQuery(server_id=self.server_id, since=self.since)


class ListQuotaSignalsQueryDTO(BaseModel):
    user_id: int | None = None
    subscription_id: int | None = None
    signal_type: QuotaSignalType | None = None
    acknowledged: bool | None = None

    def to_domain(self) -> ListQuotaSignalsQuery:
        return ListQuotaSignalsQuery(
            user_id=self.user_id,
            subscription_id=self.subscription_id,
            signal_type=self.signal_type,
            acknowledged=self.acknowledged,
        )


class AcknowledgeQuotaSignalDTO(BaseModel):
    def to_domain(self, signal_id: int) -> AcknowledgeQuotaSignalCommand:
        return AcknowledgeQuotaSignalCommand(signal_id=signal_id)
