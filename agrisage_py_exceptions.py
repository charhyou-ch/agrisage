"""
Hiérarchie des exceptions AgriSage SDK.

Chaque exception expose :
  - message    : description humaine
  - code       : code machine (ex: UNAUTHORIZED)
  - status_code: code HTTP
  - request_id : identifiant de la requête (utile pour le support)
  - suggestion : conseil de résolution
"""


class AgriSageError(Exception):
    """Erreur de base du SDK AgriSage."""

    def __init__(
        self,
        message: str,
        code: str = "UNKNOWN_ERROR",
        status_code: int | None = None,
        request_id: str | None = None,
        suggestion: str | None = None,
    ):
        super().__init__(message)
        self.message     = message
        self.code        = code
        self.status_code = status_code
        self.request_id  = request_id
        self.suggestion  = suggestion

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}("
            f"code={self.code!r}, "
            f"status_code={self.status_code}, "
            f"message={self.message!r})"
        )


class AuthenticationError(AgriSageError):
    """Clé API manquante, expirée ou invalide (HTTP 401)."""

    def __init__(self, message: str, request_id: str | None = None):
        super().__init__(message, "UNAUTHORIZED", 401, request_id)


class PlanLimitError(AgriSageError):
    """Fonctionnalité non disponible sur votre plan actuel (HTTP 403)."""

    def __init__(
        self,
        message: str,
        request_id: str | None = None,
        suggestion: str | None = None,
    ):
        super().__init__(message, "PLAN_LIMIT", 403, request_id, suggestion)


class QuotaExceededError(AgriSageError):
    """Quota mensuel de requêtes atteint (HTTP 429)."""

    def __init__(
        self,
        message: str,
        request_id: str | None = None,
        reset_at: str | None = None,
    ):
        super().__init__(message, "QUOTA_EXCEEDED", 429, request_id)
        self.reset_at = reset_at


class NotFoundError(AgriSageError):
    """Ressource introuvable (HTTP 404)."""

    def __init__(
        self,
        message: str,
        request_id: str | None = None,
        suggestion: str | None = None,
    ):
        super().__init__(message, "NOT_FOUND", 404, request_id, suggestion)


class ValidationError(AgriSageError):
    """Paramètre invalide ou manquant (HTTP 400)."""

    def __init__(
        self,
        message: str,
        request_id: str | None = None,
        suggestion: str | None = None,
    ):
        super().__init__(message, "INVALID_PARAM", 400, request_id, suggestion)


class NetworkError(AgriSageError):
    """Erreur réseau (timeout, connexion refusée, etc.)."""

    def __init__(self, message: str, original_error: Exception | None = None):
        super().__init__(message, "NETWORK_ERROR")
        self.original_error = original_error
