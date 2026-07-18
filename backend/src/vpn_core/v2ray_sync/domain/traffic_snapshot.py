from pydantic import BaseModel


class V2RayTrafficSnapshot(BaseModel):
    live: dict[str, int]
