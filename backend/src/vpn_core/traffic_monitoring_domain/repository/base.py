from abc import ABC, abstractmethod

from vpn_core.traffic_monitoring_domain.domain.connection_log import ConnectionLog
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
from vpn_core.traffic_monitoring_domain.domain.quota_signal import QuotaSignal
from vpn_core.traffic_monitoring_domain.domain.realtime_snapshot import RealtimeSnapshot
from vpn_core.traffic_monitoring_domain.domain.traffic_aggregation import TrafficAggregation
from vpn_core.traffic_monitoring_domain.domain.traffic_sample import TrafficSample
from vpn_core.traffic_monitoring_domain.domain.usage_history import UsageHistory


class TrafficMonitoringRepository(ABC):
    @abstractmethod
    async def create_traffic_sample(self, sample: TrafficSample) -> TrafficSample:
        pass

    @abstractmethod
    async def list_traffic_samples(self, query: ListTrafficSamplesQuery) -> list[TrafficSample]:
        pass

    @abstractmethod
    async def sum_traffic_samples(
        self,
        uuid: str,
        server_id: int | None = None,
        period_start=None,
        period_end=None,
    ) -> tuple[int, int]:
        pass

    @abstractmethod
    async def create_traffic_aggregation(self, aggregation: TrafficAggregation) -> TrafficAggregation:
        pass

    @abstractmethod
    async def list_traffic_aggregations(
        self,
        query: ListTrafficAggregationsQuery,
    ) -> list[TrafficAggregation]:
        pass

    @abstractmethod
    async def create_usage_history(self, history: UsageHistory) -> UsageHistory:
        pass

    @abstractmethod
    async def list_usage_history(self, query: ListUsageHistoryQuery) -> list[UsageHistory]:
        pass

    @abstractmethod
    async def create_realtime_snapshot(self, snapshot: RealtimeSnapshot) -> RealtimeSnapshot:
        pass

    @abstractmethod
    async def get_latest_realtime_snapshot(
        self,
        query: GetLatestRealtimeSnapshotQuery,
    ) -> RealtimeSnapshot | None:
        pass

    @abstractmethod
    async def list_realtime_snapshots(
        self,
        query: ListRealtimeSnapshotsQuery,
    ) -> list[RealtimeSnapshot]:
        pass

    @abstractmethod
    async def create_connection_log(self, log: ConnectionLog) -> ConnectionLog:
        pass

    @abstractmethod
    async def list_connection_logs(self, query: ListConnectionLogsQuery) -> list[ConnectionLog]:
        pass

    @abstractmethod
    async def create_health_metric(self, metric: HealthMetric) -> HealthMetric:
        pass

    @abstractmethod
    async def list_health_metrics(self, query: ListHealthMetricsQuery) -> list[HealthMetric]:
        pass

    @abstractmethod
    async def create_quota_signal(self, signal: QuotaSignal) -> QuotaSignal:
        pass

    @abstractmethod
    async def get_quota_signal(self, signal_id: int) -> QuotaSignal | None:
        pass

    @abstractmethod
    async def update_quota_signal(self, signal: QuotaSignal) -> QuotaSignal | None:
        pass

    @abstractmethod
    async def list_quota_signals(self, query: ListQuotaSignalsQuery) -> list[QuotaSignal]:
        pass
