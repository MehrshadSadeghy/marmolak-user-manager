import asyncio
import logging
import os
from typing import TYPE_CHECKING

from vpn_core.core.manager.base import Manager

if TYPE_CHECKING:
    from vpn_core.container import AppContainer

LOGGER = logging.getLogger(__name__)

DEFAULT_INTERVAL_SECONDS = 900


class ExpiryEnforcementManager(Manager):
    def __init__(self, container: "AppContainer"):
        self._container = container
        self._enabled = os.getenv("EXPIRY_ENFORCEMENT_ENABLED", "true").lower() in (
            "1",
            "true",
            "yes",
        )
        self._interval_seconds = int(
            os.getenv("EXPIRY_ENFORCEMENT_INTERVAL_SECONDS", str(DEFAULT_INTERVAL_SECONDS))
        )

    async def setup(self) -> None:
        if self._enabled:
            LOGGER.info(
                "Expiry enforcement enabled (interval=%ss)",
                self._interval_seconds,
            )
        else:
            LOGGER.info("Expiry enforcement disabled")

    async def run(self) -> None:
        if not self._enabled:
            return

        while True:
            await self._run_cycle()
            await asyncio.sleep(self._interval_seconds)

    async def _run_cycle(self) -> None:
        session = self._container.create_db_session()
        try:
            service = self._container.build_subscription_expiry_enforcement_service(session)
            summary = await service.enforce()
            LOGGER.info(
                "Expiry enforcement cycle complete: checked=%s expired=%s revoked=%s errors=%s",
                summary.subscriptions_checked,
                summary.subscriptions_expired,
                summary.configs_revoked,
                len(summary.errors),
            )
            for error in summary.errors:
                LOGGER.warning("Expiry enforcement: %s", error)
        except Exception:
            LOGGER.exception("Expiry enforcement cycle failed")
        finally:
            session.close()

    async def teardown(self) -> None:
        pass
