import asyncio
import logging
import os
from typing import TYPE_CHECKING

from vpn_core.core.manager.base import Manager

if TYPE_CHECKING:
    from vpn_core.container import AppContainer

LOGGER = logging.getLogger(__name__)

DEFAULT_INTERVAL_SECONDS = 3600


class TrafficEnforcementManager(Manager):
    def __init__(self, container: "AppContainer"):
        self._container = container
        self._enabled = os.getenv("TRAFFIC_ENFORCEMENT_ENABLED", "true").lower() in (
            "1",
            "true",
            "yes",
        )
        self._interval_seconds = int(
            os.getenv("TRAFFIC_ENFORCEMENT_INTERVAL_SECONDS", str(DEFAULT_INTERVAL_SECONDS))
        )

    async def setup(self) -> None:
        if self._enabled:
            LOGGER.info(
                "Traffic enforcement enabled (interval=%ss)",
                self._interval_seconds,
            )
        else:
            LOGGER.info("Traffic enforcement disabled")

    async def run(self) -> None:
        if not self._enabled:
            return

        while True:
            await self._run_cycle()
            await asyncio.sleep(self._interval_seconds)

    async def _run_cycle(self) -> None:
        session = self._container.create_db_session()
        try:
            service = self._container.build_openvpn_traffic_enforcement_service(session)
            summary = await service.sync_and_enforce()
            LOGGER.info(
                "Traffic enforcement cycle complete: checked=%s bytes=%s exceeded=%s revoked=%s errors=%s",
                summary.subscriptions_checked,
                summary.bytes_accounted,
                summary.subscriptions_exceeded,
                summary.configs_revoked,
                len(summary.errors),
            )
            for error in summary.errors:
                LOGGER.warning("Traffic enforcement: %s", error)
        except Exception:
            LOGGER.exception("Traffic enforcement cycle failed")
        finally:
            session.close()

    async def teardown(self) -> None:
        pass
