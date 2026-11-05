from typing import Any, Literal
from pydantic import BaseModel

ServiceStatus = Literal["success", "timeout", "error"]


class ServiceWarning(BaseModel):
    service: str
    message: str


class OrderSummaryResponse(BaseModel):
    order_id: str
    status: Literal["complete", "partial"]
    data: dict[str, dict[str, Any] | None]
    services: dict[str, ServiceStatus]
    warnings: list[ServiceWarning]
