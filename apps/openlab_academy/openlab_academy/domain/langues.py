"""Langues de la plateforme : liste blanche stricte, sans Frappe. Le français est la langue par défaut ; l'en-tête
Accept-Language n'est jamais suivi."""

LANGUES: tuple[str, ...] = ("fr", "en")
DEFAUT = "fr"
_LOCALES = {"fr": "fr-FR", "en": "en-GB"}


def normaliser(valeur: object) -> str | None:
    """La langue si elle figure exactement dans la liste blanche, sinon None (casse, espaces, chemins : refusés)."""
    return valeur if isinstance(valeur, str) and valeur in LANGUES else None


def locale(langue: str) -> str:
    return _LOCALES[langue]


def resoudre(parametre: object, cookie: object, compte: object, connecte: bool, courante: object) -> str:
    """Langue d'une requête : `_lang` valide d'abord ; un `_lang` hors liste est ignoré. Visiteur : cookie valide, sinon
    défaut. Compte connecté : sa langue (celle déjà résolue par Frappe, si valide, quand rien n'est demandé)."""
    if (demandee := normaliser(parametre)):
        return demandee
    if not connecte:
        return normaliser(cookie) or DEFAUT
    return normaliser(compte if parametre else courante) or normaliser(compte) or DEFAUT
