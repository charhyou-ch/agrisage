"""
Tests unitaires du SDK AgriSage Python.
Aucune dépendance externe — lancez avec : python -m pytest tests/ ou python tests/test_sdk.py
"""

import sys
import unittest
import json
from unittest.mock import patch, MagicMock
from io import BytesIO

sys.path.insert(0, ".")

from agrisage import (
    AgriSageClient,
    AgriSageError,
    AuthenticationError,
    PlanLimitError,
    QuotaExceededError,
    NotFoundError,
    ValidationError,
    NetworkError,
    STADES,
    REGIONS,
    USAGES,
    ALERTES_TYPES,
)


def make_client(**kwargs):
    defaults = {"api_key": "as_test_abc123"}
    defaults.update(kwargs)
    return AgriSageClient(**defaults)


def mock_http_response(data: dict | bytes, status: int = 200, content_type: str = "application/json"):
    """Crée un mock urllib.request.urlopen retournant une réponse contrôlée."""
    if isinstance(data, dict):
        body = json.dumps(data).encode()
    else:
        body = data

    mock_resp = MagicMock()
    mock_resp.status = status
    mock_resp.read.return_value = body
    mock_resp.headers = {
        "content-type":        content_type,
        "x-ratelimit-limit":   "10000",
        "x-ratelimit-remaining": "9843",
        "x-ratelimit-reset":   "2025-04-01T00:00:00Z",
    }
    mock_resp.__enter__ = lambda s: s
    mock_resp.__exit__  = MagicMock(return_value=False)
    return mock_resp


def mock_http_error(status: int, body: dict):
    import urllib.error
    raw = json.dumps(body).encode()
    err = urllib.error.HTTPError(
        url="https://api.agrisage.ma/v1/conseil",
        code=status,
        msg="Error",
        hdrs=MagicMock(items=lambda: []),
        fp=BytesIO(raw),
    )
    err.read = lambda: raw
    err.headers = {"content-type": "application/json"}
    return err


class TestInit(unittest.TestCase):

    def test_manque_api_key(self):
        with self.assertRaises(AgriSageError) as ctx:
            AgriSageClient(api_key="")
        self.assertEqual(ctx.exception.code, "MISSING_API_KEY")

    def test_api_key_requis(self):
        with self.assertRaises(TypeError):
            AgriSageClient()

    def test_client_cree_ressources(self):
        c = make_client()
        self.assertIsNotNone(c.conseil)
        self.assertIsNotNone(c.produits)
        self.assertIsNotNone(c.traitement)
        self.assertIsNotNone(c.carnet)
        self.assertIsNotNone(c.groupes)
        self.assertIsNotNone(c.alertes)
        self.assertIsNotNone(c.cultures)

    def test_sandbox_url(self):
        c = make_client(sandbox=True)
        self.assertIn("sandbox", c._base_url)

    def test_base_url_personnalisee(self):
        c = make_client(base_url="http://localhost:4000")
        self.assertEqual(c._base_url, "http://localhost:4000")

    def test_lang_par_defaut_fr(self):
        c = make_client()
        self.assertEqual(c._lang, "fr")

    def test_lang_ar(self):
        c = make_client(lang="ar")
        self.assertEqual(c._lang, "ar")

    def test_timeout_par_defaut(self):
        c = make_client()
        self.assertEqual(c._timeout, 30)


class TestConseil(unittest.TestCase):

    def test_champs_requis_culture(self):
        c = make_client()
        with self.assertRaises(ValidationError) as ctx:
            c.conseil.generer(culture="", ravageur="botrytis", stade="floraison")
        self.assertIn("culture", str(ctx.exception))

    def test_champs_requis_ravageur(self):
        c = make_client()
        with self.assertRaises(ValidationError):
            c.conseil.generer(culture="tomate", ravageur="", stade="floraison")

    def test_champs_requis_stade(self):
        c = make_client()
        with self.assertRaises(ValidationError):
            c.conseil.generer(culture="tomate", ravageur="botrytis", stade="")

    @patch("urllib.request.urlopen")
    def test_generer_succes(self, mock_open):
        payload = {
            "conseil_id": "c_abc",
            "produit": "Switch 62.5 WG",
            "dar": 3,
            "groupe_frac": "9 + 12",
            "risque_abeilles": "faible",
            "alertes": [],
        }
        mock_open.return_value = mock_http_response(payload)
        c = make_client()
        resp = c.conseil.generer(culture="tomate", ravageur="botrytis", stade="floraison")
        self.assertEqual(resp.data["produit"], "Switch 62.5 WG")
        self.assertEqual(resp.data["dar"], 3)
        self.assertEqual(resp.rate_limit.remaining, 9843)

    @patch("urllib.request.urlopen")
    def test_generer_transmet_params_optionnels(self, mock_open):
        mock_open.return_value = mock_http_response({"conseil_id": "c_xyz"})
        c = make_client()

        captured_body = {}

        original_request = c._request
        def capture(*args, **kwargs):
            captured_body.update(kwargs.get("body", {}))
            return original_request(*args, **kwargs)

        c._request = capture
        try:
            c.conseil.generer(
                culture="tomate",
                ravageur="botrytis",
                stade="floraison",
                dar_max=7,
                globalgap=True,
                historique_frac=["1", "9"],
            )
        except Exception:
            pass

        self.assertEqual(captured_body.get("dar_max"), 7)
        self.assertTrue(captured_body.get("globalgap"))
        self.assertEqual(captured_body.get("historique_frac"), ["1", "9"])


class TestProduits(unittest.TestCase):

    def test_obtenir_id_vide(self):
        c = make_client()
        with self.assertRaises(ValidationError):
            c.produits.obtenir("")

    @patch("urllib.request.urlopen")
    def test_lister_succes(self, mock_open):
        payload = {"data": [{"id": "prod_001", "nom_commercial": "Switch 62.5 WG"}], "pagination": {}}
        mock_open.return_value = mock_http_response(payload)
        c = make_client()
        resp = c.produits.lister(culture="tomate", usage="fongicide")
        self.assertEqual(len(resp.data["data"]), 1)

    @patch("urllib.request.urlopen")
    def test_obtenir_succes(self, mock_open):
        payload = {"id": "prod_onssa_00412", "nom_commercial": "Switch 62.5 WG"}
        mock_open.return_value = mock_http_response(payload)
        c = make_client()
        resp = c.produits.obtenir("prod_onssa_00412")
        self.assertEqual(resp.data["id"], "prod_onssa_00412")


class TestTraitement(unittest.TestCase):

    def test_champs_requis(self):
        c = make_client()
        with self.assertRaises(ValidationError):
            c.traitement.enregistrer(
                parcelle_id="p1",
                produit_nom="",
                dose_appliquee={"valeur": 0.8, "unite": "kg/ha"},
                date_traitement="2025-03-15",
            )

    @patch("urllib.request.urlopen")
    def test_enregistrer_succes(self, mock_open):
        payload = {"traitement_id": "tr_abc", "statut": "enregistré", "dar_restant": 7, "alertes": []}
        mock_open.return_value = mock_http_response(payload, 201)
        c = make_client()
        resp = c.traitement.enregistrer(
            parcelle_id="parcelle_001",
            produit_nom="Switch 62.5 WG",
            dose_appliquee={"valeur": 0.8, "unite": "kg/ha"},
            date_traitement="2025-03-15",
        )
        self.assertEqual(resp.data["statut"], "enregistré")


class TestCarnet(unittest.TestCase):

    @patch("urllib.request.urlopen")
    def test_exporter_pdf_retourne_bytes(self, mock_open):
        mock_open.return_value = mock_http_response(b"%PDF-1.4 faux pdf", content_type="application/pdf")
        c = make_client()
        pdf = c.carnet.exporter_pdf(parcelle_id="p1")
        self.assertIsInstance(pdf, bytes)
        self.assertTrue(pdf.startswith(b"%PDF"))


class TestGroupes(unittest.TestCase):

    def test_type_requis(self):
        c = make_client()
        with self.assertRaises(ValidationError):
            c.groupes.lister(type="")

    @patch("urllib.request.urlopen")
    def test_raccourci_frac(self, mock_open):
        mock_open.return_value = mock_http_response({"data": [], "total": 0})
        c = make_client()

        captured = {}
        orig = c._request
        def cap(*args, **kwargs):
            captured.update(kwargs.get("query", {}))
            return orig(*args, **kwargs)
        c._request = cap

        try:
            c.groupes.frac(ma="cyprodinil")
        except Exception:
            pass
        self.assertEqual(captured.get("type"), "frac")
        self.assertEqual(captured.get("ma"), "cyprodinil")

    @patch("urllib.request.urlopen")
    def test_raccourci_irac(self, mock_open):
        mock_open.return_value = mock_http_response({"data": [], "total": 0})
        c = make_client()
        captured = {}
        orig = c._request
        def cap(*a, **kw):
            captured.update(kw.get("query", {}))
            return orig(*a, **kw)
        c._request = cap
        try:
            c.groupes.irac()
        except Exception:
            pass
        self.assertEqual(captured.get("type"), "irac")


class TestAlertes(unittest.TestCase):

    def test_marquer_lue_id_vide(self):
        c = make_client()
        with self.assertRaises(ValidationError):
            c.alertes.marquer_lue("")

    @patch("urllib.request.urlopen")
    def test_non_lues_passe_lue_false(self, mock_open):
        mock_open.return_value = mock_http_response({"data": [], "non_lues": 0, "pagination": {}})
        c = make_client()
        captured = {}
        orig = c._request
        def cap(*a, **kw):
            captured.update(kw.get("query", {}))
            return orig(*a, **kw)
        c._request = cap
        try:
            c.alertes.non_lues()
        except Exception:
            pass
        self.assertEqual(captured.get("lue"), "false")

    @patch("urllib.request.urlopen")
    def test_critiques_filtre_urgence(self, mock_open):
        mock_open.return_value = mock_http_response({"data": [], "non_lues": 0, "pagination": {}})
        c = make_client()
        captured = {}
        orig = c._request
        def cap(*a, **kw):
            captured.update(kw.get("query", {}))
            return orig(*a, **kw)
        c._request = cap
        try:
            c.alertes.critiques()
        except Exception:
            pass
        self.assertEqual(captured.get("urgence"), "critique")


class TestCultures(unittest.TestCase):

    @patch("urllib.request.urlopen")
    def test_rechercher_passe_q(self, mock_open):
        mock_open.return_value = mock_http_response({"data": [], "total": 0})
        c = make_client()
        captured = {}
        orig = c._request
        def cap(*a, **kw):
            captured.update(kw.get("query", {}))
            return orig(*a, **kw)
        c._request = cap
        try:
            c.cultures.rechercher("tom")
        except Exception:
            pass
        self.assertEqual(captured.get("q"), "tom")


class TestErreurs(unittest.TestCase):

    def test_hierarchy(self):
        self.assertTrue(issubclass(AuthenticationError, AgriSageError))
        self.assertTrue(issubclass(PlanLimitError,      AgriSageError))
        self.assertTrue(issubclass(QuotaExceededError,  AgriSageError))
        self.assertTrue(issubclass(NotFoundError,       AgriSageError))
        self.assertTrue(issubclass(ValidationError,     AgriSageError))
        self.assertTrue(issubclass(NetworkError,        AgriSageError))

    def test_auth_error_code(self):
        e = AuthenticationError("Non autorisé", "req_123")
        self.assertEqual(e.code, "UNAUTHORIZED")
        self.assertEqual(e.status_code, 401)
        self.assertEqual(e.request_id, "req_123")

    def test_quota_error_reset_at(self):
        e = QuotaExceededError("Quota dépassé", reset_at="2025-04-01T00:00:00Z")
        self.assertEqual(e.reset_at, "2025-04-01T00:00:00Z")
        self.assertEqual(e.status_code, 429)

    def test_plan_limit_suggestion(self):
        e = PlanLimitError("Plan insuffisant", suggestion="Passez au plan Pro")
        self.assertEqual(e.suggestion, "Passez au plan Pro")
        self.assertEqual(e.status_code, 403)

    @patch("urllib.request.urlopen")
    def test_leve_auth_error_sur_401(self, mock_open):
        import urllib.error
        err_body = {"error": {"code": "UNAUTHORIZED", "message": "Clé invalide", "request_id": "req_1"}}
        http_err = urllib.error.HTTPError("url", 401, "Unauthorized", {}, BytesIO(json.dumps(err_body).encode()))
        http_err.read = lambda: json.dumps(err_body).encode()
        http_err.headers = {}
        mock_open.side_effect = http_err

        c = make_client()
        with self.assertRaises(AuthenticationError):
            c.conseil.generer(culture="tomate", ravageur="botrytis", stade="floraison")

    @patch("urllib.request.urlopen")
    def test_leve_plan_limit_sur_403(self, mock_open):
        import urllib.error
        err_body = {"error": {"code": "PLAN_LIMIT", "message": "Plan insuffisant", "suggestion": "Passez au Pro"}}
        http_err = urllib.error.HTTPError("url", 403, "Forbidden", {}, BytesIO(json.dumps(err_body).encode()))
        http_err.read = lambda: json.dumps(err_body).encode()
        http_err.headers = {}
        mock_open.side_effect = http_err

        c = make_client()
        with self.assertRaises(PlanLimitError) as ctx:
            c.conseil.generer(culture="tomate", ravageur="botrytis", stade="floraison")
        self.assertEqual(ctx.exception.suggestion, "Passez au Pro")


class TestConstantes(unittest.TestCase):

    def test_stades_complets(self):
        for attr in ["GERMINATION", "LEVEE", "VEGETATION", "FLORAISON", "FRUCTIFICATION", "RECOLTE", "POST_RECOLTE"]:
            self.assertTrue(hasattr(STADES, attr), f"STADES.{attr} manquant")
        self.assertEqual(STADES.FLORAISON, "floraison")

    def test_regions_maroc(self):
        self.assertEqual(REGIONS.SOUSS_MASSA, "souss-massa")
        self.assertEqual(REGIONS.TANGER_TETOUAN, "tanger-tetouan")

    def test_usages(self):
        self.assertEqual(USAGES.FONGICIDE, "fongicide")
        self.assertEqual(USAGES.INSECTICIDE, "insecticide")

    def test_alertes_types(self):
        self.assertEqual(ALERTES_TYPES.DAR_DEPASSE, "DAR_DEPASSE")
        self.assertEqual(ALERTES_TYPES.LMR_MODIFIEE, "LMR_MODIFIEE")

    def test_constantes_immutables(self):
        with self.assertRaises(AttributeError):
            STADES.NOUVEAU = "nouveau"

    def test_contient_valeur(self):
        self.assertIn("floraison", STADES)
        self.assertIn("souss-massa", REGIONS)


if __name__ == "__main__":
    loader = unittest.TestLoader()
    suite  = loader.loadTestsFromModule(sys.modules[__name__])
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    sys.exit(0 if result.wasSuccessful() else 1)
