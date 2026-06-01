from abc import ABC, abstractmethod

from sqlalchemy import Engine
from sqlalchemy.orm import Session


class BaseDatabase(ABC):
    @abstractmethod
    def create_url(self) -> dict:
        pass

    @abstractmethod
    def create_engine(self, url) -> Engine:
        pass

    @abstractmethod
    def setup_session(self, engine:Engine) -> Session:
        pass



