import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    request_timeout: float = 2.0
    max_attempts: int = 3
    backoff_base: float = 0.5

    def __post_init__(self) -> None:
        if not 0 < self.request_timeout < float("inf"):
            raise ValueError("REQUEST_TIMEOUT deve ser positivo e finito")
        if not 1 <= self.max_attempts <= 3:
            raise ValueError("MAX_ATTEMPTS deve estar entre 1 e 3")
        if not 0 <= self.backoff_base < float("inf"):
            raise ValueError("BACKOFF_BASE deve ser não negativo e finito")


def get_settings() -> Settings:
    return Settings(
        request_timeout=float(os.getenv("REQUEST_TIMEOUT", "2.0")),
        max_attempts=int(os.getenv("MAX_ATTEMPTS", "3")),
        backoff_base=float(os.getenv("BACKOFF_BASE", "0.5")),
    )
