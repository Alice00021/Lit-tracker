"""
Backward-compatible re-exports from common.exceptions.

Все исключения теперь живут в common-service — единый источник
для всех микросервисов.
"""
from common.exceptions import (
    AppException,
    NotFoundError,
    ValidationError,
    ConflictError,
    UnauthorizedError,
    ForbiddenError,
    ServiceError,
    BadRequestError,
    RateLimitError,
)

__all__ = [
    "AppException",
    "NotFoundError",
    "ValidationError",
    "ConflictError",
    "UnauthorizedError",
    "ForbiddenError",
    "ServiceError",
    "BadRequestError",
    "RateLimitError",
]
