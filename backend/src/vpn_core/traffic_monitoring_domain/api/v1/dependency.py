from typing import Annotated

from fastapi import Depends, Request

from vpn_core.traffic_monitoring_domain.service import TrafficMonitoringService


def get_traffic_monitoring_service(request: Request) -> TrafficMonitoringService:
    container = request.app.state.container
    return container.get_traffic_monitoring_service()


TrafficMonitoringServiceDep = Annotated[
    TrafficMonitoringService,
    Depends(get_traffic_monitoring_service),
]
