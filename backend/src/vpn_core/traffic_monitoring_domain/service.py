from datetime import UTC, datetime

from vpn_core.traffic_monitoring_domain.domain.commands import (
    AcknowledgeQuotaSignalCommand,
    AggregateTrafficCommand,
    CollectTrafficCommand,
    EmitQuotaSignalCommand,
)
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
from vpn_core.traffic_monitoring_domain.domain.quota_signal import QuotaSignal, QuotaSignalType
from vpn_core.traffic_monitoring_domain.domain.realtime_snapshot import RealtimeSnapshot
from vpn_core.traffic_monitoring_domain.domain.traffic_aggregation import TrafficAggregation
from vpn_core.traffic_monitoring_domain.domain.traffic_sample import TrafficSample
from vpn_core.traffic_monitoring_domain.domain.usage_history import UsageHistory
from vpn_core.traffic_monitoring_domain.repository.base import TrafficMonitoringRepository


class TrafficMonitoringService:
    def __init__(self, repository: TrafficMonitoringRepository):
        self._repository = repository

    async def collect_traffic(self, command: CollectTrafficCommand) -> TrafficSample:
        sample = TrafficSample(
            uuid=command.uuid,
            server_id=command.server_id,
            upload_bytes=command.upload_bytes,
            download_bytes=command.download_bytes,
            connection_type=command.connection_type,
            recorded_at=command.recorded_at or datetime.now(UTC),
        )
        return await self._repository.create_traffic_sample(sample)

    async def list_traffic_samples(self, query: ListTrafficSamplesQuery) -> list[TrafficSample]:
        return await self._repository.list_traffic_samples(query)

    async def aggregate_traffic(self, command: AggregateTrafficCommand) -> TrafficAggregation:
        upload_bytes, download_bytes = await self._repository.sum_traffic_samples(
            uuid=command.uuid,
            server_id=command.server_id,
            period_start=command.period_start,
            period_end=command.period_end,
        )
        total_bytes = upload_bytes + download_bytes

        aggregation = TrafficAggregation(
            uuid=command.uuid,
            subscription_id=command.subscription_id,
            server_id=command.server_id,
            upload_bytes=upload_bytes,
            download_bytes=download_bytes,
            total_bytes=total_bytes,
            period_start=command.period_start,
            period_end=command.period_end,
        )
        return await self._repository.create_traffic_aggregation(aggregation)

    async def list_traffic_aggregations(
        self,
        query: ListTrafficAggregationsQuery,
    ) -> list[TrafficAggregation]:
        return await self._repository.list_traffic_aggregations(query)

    async def record_usage_history(self, history: UsageHistory) -> UsageHistory:
        if history.recorded_at is None:
            history.recorded_at = datetime.now(UTC)
        return await self._repository.create_usage_history(history)

    async def list_usage_history(self, query: ListUsageHistoryQuery) -> list[UsageHistory]:
        return await self._repository.list_usage_history(query)

    async def record_realtime_snapshot(self, snapshot: RealtimeSnapshot) -> RealtimeSnapshot:
        if snapshot.recorded_at is None:
            snapshot.recorded_at = datetime.now(UTC)
        return await self._repository.create_realtime_snapshot(snapshot)

    async def get_latest_realtime_snapshot(
        self,
        query: GetLatestRealtimeSnapshotQuery,
    ) -> RealtimeSnapshot | None:
        return await self._repository.get_latest_realtime_snapshot(query)

    async def list_realtime_snapshots(
        self,
        query: ListRealtimeSnapshotsQuery,
    ) -> list[RealtimeSnapshot]:
        return await self._repository.list_realtime_snapshots(query)

    async def record_connection_log(self, log: ConnectionLog) -> ConnectionLog:
        if log.recorded_at is None:
            log.recorded_at = datetime.now(UTC)
        return await self._repository.create_connection_log(log)

    async def list_connection_logs(self, query: ListConnectionLogsQuery) -> list[ConnectionLog]:
        return await self._repository.list_connection_logs(query)

    async def record_health_metric(self, metric: HealthMetric) -> HealthMetric:
        if metric.recorded_at is None:
            metric.recorded_at = datetime.now(UTC)
        return await self._repository.create_health_metric(metric)

    async def list_health_metrics(self, query: ListHealthMetricsQuery) -> list[HealthMetric]:
        return await self._repository.list_health_metrics(query)

    async def emit_quota_signal(self, command: EmitQuotaSignalCommand) -> QuotaSignal | None:
        if command.limit_bytes <= 0:
            return None

        ratio = command.used_bytes / command.limit_bytes
        if ratio >= 1.0:
            signal_type = QuotaSignalType.traffic_exceeded
        elif ratio >= command.approaching_threshold:
            signal_type = QuotaSignalType.approaching_limit
        else:
            return None

        signal = QuotaSignal(
            user_id=command.user_id,
            subscription_id=command.subscription_id,
            uuid=command.uuid,
            signal_type=signal_type,
            used_bytes=command.used_bytes,
            limit_bytes=command.limit_bytes,
            recorded_at=datetime.now(UTC),
        )
        return await self._repository.create_quota_signal(signal)

    async def acknowledge_quota_signal(
        self,
        command: AcknowledgeQuotaSignalCommand,
    ) -> QuotaSignal | None:
        signal = await self._repository.get_quota_signal(command.signal_id)
        if not signal:
            return None

        signal.acknowledged = True
        return await self._repository.update_quota_signal(signal)

    async def list_quota_signals(self, query: ListQuotaSignalsQuery) -> list[QuotaSignal]:
        return await self._repository.list_quota_signals(query)
