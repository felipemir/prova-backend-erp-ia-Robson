import asyncio
import logging
from collections.abc import Awaitable, Callable
from typing import Any

from app.core.config import Settings, get_settings
from app.integrations import mock_services
from app.integrations.retry import IntegrationError, call_with_retry
from app.modules.orders.schemas import OrderSummaryResponse, ServiceStatus, ServiceWarning

logger = logging.getLogger(__name__)


async def consultar_com_protecao(
    service_name: str,
    operation: Callable[[], Awaitable[dict[str, Any]]],
    settings: Settings,
) -> tuple[str, dict[str, Any] | None, ServiceStatus]:
    try:
        data = await call_with_retry(operation, service_name, settings)
        return service_name, data, "success"
    except TimeoutError:
        logger.error("Timeout definitivo na integração %s", service_name)
        return service_name, None, "timeout"
    except IntegrationError:
        logger.exception("Falha definitiva na integração %s", service_name)
        return service_name, None, "error"
    except Exception:
        logger.exception("Erro inesperado na integração %s", service_name)
        raise


async def get_order_summary(order_id: str) -> OrderSummaryResponse:
    settings = get_settings()
    results = await asyncio.gather(
        consultar_com_protecao(
            "cliente", lambda: mock_services.consultar_cliente(order_id), settings
        ),
        consultar_com_protecao(
            "estoque", lambda: mock_services.consultar_estoque(order_id), settings
        ),
        consultar_com_protecao(
            "financeiro", lambda: mock_services.consultar_financeiro(order_id), settings
        ),
    )

    data: dict[str, dict[str, Any] | None] = {}
    services: dict[str, ServiceStatus] = {}
    warnings: list[ServiceWarning] = []
    for service_name, result, status in results:
        data[service_name] = result
        services[service_name] = status
        if status != "success":
            warnings.append(
                ServiceWarning(
                    service=service_name,
                    message="Dados temporariamente indisponíveis nesta integração.",
                )
            )

    return OrderSummaryResponse(
        order_id=order_id,
        status=("unavailable" if len(warnings) == len(results) else "partial" if warnings else "complete"),
        data=data,
        services=services,
        warnings=warnings,
    )
