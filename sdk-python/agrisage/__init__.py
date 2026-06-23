# ─────────────────────────────────────────────────────────────────────────────
# AgriSage SDK — Python
# Version : 1.0.0
# Docs    : https://docs.agrisage.ma
# Support : api@agrisage.ma
# Python  : >= 3.8
# Deps    : aucune dépendance externe (stdlib uniquement)
# ─────────────────────────────────────────────────────────────────────────────

from .client import AgriSageClient
from .exceptions import (
    AgriSageError,
    AuthenticationError,
    PlanLimitError,
    QuotaExceededError,
    NotFoundError,
    ValidationError,
    NetworkError,
)
from .constants import STADES, REGIONS, USAGES, ALERTES_TYPES

__version__ = "1.0.0"
__all__ = [
    "AgriSageClient",
    "AgriSageError",
    "AuthenticationError",
    "PlanLimitError",
    "QuotaExceededError",
    "NotFoundError",
    "ValidationError",
    "NetworkError",
    "STADES",
    "REGIONS",
    "USAGES",
    "ALERTES_TYPES",
]
