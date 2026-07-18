from pydantic import BaseModel


class V2RayUser(BaseModel):
    email: str
    telegram_id: str
