"""
Transport HTTP et client principal AgriSage.
Utilise uniquement la stdlib Python (urllib, json, time).
"""

from __future__ import annotations

import json
import logging
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from typing import Any

from .exceptions import (
    AgriSageError,
    AuthenticationError,
    NetworkError,
    NotFoundError,
    PlanLimitError,
    QuotaExceededError,
    ValidationError,
)
from .resources import (
    AlertesResource,
    CarnetResource,
    ConseilResource,
    CulturesResource,
    GroupesResource,
    ProduitsResource,
    TraitementResource,
)

__all__ = ["AgriSageClient", "ApiResponse", "RateLimit"]

SDK_VERSION      = "1.0.0"
DEFAULT_BASE_URL = "https://api.agrisage.ma/v1"
SANDBOX_BASE_URL = "https://api-sandbox.agrisage.ma/v1"
DEFAULT_TIMEOUT  = 30        # secondes
DEFAULT_RETRIES  = 2
RETRY_DELAY_S    = 0.5       # secondes (doublé à chaque tentative)

logger = logging.getLogger("agrisage")


@dataclass
class RateLimit:
    """Informations de quota extraites des headers HTTP."""
    limit:     int | None = None
    remaining: int | None = None
    reset:     str | None = None


@dataclass
class ApiResponse:
    """Réponse enrichie retournée par chaque méthode du SDK."""
    data:         Any
    rate_limit:   RateLimit = field(default_factory=RateLimit)
    content_type: str       = "application/json"


# ── Helpers internes ──────────────────────────────────────────────────────────

def _clean(d: dict) -> dict:
    """Supprime les valeurs None/vides pour ne pas polluer le JSON/query."""
    return {k: v for k, v in d.items() if v is not None}


def _require_fields(params: dict, fields: list[str], method: str) -> None:
    for f in fields:
        if not params.get(f) and params.get(f) != 0:
            raise ValidationError(
                f"Le champ '{f}' est requis pour {method}",
                suggestion=f"Consultez la doc : https://docs.agrisage.ma#{method.replace('.', '-')}",
            )


def _parse_error_body(body: bytes | str, status_code: int) -> dict:
    try:
        parsed = json.loads(body)
        err = parsed.get("error", {})
        return {
            "message":    err.get("message")    or f"Erreur HTTP {status_code}",
            "code":       err.get("code")        or "UNKNOWN_ERROR",
            "request_id": err.get("request_id"),
            "suggestion": err.get("suggestion"),
        }
    except (json.JSONDecodeError, AttributeError):
        return {
            "message":    f"Erreur HTTP {status_code}",
            "code":       "UNKNOWN_ERROR",
            "request_id": None,
            "suggestion": None,
        }


def _raise_for_status(status_code: int, body: bytes | str, headers: dict) -> None:
    info = _parse_error_body(body, status_code)
    msg        = info["message"]
    request_id = info["request_id"]
    suggestion = info["suggestion"]

    if status_code == 400:
        raise ValidationError(msg, request_id, suggestion)
    if status_code == 401:
        raise AuthenticationError(msg, request_id)
    if status_code == 403:
        raise PlanLimitError(msg, request_id, suggestion)
    if status_code == 404:
        raise NotFoundError(msg, request_id, suggestion)
    if status_code == 429:
        reset_at = headers.get("x-ratelimit-reset")
        raise QuotaExceededError(msg, request_id, reset_at)
    raise AgriSageError(msg, info["code"], status_code, request_id, suggestion)


# ── Client principal ──────────────────────────────────────────────────────────

class AgriSageClient:
    """
    Client Python pour l'API AgriSage.

    Exemple minimal ::

        import os
        from agrisage import AgriSageClient, STADES, REGIONS

        client = AgriSageClient(api_key=os.environ["AGRISAGE_API_KEY"])

        response = client.conseil.generer(
            culture="tomate",
            ravageur="botrytis",
            stade=STADES.FLORAISON,
            region=REGIONS.SOUSS_MASSA,
            dar_max=7,
            globalgap=True,
        )
        print(response.data["produit"])       # "Switch 62.5 WG"
        print(response.data["dar"])           # 3
        print(response.data["groupe_frac"])   # "9 + 12"

    Paramètres:
        api_key     : Clé API AgriSage (préfixe ``as_test_`` ou ``as_live_``)
        base_url    : URL de base personnalisée (écrase ``sandbox``)
        sandbox     : Si ``True``, utilise l'environnement sandbox
        lang        : Langue des réponses — ``'fr'`` (défaut) ou ``'ar'``
        timeout     : Timeout en secondes (défaut : 30)
        max_retries : Tentatives automatiques sur erreur réseau / 5xx (défaut : 2)
        debug       : Active les logs de debug via ``logging``
    """

    def __init__(
        self,
        *,
        api_key:     str,
        base_url:    str | None = None,
        sandbox:     bool = False,
        lang:        str = "fr",
        timeout:     int = DEFAULT_TIMEOUT,
        max_retries: int = DEFAULT_RETRIES,
        debug:       bool = False,
    ):
        if not api_key:
            raise AgriSageError(
                "api_key est requis. Obtenez votre clé sur agrisage.ma/dashboard",
                "MISSING_API_KEY",
            )

        self._api_key     = api_key
        self._base_url    = base_url or (SANDBOX_BASE_URL if sandbox else DEFAULT_BASE_URL)
        self._lang        = lang
        self._timeout     = timeout
        self._max_retries = max_retries

        if debug:
            logging.basicConfig(level=logging.DEBUG)
            logger.setLevel(logging.DEBUG)

        # Sous-ressources (style Stripe)
        self.conseil    = ConseilResource(self)
        self.produits   = ProduitsResource(self)
        self.traitement = TraitementResource(self)
        self.carnet     = CarnetResource(self)
        self.groupes    = GroupesResource(self)
        self.alertes    = AlertesResource(self)
        self.cultures   = CulturesResource(self)

        logger.debug("AgriSage SDK v%s initialisé — %s", SDK_VERSION, self._base_url)

    # ── Requête interne ───────────────────────────────────────────────────────

    def _request(
        self,
        method:  str,
        path:    str,
        *,
        query:   dict | None = None,
        body:    dict | None = None,
    ) -> ApiResponse:
        """
        Effectue une requête HTTP avec retry automatique.

        Retry déclenché sur : erreur réseau, 429, 5xx.
        Backoff exponentiel : 0.5s → 1s → 2s…
        """
        # Construire l'URL complète avec query string
        params = _clean({"lang": self._lang, **(query or {})})
        qs     = ("?" + urllib.parse.urlencode(params, doseq=True)) if params else ""
        url    = self._base_url + path + qs

        # Sérialiser le body JSON
        payload = json.dumps(body).encode("utf-8") if body else None

        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Accept":        "application/json",
            "User-Agent":    f"agrisage-python/{SDK_VERSION}",
        }
        if payload:
            headers["Content-Type"]   = "application/json"
            headers["Content-Length"] = str(len(payload))

        req = urllib.request.Request(
            url,
            data=payload,
            headers=headers,
            method=method.upper(),
        )

        attempt = 0
        while attempt <= self._max_retries:
            logger.debug("%s %s (tentative %d)", method.upper(), path, attempt + 1)
            try:
                with urllib.request.urlopen(req, timeout=self._timeout) as resp:
                    raw          = resp.read()
                    resp_headers = dict(resp.headers)
                    status_code  = resp.status
                    content_type = resp_headers.get("content-type", "")

                    rate_limit = RateLimit(
                        limit=_to_int(resp_headers.get("x-ratelimit-limit")),
                        remaining=_to_int(resp_headers.get("x-ratelimit-remaining")),
                        reset=resp_headers.get("x-ratelimit-reset"),
                    )
                    logger.debug("← %d · quota restant: %s", status_code, rate_limit.remaining)

                    # PDF : retourner les bytes bruts
                    if "application/pdf" in content_type:
                        return ApiResponse(data=raw, rate_limit=rate_limit, content_type="application/pdf")

                    data = json.loads(raw) if raw else None
                    return ApiResponse(data=data, rate_limit=rate_limit)

            except urllib.error.HTTPError as exc:
                raw_body = exc.read()
                status   = exc.code
                hdrs     = dict(exc.headers)

                should_retry = (status == 429 or status >= 500) and attempt < self._max_retries
                if should_retry:
                    delay = RETRY_DELAY_S * (2 ** attempt)
                    logger.debug("HTTP %d — retry dans %.1fs…", status, delay)
                    time.sleep(delay)
                    attempt += 1
                    continue

                _raise_for_status(status, raw_body, hdrs)

            except (urllib.error.URLError, TimeoutError, OSError) as exc:
                if attempt < self._max_retries:
                    delay = RETRY_DELAY_S * (2 ** attempt)
                    logger.debug("Erreur réseau — retry dans %.1fs…", delay)
                    time.sleep(delay)
                    attempt += 1
                    continue
                raise NetworkError(str(exc), exc) from exc


def _to_int(value: str | None) -> int | None:
    try:
        return int(value) if value is not None else None
    except (ValueError, TypeError):
        return None
