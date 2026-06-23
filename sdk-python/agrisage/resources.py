"""
Ressources de l'API AgriSage.

Chaque ressource correspond à un groupe d'endpoints.
Les méthodes acceptent des paramètres Python (snake_case)
et les convertissent en snake_case JSON pour l'API.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from .exceptions import ValidationError

if TYPE_CHECKING:
    from .client import AgriSageClient, ApiResponse


# ── helpers ───────────────────────────────────────────────────────────────────

def _clean(d: dict) -> dict:
    return {k: v for k, v in d.items() if v is not None}


def _require(params: dict, fields: list[str], method: str) -> None:
    for f in fields:
        val = params.get(f)
        if val is None or val == "":
            raise ValidationError(
                f"Le paramètre '{f}' est requis pour {method}",
                suggestion=f"Docs : https://docs.agrisage.ma#{method.replace('.', '-')}",
            )


# ── Conseil ───────────────────────────────────────────────────────────────────

class ConseilResource:
    """Génération de conseils phytosanitaires."""

    def __init__(self, client: "AgriSageClient"):
        self._client = client

    def generer(
        self,
        *,
        culture:           str,
        ravageur:          str,
        stade:             str,
        region:            str | None  = None,
        dar_max:           int | None  = None,
        globalgap:         bool | None = None,
        export_ue:         bool | None = None,
        historique_frac:   list[str] | None = None,
        historique_irac:   list[str] | None = None,
        nb_alternatives:   int | None  = None,
        lang:              str | None  = None,
    ) -> "ApiResponse":
        """
        Génère un conseil phytosanitaire validé.

        Args:
            culture:         Nom de la culture (ex: ``"tomate"``)
            ravageur:        Organisme nuisible (ex: ``"botrytis"``)
            stade:           Stade phénologique. Utilisez ``STADES.FLORAISON`` etc.
            region:          Code région marocaine. Utilisez ``REGIONS.SOUSS_MASSA`` etc.
            dar_max:         DAR maximum acceptable en jours.
            globalgap:       Si ``True``, filtre sur la conformité GlobalGAP v6.
            export_ue:       Applique les LMR UE 396/2005 (plan Pro+).
            historique_frac: Groupes FRAC déjà utilisés ce cycle.
            historique_irac: Groupes IRAC déjà utilisés ce cycle.
            nb_alternatives: Nombre de produits alternatifs (0–5, défaut 2).
            lang:            ``'fr'`` ou ``'ar'``.

        Returns:
            :class:`~agrisage.client.ApiResponse` dont ``data`` est un :class:`dict`
            contenant ``produit``, ``dose``, ``dar``, ``groupe_frac``, ``alertes``, etc.

        Raises:
            :class:`~agrisage.exceptions.ValidationError`: champ requis manquant.
            :class:`~agrisage.exceptions.PlanLimitError`: ``export_ue`` nécessite plan Pro+.
        """
        _require({"culture": culture, "ravageur": ravageur, "stade": stade},
                 ["culture", "ravageur", "stade"], "conseil.generer")

        body = _clean({
            "culture":           culture,
            "ravageur":          ravageur,
            "stade":             stade,
            "region":            region,
            "dar_max":           dar_max,
            "globalgap":         globalgap,
            "export_ue":         export_ue,
            "historique_frac":   historique_frac,
            "historique_irac":   historique_irac,
            "nb_alternatives":   nb_alternatives,
            "lang":              lang or self._client._lang,
        })
        return self._client._request("POST", "/conseil", body=body)


# ── Produits ──────────────────────────────────────────────────────────────────

class ProduitsResource:
    """Index phytosanitaire ONSSA."""

    def __init__(self, client: "AgriSageClient"):
        self._client = client

    def lister(
        self,
        *,
        culture:     str | None = None,
        usage:       str | None = None,
        ma:          str | None = None,
        statut:      str | None = None,
        groupe_frac: str | None = None,
        groupe_irac: str | None = None,
        page:        int | None = None,
        lang:        str | None = None,
    ) -> "ApiResponse":
        """
        Liste les produits ONSSA avec filtres.

        Args:
            culture:     Filtre par culture homologuée.
            usage:       Type — ``'fongicide'``, ``'insecticide'``, ``'herbicide'``…
            ma:          Recherche par matière active (correspondance partielle).
            statut:      ``'homologue'`` (défaut), ``'retire'`` ou ``'tous'``.
            groupe_frac: Filtre par numéro de groupe FRAC.
            groupe_irac: Filtre par numéro de groupe IRAC.
            page:        Numéro de page (50 résultats par page).

        Returns:
            ``data`` → ``{"data": [ProduitONSSA, ...], "pagination": {...}}``
        """
        return self._client._request("GET", "/produits", query=_clean({
            "culture":     culture,
            "usage":       usage,
            "ma":          ma,
            "statut":      statut,
            "groupe_frac": groupe_frac,
            "groupe_irac": groupe_irac,
            "page":        page,
            "lang":        lang,
        }))

    def obtenir(self, id: str, *, lang: str | None = None) -> "ApiResponse":
        """
        Détail complet d'un produit ONSSA.

        Args:
            id:   Identifiant du produit (ex: ``"prod_onssa_00412"``).
            lang: ``'fr'`` ou ``'ar'``.

        Returns:
            ``data`` → dict ``ProduitONSSA``

        Raises:
            :class:`~agrisage.exceptions.NotFoundError`: produit introuvable.
        """
        if not id:
            raise ValidationError("'id' est requis pour produits.obtenir")
        return self._client._request(
            "GET", f"/produits/{urllib_quote(id)}", query=_clean({"lang": lang})
        )


# ── Traitement ────────────────────────────────────────────────────────────────

class TraitementResource:
    """Carnet de traitements — enregistrement (plan Pro+)."""

    def __init__(self, client: "AgriSageClient"):
        self._client = client

    def enregistrer(
        self,
        *,
        parcelle_id:          str,
        produit_nom:          str,
        dose_appliquee:       dict,
        date_traitement:      str,
        conseil_id:           str | None   = None,
        culture:              str | None   = None,
        numero_amm:           str | None   = None,
        surface_traitee:      float | None = None,
        date_recolte_prevue:  str | None   = None,
        operateur:            str | None   = None,
        epi_portes:           list[str] | None = None,
        conditions_meteo:     dict | None  = None,
        notes:                str | None   = None,
    ) -> "ApiResponse":
        """
        Enregistre un traitement dans le carnet (plan Pro+).

        Args:
            parcelle_id:         Identifiant de la parcelle dans votre système.
            produit_nom:         Nom commercial du produit utilisé.
            dose_appliquee:      Dict ``{"valeur": float, "unite": str}``.
            date_traitement:     Date ISO 8601 (ex: ``"2025-03-15"``).
            conseil_id:          ID du conseil AgriSage associé (optionnel).
            culture:             Culture traitée.
            numero_amm:          Numéro AMM ONSSA du produit.
            surface_traitee:     Surface en hectares.
            date_recolte_prevue: Déclenche une alerte si DAR risque d'être dépassé.
            operateur:           Nom de l'opérateur.
            epi_portes:          Liste des EPI portés (ex: ``["gants nitrile", "FFP2"]``).
            conditions_meteo:    Dict optionnel avec ``temperature_c``, ``vent_kmh``,
                                 ``hygrometrie_pct``.
            notes:               Observations libres.

        Returns:
            ``data`` → ``{"traitement_id": str, "statut": str, "dar_restant": int, "alertes": [...]}``
        """
        _require(
            {
                "parcelle_id":     parcelle_id,
                "produit_nom":     produit_nom,
                "dose_appliquee":  dose_appliquee,
                "date_traitement": date_traitement,
            },
            ["parcelle_id", "produit_nom", "dose_appliquee", "date_traitement"],
            "traitement.enregistrer",
        )
        body = _clean({
            "conseil_id":          conseil_id,
            "parcelle_id":         parcelle_id,
            "culture":             culture,
            "produit_nom":         produit_nom,
            "numero_amm":          numero_amm,
            "dose_appliquee":      dose_appliquee,
            "surface_traitee":     surface_traitee,
            "date_traitement":     date_traitement,
            "date_recolte_prevue": date_recolte_prevue,
            "operateur":           operateur,
            "epi_portes":          epi_portes,
            "conditions_meteo":    conditions_meteo,
            "notes":               notes,
        })
        return self._client._request("POST", "/traitement", body=body)


# ── Carnet ────────────────────────────────────────────────────────────────────

class CarnetResource:
    """Consultation et export du carnet de traitements (plan Pro+)."""

    def __init__(self, client: "AgriSageClient"):
        self._client = client

    def obtenir(
        self,
        *,
        parcelle_id: str | None  = None,
        du:          str | None  = None,
        au:          str | None  = None,
        format:      str | None  = None,
        page:        int | None  = None,
    ) -> "ApiResponse":
        """
        Consulte l'historique des traitements.

        Args:
            parcelle_id: Filtre par identifiant de parcelle.
            du:          Date de début ISO 8601.
            au:          Date de fin ISO 8601.
            format:      ``'json'`` (défaut) ou ``'pdf'``.
            page:        Numéro de page.

        Returns:
            ``data`` → liste de traitements (JSON) ou ``bytes`` (PDF).
        """
        return self._client._request("GET", "/carnet", query=_clean({
            "parcelle_id": parcelle_id,
            "du":          du,
            "au":          au,
            "format":      format,
            "page":        page,
        }))

    def exporter_pdf(
        self,
        *,
        parcelle_id: str | None = None,
        du:          str | None = None,
        au:          str | None = None,
    ) -> bytes:
        """
        Exporte le carnet au format PDF GlobalGAP v6.

        Returns:
            Contenu PDF en ``bytes``, prêt à écrire sur disque.

        Example::

            pdf = client.carnet.exporter_pdf(
                parcelle_id="parcelle_nord_003",
                du="2025-01-01",
                au="2025-12-31",
            )
            with open("audit_globalgap_2025.pdf", "wb") as f:
                f.write(pdf)
        """
        response = self.obtenir(parcelle_id=parcelle_id, du=du, au=au, format="pdf")
        return response.data


# ── Groupes ───────────────────────────────────────────────────────────────────

class GroupesResource:
    """Référentiels IRAC / FRAC / HRAC."""

    def __init__(self, client: "AgriSageClient"):
        self._client = client

    def lister(
        self,
        *,
        type:   str,
        groupe: str | None = None,
        ma:     str | None = None,
        risque: str | None = None,
        lang:   str | None = None,
    ) -> "ApiResponse":
        """
        Liste les groupes de résistance.

        Args:
            type:   Classification — ``'irac'``, ``'frac'`` ou ``'hrac'`` (requis).
            groupe: Filtre par numéro de groupe (ex: ``"9"``).
            ma:     Recherche par matière active (ex: ``"cyprodinil"``).
            risque: ``'faible'``, ``'modéré'``, ``'élevé'`` ou ``'très élevé'``.
            lang:   ``'fr'`` ou ``'ar'``.

        Returns:
            ``data`` → ``{"data": [GroupeResistance, ...], "total": int}``
        """
        _require({"type": type}, ["type"], "groupes.lister")
        return self._client._request("GET", "/groupes", query=_clean({
            "type":   type,
            "groupe": groupe,
            "ma":     ma,
            "risque": risque,
            "lang":   lang,
        }))

    def irac(self, **kwargs: Any) -> "ApiResponse":
        """Raccourci — liste les groupes IRAC (insecticides)."""
        return self.lister(type="irac", **kwargs)

    def frac(self, **kwargs: Any) -> "ApiResponse":
        """Raccourci — liste les groupes FRAC (fongicides)."""
        return self.lister(type="frac", **kwargs)

    def hrac(self, **kwargs: Any) -> "ApiResponse":
        """Raccourci — liste les groupes HRAC (herbicides)."""
        return self.lister(type="hrac", **kwargs)


# ── Alertes ───────────────────────────────────────────────────────────────────

class AlertesResource:
    """Alertes DAR, retraits ONSSA, LMR modifiées."""

    def __init__(self, client: "AgriSageClient"):
        self._client = client

    def lister(
        self,
        *,
        type:        str | None  = None,
        urgence:     str | None  = None,
        lue:         bool | None = None,
        parcelle_id: str | None  = None,
        page:        int | None  = None,
    ) -> "ApiResponse":
        """
        Consulte les alertes actives.

        Args:
            type:        Filtre par type — ``'DAR_DEPASSE'``, ``'PRODUIT_RETIRE'``, etc.
            urgence:     ``'critique'``, ``'élevée'``, ``'modérée'``, ``'information'``.
            lue:         ``False`` = uniquement les non lues.
            parcelle_id: Filtre par parcelle.
            page:        Numéro de page.

        Returns:
            ``data`` → ``{"data": [Alerte, ...], "non_lues": int, "pagination": {...}}``
        """
        query = _clean({"type": type, "urgence": urgence, "parcelle_id": parcelle_id, "page": page})
        if lue is not None:
            query["lue"] = "true" if lue else "false"
        return self._client._request("GET", "/alertes", query=query)

    def marquer_lue(self, id: str) -> "ApiResponse":
        """
        Marque une alerte comme lue.

        Args:
            id: Identifiant de l'alerte (ex: ``"al_7d4e2f1b"``).

        Returns:
            ``data`` → ``{"alerte_id": str, "lue": True}``
        """
        if not id:
            raise ValidationError("'id' est requis pour alertes.marquer_lue")
        return self._client._request("PATCH", f"/alertes/{urllib_quote(id)}/lue")

    def non_lues(self, **kwargs: Any) -> "ApiResponse":
        """Raccourci — alertes non lues uniquement."""
        return self.lister(lue=False, **kwargs)

    def critiques(self, **kwargs: Any) -> "ApiResponse":
        """Raccourci — alertes d'urgence critique uniquement."""
        return self.lister(urgence="critique", **kwargs)


# ── Cultures ──────────────────────────────────────────────────────────────────

class CulturesResource:
    """Référentiel des cultures disponibles dans l'index ONSSA."""

    def __init__(self, client: "AgriSageClient"):
        self._client = client

    def lister(
        self,
        *,
        q:    str | None = None,
        lang: str | None = None,
    ) -> "ApiResponse":
        """
        Liste toutes les cultures indexées.

        Args:
            q:    Recherche par nom (correspondance partielle, ex: ``"tom"``).
            lang: ``'fr'`` ou ``'ar'``.

        Returns:
            ``data`` → ``{"data": [Culture, ...], "total": int}``
        """
        return self._client._request("GET", "/cultures", query=_clean({"q": q, "lang": lang}))

    def rechercher(self, terme: str, *, lang: str | None = None) -> "ApiResponse":
        """
        Recherche rapide par nom de culture.

        Args:
            terme: Terme à rechercher (ex: ``"tom"`` → tomate, tomate cerise…).
            lang:  ``'fr'`` ou ``'ar'``.
        """
        return self.lister(q=terme, lang=lang)


# ── Util interne ──────────────────────────────────────────────────────────────

def urllib_quote(s: str) -> str:
    import urllib.parse
    return urllib.parse.quote(str(s), safe="")
