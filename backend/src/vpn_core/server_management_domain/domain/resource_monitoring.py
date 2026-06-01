from pydantic import BaseModel, ConfigDict, Field


class ResourceMonitoring(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    cpu_usage: float = Field(default=0.0, ge=0.0, le=100.0, description="CPU usage percentage")
    ram_usage: float = Field(default=0.0, ge=0.0, le=100.0, description="RAM usage percentage")
    disk_usage: float = Field(default=0.0, ge=0.0, le=100.0, description="Disk usage percentage")
    network_in: int = Field(default=0, ge=0, description="Inbound traffic in bytes per second")
    network_out: int = Field(default=0, ge=0, description="Outbound traffic in bytes per second")
