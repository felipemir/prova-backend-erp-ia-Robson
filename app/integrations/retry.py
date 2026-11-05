import asyncio
import logging
from collections.abc import Awaitable, Callable
from typing import TypeVar

from app.core.config import Settings

logger = logging.getLogger(__name__)
T = TypeVar("T")


class IntegrationError(Exception):
    """Falha esperada de uma integração."""


class TransientServiceError(IntegrationError):
    """Falha transitória passível de nova tentativa."""


class PermanentServiceError(IntegrationError):
    """Falha permanente que não deve ser repetida."""


async def call_with_retry(
    operation: Callable[[], Awaitable[T]],
    service_name: str,
    settings: Settings,
) -> T:
    for attempt in range(1, settings.max_attempts + 1):
        try:
            return await asyncio.wait_for(
                operation(), timeout=settings.request_timeout
            )
        except (TimeoutError, TransientServiceError) as exc:
            logger.warning(
                "Falha transitória na integração %s, tentativa %s/%s (%s)",
                service_name,
                attempt,
                settings.max_attempts,
                type(exc).__name__,
            )
            if attempt == settings.max_attempts:
                raise
            await asyncio.sleep(settings.backoff_base * (2 ** (attempt - 1)))

    raise RuntimeError("Nenhuma tentativa foi executada")
