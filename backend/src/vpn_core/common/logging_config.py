import logging
import os

# Keep application logs; suppress noisy database/driver libraries.
_QUIET_LOGGER_PREFIXES = (
    "sqlalchemy",
    "asyncpg",
    "psycopg2",
    "neo4j",
    "neo4j.notifications",
    "alembic",
    "httpx",
    "httpcore",
)


def configure_logging() -> None:
    level_name = os.getenv("LOG_LEVEL", "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)

    logging.basicConfig(
        level=level,
        format="%(levelname)s: %(message)s",
        force=True,
    )

    for prefix in _QUIET_LOGGER_PREFIXES:
        logging.getLogger(prefix).setLevel(logging.WARNING)
