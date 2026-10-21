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


def prochain_recours(actuel: str, suppleants: tuple[str, ...], responsable: str) -> str:
    """Après le titulaire (`actuel` vide) puis chaque recours : les suppléants dans l'ordre, puis le responsable
    pédagogique ; vide quand l'escalade est épuisée. Un recours retiré de l'équipe entre-temps passe la main au
    responsable."""
    recours = [p for p in dict.fromkeys((*suppleants, responsable)) if p]
    if not actuel:
        return recours[0] if recours else ""
    if actuel in recours:
        suite = recours[recours.index(actuel) + 1:]
        return suite[0] if suite else ""
    return responsable
