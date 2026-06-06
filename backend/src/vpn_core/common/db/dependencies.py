from collections.abc import Generator
from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.orm import Session


def get_db_session(request: Request) -> Generator[Session, None, None]:
    session = request.app.state.container.create_db_session()
    try:
        yield session
    finally:
        session.close()


DbSessionDep = Annotated[Session, Depends(get_db_session)]
