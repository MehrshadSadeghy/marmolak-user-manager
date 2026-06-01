from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query
from fastapi.params import Path

from vpn_core.traffic_monitoring_domain.api.v1.dependency import TrafficMonitoringServiceDep
from vpn_core.traffic_monitoring_domain.api.v1.dto import (
    AggregateTrafficDTO,
    AcknowledgeQuotaSignalDTO,
    CollectTrafficDTO,
    ConnectionLogListResponseDTO,
    ConnectionLogResponseDTO,
    CreateConnectionLogDTO,
    CreateHealthMetricDTO,
    CreateRealtimeSnapshotDTO,
    CreateUsageHistoryDTO,
    EmitQuotaSignalDTO,
    GetLatestRealtimeSnapshotQueryDTO,
    HealthMetricListResponseDTO,
    HealthMetricResponseDTO,
    ListConnectionLogsQueryDTO,
    ListHealthMetricsQueryDTO,
    ListQuotaSignalsQueryDTO,
    ListRealtimeSnapshotsQueryDTO,
    ListTrafficAggregationsQueryDTO,
    ListTrafficSamplesQueryDTO,
    ListUsageHistoryQueryDTO,
    QuotaSignalListResponseDTO,
    QuotaSignalResponseDTO,
    RealtimeSnapshotListResponseDTO,
    RealtimeSnapshotResponseDTO,
    TrafficAggregationListResponseDTO,
    TrafficAggregationResponseDTO,
    TrafficSampleListResponseDTO,
    TrafficSampleResponseDTO,
    UsageHistoryListResponseDTO,
    UsageHistoryResponseDTO,
)
from vpn_core.traffic_monitoring_domain.domain.connection_log import ConnectionEvent
from vpn_core.traffic_monitoring_domain.domain.quota_signal import QuotaSignalType

router = APIRouter(
    prefix="/api/v1/traffic-monitoring",
    tags=["traffic-monitoring"],
)


@router.post("/traffic/samples", response_model=TrafficSampleResponseDTO)
async def collect_traffic(
    body: CollectTrafficDTO,
    service: TrafficMonitoringServiceDep,
) -> TrafficSampleResponseDTO:
    sample = await service.collect_traffic(body.to_domain())
    return TrafficSampleResponseDTO(traffic_sample=sample)


@router.get("/traffic/samples", response_model=TrafficSampleListResponseDTO)
async def list_traffic_samples(
    service: TrafficMonitoringServiceDep,
    uuid: Annotated[str | None, Query()] = None,
    server_id: Annotated[int | None, Query()] = None,
) -> TrafficSampleListResponseDTO:
    query = ListTrafficSamplesQueryDTO(uuid=uuid, server_id=server_id).to_domain()
    samples = await service.list_traffic_samples(query)
    return TrafficSampleListResponseDTO(traffic_samples=samples)


@router.post("/traffic/aggregate", response_model=TrafficAggregationResponseDTO)
async def aggregate_traffic(
    body: AggregateTrafficDTO,
    service: TrafficMonitoringServiceDep,
) -> TrafficAggregationResponseDTO:
    aggregation = await service.aggregate_traffic(body.to_domain())
    return TrafficAggregationResponseDTO(traffic_aggregation=aggregation)


@router.get("/traffic/aggregations", response_model=TrafficAggregationListResponseDTO)
async def list_traffic_aggregations(
    service: TrafficMonitoringServiceDep,
    uuid: Annotated[str | None, Query()] = None,
    subscription_id: Annotated[int | None, Query()] = None,
    server_id: Annotated[int | None, Query()] = None,
) -> TrafficAggregationListResponseDTO:
    query = ListTrafficAggregationsQueryDTO(
        uuid=uuid,
        subscription_id=subscription_id,
        server_id=server_id,
    ).to_domain()
    aggregations = await service.list_traffic_aggregations(query)
    return TrafficAggregationListResponseDTO(traffic_aggregations=aggregations)


@router.post("/usage-history", response_model=UsageHistoryResponseDTO)
async def record_usage_history(
    body: CreateUsageHistoryDTO,
    service: TrafficMonitoringServiceDep,
) -> UsageHistoryResponseDTO:
    history = await service.record_usage_history(body.to_domain())
    return UsageHistoryResponseDTO(usage_history=history)


@router.get("/usage-history", response_model=UsageHistoryListResponseDTO)
async def list_usage_history(
    service: TrafficMonitoringServiceDep,
    user_id: Annotated[int | None, Query()] = None,
    subscription_id: Annotated[int | None, Query()] = None,
    server_id: Annotated[int | None, Query()] = None,
    since: Annotated[datetime | None, Query()] = None,
) -> UsageHistoryListResponseDTO:
    query = ListUsageHistoryQueryDTO(
        user_id=user_id,
        subscription_id=subscription_id,
        server_id=server_id,
        since=since,
    ).to_domain()
    history = await service.list_usage_history(query)
    return UsageHistoryListResponseDTO(usage_history=history)


@router.post("/realtime", response_model=RealtimeSnapshotResponseDTO)
async def record_realtime_snapshot(
    body: CreateRealtimeSnapshotDTO,
    service: TrafficMonitoringServiceDep,
) -> RealtimeSnapshotResponseDTO:
    snapshot = await service.record_realtime_snapshot(body.to_domain())
    return RealtimeSnapshotResponseDTO(realtime_snapshot=snapshot)


@router.get("/realtime", response_model=RealtimeSnapshotListResponseDTO)
async def list_realtime_snapshots(
    service: TrafficMonitoringServiceDep,
    server_id: Annotated[int | None, Query()] = None,
) -> RealtimeSnapshotListResponseDTO:
    query = ListRealtimeSnapshotsQueryDTO(server_id=server_id).to_domain()
    snapshots = await service.list_realtime_snapshots(query)
    return RealtimeSnapshotListResponseDTO(realtime_snapshots=snapshots)


@router.get("/realtime/servers/{server_id}/latest", response_model=RealtimeSnapshotResponseDTO)
async def get_latest_realtime_snapshot(
    server_id: Annotated[int, Path()],
    service: TrafficMonitoringServiceDep,
) -> RealtimeSnapshotResponseDTO:
    query = GetLatestRealtimeSnapshotQueryDTO(server_id=server_id).to_domain()
    snapshot = await service.get_latest_realtime_snapshot(query)
    if not snapshot:
        raise HTTPException(status_code=404, detail="No realtime snapshot found for server")
    return RealtimeSnapshotResponseDTO(realtime_snapshot=snapshot)


@router.post("/connection-logs", response_model=ConnectionLogResponseDTO)
async def record_connection_log(
    body: CreateConnectionLogDTO,
    service: TrafficMonitoringServiceDep,
) -> ConnectionLogResponseDTO:
    log = await service.record_connection_log(body.to_domain())
    return ConnectionLogResponseDTO(connection_log=log)


@router.get("/connection-logs", response_model=ConnectionLogListResponseDTO)
async def list_connection_logs(
    service: TrafficMonitoringServiceDep,
    uuid: Annotated[str | None, Query()] = None,
    server_id: Annotated[int | None, Query()] = None,
    subscription_id: Annotated[int | None, Query()] = None,
    event: Annotated[ConnectionEvent | None, Query()] = None,
) -> ConnectionLogListResponseDTO:
    query = ListConnectionLogsQueryDTO(
        uuid=uuid,
        server_id=server_id,
        subscription_id=subscription_id,
        event=event,
    ).to_domain()
    logs = await service.list_connection_logs(query)
    return ConnectionLogListResponseDTO(connection_logs=logs)


@router.post("/health-metrics", response_model=HealthMetricResponseDTO)
async def record_health_metric(
    body: CreateHealthMetricDTO,
    service: TrafficMonitoringServiceDep,
) -> HealthMetricResponseDTO:
    metric = await service.record_health_metric(body.to_domain())
    return HealthMetricResponseDTO(health_metric=metric)


@router.get("/health-metrics", response_model=HealthMetricListResponseDTO)
async def list_health_metrics(
    service: TrafficMonitoringServiceDep,
    server_id: Annotated[int | None, Query()] = None,
    since: Annotated[datetime | None, Query()] = None,
) -> HealthMetricListResponseDTO:
    query = ListHealthMetricsQueryDTO(server_id=server_id, since=since).to_domain()
    metrics = await service.list_health_metrics(query)
    return HealthMetricListResponseDTO(health_metrics=metrics)


@router.post("/quota-signals", response_model=QuotaSignalResponseDTO)
async def emit_quota_signal(
    body: EmitQuotaSignalDTO,
    service: TrafficMonitoringServiceDep,
) -> QuotaSignalResponseDTO:
    signal = await service.emit_quota_signal(body.to_domain())
    if not signal:
        raise HTTPException(
            status_code=422,
            detail="Usage is below threshold — no signal emitted",
        )
    return QuotaSignalResponseDTO(quota_signal=signal)


@router.get("/quota-signals", response_model=QuotaSignalListResponseDTO)
async def list_quota_signals(
    service: TrafficMonitoringServiceDep,
    user_id: Annotated[int | None, Query()] = None,
    subscription_id: Annotated[int | None, Query()] = None,
    signal_type: Annotated[QuotaSignalType | None, Query()] = None,
    acknowledged: Annotated[bool | None, Query()] = None,
) -> QuotaSignalListResponseDTO:
    query = ListQuotaSignalsQueryDTO(
        user_id=user_id,
        subscription_id=subscription_id,
        signal_type=signal_type,
        acknowledged=acknowledged,
    ).to_domain()
    signals = await service.list_quota_signals(query)
    return QuotaSignalListResponseDTO(quota_signals=signals)


@router.patch("/quota-signals/{signal_id}/acknowledge", response_model=QuotaSignalResponseDTO)
async def acknowledge_quota_signal(
    signal_id: Annotated[int, Path()],
    service: TrafficMonitoringServiceDep,
) -> QuotaSignalResponseDTO:
    command = AcknowledgeQuotaSignalDTO().to_domain(signal_id=signal_id)
    signal = await service.acknowledge_quota_signal(command)
    if not signal:
        raise HTTPException(status_code=404, detail="Quota signal not found")
    return QuotaSignalResponseDTO(quota_signal=signal)
