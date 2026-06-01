from datetime import datetime

from sqlalchemy import func
from sqlalchemy.orm import Session

from vpn_core.traffic_monitoring_domain.db_model import (
    ConnectionLogORM,
    HealthMetricORM,
    QuotaSignalORM,
    RealtimeSnapshotORM,
    TrafficAggregationORM,
    TrafficSampleORM,
    UsageHistoryORM,
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
from vpn_core.traffic_monitoring_domain.domain.quota_signal import QuotaSignal
from vpn_core.traffic_monitoring_domain.domain.realtime_snapshot import RealtimeSnapshot
from vpn_core.traffic_monitoring_domain.domain.traffic_aggregation import TrafficAggregation
from vpn_core.traffic_monitoring_domain.domain.traffic_sample import TrafficSample
from vpn_core.traffic_monitoring_domain.domain.usage_history import UsageHistory
from vpn_core.traffic_monitoring_domain.repository.base import TrafficMonitoringRepository


class TrafficMonitoringDBRepository(TrafficMonitoringRepository):
    def __init__(self, session: Session):
        self._session = session

    async def create_traffic_sample(self, sample: TrafficSample) -> TrafficSample:
        obj = TrafficSampleORM(
            uuid=sample.uuid,
            server_id=sample.server_id,
            upload_bytes=sample.upload_bytes,
            download_bytes=sample.download_bytes,
            connection_type=sample.connection_type,
            recorded_at=sample.recorded_at,
        )
        self._session.add(obj)
        self._session.commit()
        self._session.refresh(obj)
        return TrafficSample.model_validate(obj)

    async def list_traffic_samples(self, query: ListTrafficSamplesQuery) -> list[TrafficSample]:
        db_query = self._session.query(TrafficSampleORM)
        if query.uuid is not None:
            db_query = db_query.filter(TrafficSampleORM.uuid == query.uuid)
        if query.server_id is not None:
            db_query = db_query.filter(TrafficSampleORM.server_id == query.server_id)
        rows = db_query.order_by(TrafficSampleORM.recorded_at.desc()).all()
        return [TrafficSample.model_validate(row) for row in rows]

    async def sum_traffic_samples(
        self,
        uuid: str,
        server_id: int | None = None,
        period_start: datetime | None = None,
        period_end: datetime | None = None,
    ) -> tuple[int, int]:
        db_query = self._session.query(
            func.coalesce(func.sum(TrafficSampleORM.upload_bytes), 0),
            func.coalesce(func.sum(TrafficSampleORM.download_bytes), 0),
        ).filter(TrafficSampleORM.uuid == uuid)

        if server_id is not None:
            db_query = db_query.filter(TrafficSampleORM.server_id == server_id)
        if period_start is not None:
            db_query = db_query.filter(TrafficSampleORM.recorded_at >= period_start)
        if period_end is not None:
            db_query = db_query.filter(TrafficSampleORM.recorded_at <= period_end)

        upload_total, download_total = db_query.one()
        return int(upload_total), int(download_total)

    async def create_traffic_aggregation(
        self,
        aggregation: TrafficAggregation,
    ) -> TrafficAggregation:
        obj = TrafficAggregationORM(
            uuid=aggregation.uuid,
            subscription_id=aggregation.subscription_id,
            server_id=aggregation.server_id,
            upload_bytes=aggregation.upload_bytes,
            download_bytes=aggregation.download_bytes,
            total_bytes=aggregation.total_bytes,
            period_start=aggregation.period_start,
            period_end=aggregation.period_end,
        )
        self._session.add(obj)
        self._session.commit()
        self._session.refresh(obj)
        return TrafficAggregation.model_validate(obj)

    async def list_traffic_aggregations(
        self,
        query: ListTrafficAggregationsQuery,
    ) -> list[TrafficAggregation]:
        db_query = self._session.query(TrafficAggregationORM)
        if query.uuid is not None:
            db_query = db_query.filter(TrafficAggregationORM.uuid == query.uuid)
        if query.subscription_id is not None:
            db_query = db_query.filter(
                TrafficAggregationORM.subscription_id == query.subscription_id
            )
        if query.server_id is not None:
            db_query = db_query.filter(TrafficAggregationORM.server_id == query.server_id)
        rows = db_query.order_by(TrafficAggregationORM.created_at.desc()).all()
        return [TrafficAggregation.model_validate(row) for row in rows]

    async def create_usage_history(self, history: UsageHistory) -> UsageHistory:
        obj = UsageHistoryORM(
            user_id=history.user_id,
            subscription_id=history.subscription_id,
            server_id=history.server_id,
            used_bytes=history.used_bytes,
            recorded_at=history.recorded_at,
        )
        self._session.add(obj)
        self._session.commit()
        self._session.refresh(obj)
        return UsageHistory.model_validate(obj)

    async def list_usage_history(self, query: ListUsageHistoryQuery) -> list[UsageHistory]:
        db_query = self._session.query(UsageHistoryORM)
        if query.user_id is not None:
            db_query = db_query.filter(UsageHistoryORM.user_id == query.user_id)
        if query.subscription_id is not None:
            db_query = db_query.filter(UsageHistoryORM.subscription_id == query.subscription_id)
        if query.server_id is not None:
            db_query = db_query.filter(UsageHistoryORM.server_id == query.server_id)
        if query.since is not None:
            db_query = db_query.filter(UsageHistoryORM.recorded_at >= query.since)
        rows = db_query.order_by(UsageHistoryORM.recorded_at.desc()).all()
        return [UsageHistory.model_validate(row) for row in rows]

    async def create_realtime_snapshot(self, snapshot: RealtimeSnapshot) -> RealtimeSnapshot:
        obj = RealtimeSnapshotORM(
            server_id=snapshot.server_id,
            active_users=snapshot.active_users,
            bandwidth_mbps=snapshot.bandwidth_mbps,
            upload_bps=snapshot.upload_bps,
            download_bps=snapshot.download_bps,
            recorded_at=snapshot.recorded_at,
        )
        self._session.add(obj)
        self._session.commit()
        self._session.refresh(obj)
        return RealtimeSnapshot.model_validate(obj)

    async def get_latest_realtime_snapshot(
        self,
        query: GetLatestRealtimeSnapshotQuery,
    ) -> RealtimeSnapshot | None:
        obj = (
            self._session.query(RealtimeSnapshotORM)
            .filter(RealtimeSnapshotORM.server_id == query.server_id)
            .order_by(RealtimeSnapshotORM.recorded_at.desc())
            .first()
        )
        if not obj:
            return None
        return RealtimeSnapshot.model_validate(obj)

    async def list_realtime_snapshots(
        self,
        query: ListRealtimeSnapshotsQuery,
    ) -> list[RealtimeSnapshot]:
        db_query = self._session.query(RealtimeSnapshotORM)
        if query.server_id is not None:
            db_query = db_query.filter(RealtimeSnapshotORM.server_id == query.server_id)
        rows = db_query.order_by(RealtimeSnapshotORM.recorded_at.desc()).all()
        return [RealtimeSnapshot.model_validate(row) for row in rows]

    async def create_connection_log(self, log: ConnectionLog) -> ConnectionLog:
        obj = ConnectionLogORM(
            uuid=log.uuid,
            user_id=log.user_id,
            subscription_id=log.subscription_id,
            server_id=log.server_id,
            event=log.event,
            connection_type=log.connection_type,
            recorded_at=log.recorded_at,
        )
        self._session.add(obj)
        self._session.commit()
        self._session.refresh(obj)
        return ConnectionLog.model_validate(obj)

    async def list_connection_logs(self, query: ListConnectionLogsQuery) -> list[ConnectionLog]:
        db_query = self._session.query(ConnectionLogORM)
        if query.uuid is not None:
            db_query = db_query.filter(ConnectionLogORM.uuid == query.uuid)
        if query.server_id is not None:
            db_query = db_query.filter(ConnectionLogORM.server_id == query.server_id)
        if query.subscription_id is not None:
            db_query = db_query.filter(ConnectionLogORM.subscription_id == query.subscription_id)
        if query.event is not None:
            db_query = db_query.filter(ConnectionLogORM.event == query.event)
        rows = db_query.order_by(ConnectionLogORM.recorded_at.desc()).all()
        return [ConnectionLog.model_validate(row) for row in rows]

    async def create_health_metric(self, metric: HealthMetric) -> HealthMetric:
        obj = HealthMetricORM(
            server_id=metric.server_id,
            cpu_usage=metric.cpu_usage,
            ram_usage=metric.ram_usage,
            disk_usage=metric.disk_usage,
            latency_ms=metric.latency_ms,
            recorded_at=metric.recorded_at,
        )
        self._session.add(obj)
        self._session.commit()
        self._session.refresh(obj)
        return HealthMetric.model_validate(obj)

    async def list_health_metrics(self, query: ListHealthMetricsQuery) -> list[HealthMetric]:
        db_query = self._session.query(HealthMetricORM)
        if query.server_id is not None:
            db_query = db_query.filter(HealthMetricORM.server_id == query.server_id)
        if query.since is not None:
            db_query = db_query.filter(HealthMetricORM.recorded_at >= query.since)
        rows = db_query.order_by(HealthMetricORM.recorded_at.desc()).all()
        return [HealthMetric.model_validate(row) for row in rows]

    async def create_quota_signal(self, signal: QuotaSignal) -> QuotaSignal:
        obj = QuotaSignalORM(
            user_id=signal.user_id,
            subscription_id=signal.subscription_id,
            uuid=signal.uuid,
            signal_type=signal.signal_type,
            used_bytes=signal.used_bytes,
            limit_bytes=signal.limit_bytes,
            acknowledged=signal.acknowledged,
            recorded_at=signal.recorded_at,
        )
        self._session.add(obj)
        self._session.commit()
        self._session.refresh(obj)
        return QuotaSignal.model_validate(obj)

    async def get_quota_signal(self, signal_id: int) -> QuotaSignal | None:
        obj = self._session.get(QuotaSignalORM, signal_id)
        if not obj:
            return None
        return QuotaSignal.model_validate(obj)

    async def update_quota_signal(self, signal: QuotaSignal) -> QuotaSignal | None:
        obj = self._session.get(QuotaSignalORM, signal.id)
        if not obj:
            return None
        obj.acknowledged = signal.acknowledged
        self._session.add(obj)
        self._session.commit()
        self._session.refresh(obj)
        return QuotaSignal.model_validate(obj)

    async def list_quota_signals(self, query: ListQuotaSignalsQuery) -> list[QuotaSignal]:
        db_query = self._session.query(QuotaSignalORM)
        if query.user_id is not None:
            db_query = db_query.filter(QuotaSignalORM.user_id == query.user_id)
        if query.subscription_id is not None:
            db_query = db_query.filter(QuotaSignalORM.subscription_id == query.subscription_id)
        if query.signal_type is not None:
            db_query = db_query.filter(QuotaSignalORM.signal_type == query.signal_type)
        if query.acknowledged is not None:
            db_query = db_query.filter(QuotaSignalORM.acknowledged == query.acknowledged)
        rows = db_query.order_by(QuotaSignalORM.recorded_at.desc()).all()
        return [QuotaSignal.model_validate(row) for row in rows]
