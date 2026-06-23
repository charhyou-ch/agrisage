"""
Constantes du SDK AgriSage.

Usage :
    from agrisage import STADES, REGIONS

    conseil = client.conseil.generer(
        culture="tomate",
        stade=STADES.FLORAISON,
        region=REGIONS.SOUSS_MASSA,
    )
"""
from types import MappingProxyType


class _ConstNamespace:
    """Namespace immutable accessible par attribut ou clé."""

    def __init__(self, mapping: dict):
        object.__setattr__(self, "_data", MappingProxyType(mapping))
        for k, v in mapping.items():
            object.__setattr__(self, k, v)

    def __setattr__(self, name, value):
        raise AttributeError("Les constantes AgriSage sont immutables")

    def __getitem__(self, key):
        return self._data[key]

    def __contains__(self, item):
        return item in self._data.values()

    def __repr__(self):
        return f"{self.__class__.__name__}({dict(self._data)!r})"


STADES = _ConstNamespace({
    "GERMINATION":    "germination",
    "LEVEE":          "levee",
    "VEGETATION":     "vegetation",
    "FLORAISON":      "floraison",
    "FRUCTIFICATION": "fructification",
    "RECOLTE":        "recolte",
    "POST_RECOLTE":   "post-recolte",
})

REGIONS = _ConstNamespace({
    "SOUSS_MASSA":        "souss-massa",
    "GHARB_CHRARDA":      "gharb-chrarda",
    "MARRAKECH_SAFI":     "marrakech-safi",
    "FES_MEKNES":         "fes-meknes",
    "TANGER_TETOUAN":     "tanger-tetouan",
    "ORIENTAL":           "oriental",
    "RABAT_SALE_KENITRA": "rabat-sale-kenitra",
    "BENI_MELLAL":        "beni-mellal-khenifra",
    "DRAA_TAFILALET":     "draa-tafilalet",
    "LAAYOUNE":           "laayoune-sakia",
})

USAGES = _ConstNamespace({
    "FONGICIDE":    "fongicide",
    "INSECTICIDE":  "insecticide",
    "HERBICIDE":    "herbicide",
    "NEMATICIDE":   "nematicide",
    "ACARICIDE":    "acaricide",
    "MOLLUSCICIDE": "molluscicide",
})

ALERTES_TYPES = _ConstNamespace({
    "DAR_DEPASSE":     "DAR_DEPASSE",
    "PRODUIT_RETIRE":  "PRODUIT_RETIRE",
    "LMR_MODIFIEE":    "LMR_MODIFIEE",
    "ROTATION_REQUISE": "ROTATION_REQUISE",
    "ZNT_VIOLATION":   "ZNT_VIOLATION",
})
