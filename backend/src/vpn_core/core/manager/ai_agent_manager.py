import os

from dotenv import load_dotenv, find_dotenv
from langchain.chat_models import init_chat_model

from raya_trade_app.config import AIModelConfig
from raya_trade_app.core.manager.base import Manager


class AIManager(Manager):
    def __init__(self, model_config: AIModelConfig):
        self._model_config = model_config
        self._model = None

    async def setup(self) -> None:
        env_file = find_dotenv(usecwd=True)
        print(f"[DEBUG] .env found at: {env_file or 'NOT FOUND'}")

        if env_file:
            load_dotenv(env_file, override=True)

        google_key = os.environ.get("GOOGLE_API_KEY")
        print(f"[DEBUG] GOOGLE_API_KEY loaded: {bool(google_key)}")

        if not google_key:
            raise RuntimeError("GOOGLE_API_KEY is not set in environment or .env")

        model_kwargs = self._model_config.model_dump(exclude_none=True)
        self._model = init_chat_model(**model_kwargs)

    async def run(self) -> None:
        pass

    async def teardown(self) -> None:
        pass

    async def get_ai_model(self):
        return self._model