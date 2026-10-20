"""Domaine : échéances des étapes d'évaluation. Rien ne bloque : à expiration, l'action réglée s'applique."""
from dataclasses import dataclass
from datetime import datetime, timedelta

from openlab_academy.domain.reglages_evaluation import Chaine, Etape, Expiration


@dataclass(frozen=True)
class Echeance:
    etape: Etape
    depuis: datetime  # début de l'étape


def action_due(echeance: Echeance, chaine: Chaine, maintenant: datetime) -> Expiration | None:
    config = chaine.config(echeance.etape)
    if maintenant >= echeance.depuis + timedelta(hours=config.delai_heures):
        return config.expiration
    return None


def escalade(etape: Etape, suppleant: str | None, responsable: str) -> str:
    """Destinataire d'une escalade : le suppléant de l'étape, sinon le responsable pédagogique."""
    return suppleant or responsable
