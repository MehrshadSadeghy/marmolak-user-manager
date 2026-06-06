import logging
from typing import TYPE_CHECKING

import uvicorn
from fastapi import APIRouter, FastAPI

from vpn_core.config import APIConfig
from vpn_core.core.manager.base import Manager

if TYPE_CHECKING:
    from vpn_core.container import AppContainer


LOGGER = logging.getLogger(__name__)

class APIManager(Manager):
    def __init__(
            self, api_config: APIConfig, container: "AppContainer", routers: list[APIRouter]
    ) -> None:
        self._config = api_config
        self._container = container
        self._routers = routers

        self._app: FastAPI | None = None
        self._uvicorn_server: uvicorn.Server | None = None

    async def setup(self) -> None:
        LOGGER.info("Setting up 'API Manager'")

        self._app = FastAPI(
            debug=self._config.debug,
            title=self._config.title,
            version=self._config.version,
        )

        for router in self._routers:
            self._app.include_router(router)

        self._app.state.container = self._container

        @self._app.on_event("startup")
        async def seed_commerce_defaults() -> None:
            session = self._container.create_db_session()
            try:
                await self._container.build_commerce_service(session).ensure_defaults()
            finally:
                session.close()

    async def run(self):
        LOGGER.info("Running 'API Manager'")

        if self._app is None:
            raise ValueError("APIManager is not setup")

        self._uvicorn_server = uvicorn.Server(
            config=uvicorn.Config(
                app=self._app,
                host=self._config.host,
                port=self._config.port,
            )
        )
        await self._uvicorn_server.serve()

    async def teardown(self) -> None:
        LOGGER.info("Tearing down `APIManager`")

