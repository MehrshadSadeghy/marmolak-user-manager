import asyncio
import logging

from raya_trade_app.container import AppContainer

LOGGER = logging.getLogger(__name__)


async def main() -> None:
    container = AppContainer()
    managers = container.get_managers()

    try:
        await asyncio.gather(*[manager.setup() for manager in managers])
        await asyncio.gather(*[manager.run() for manager in managers])
    except Exception as ex:
        LOGGER.exception(ex)

    finally:
        await asyncio.gather(*[manager.teardown() for manager in managers])

if __name__ == "__main__":
    asyncio.run(main())


