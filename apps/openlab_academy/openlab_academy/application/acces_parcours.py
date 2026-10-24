"""Accès à un parcours : bloqué tant que son dossier de paiement est en retard. Rien n'est stocké, tout se calcule
à la demande depuis le dossier ; sans dossier (parcours gratuit, formateur) ou pour un rôle exempté, jamais bloqué."""
from datetime import date
from typing import Protocol
from urllib.parse import quote

from openlab_academy.application.ports_paiement import DossierEnregistre
from openlab_academy.domain.dossier_paiement import bloque

PREFIXE_PAIEMENT = "/espace/paiement/"


class DossiersApprenant(Protocol):
    def charger(self, apprenant: str, cours: str) -> DossierEnregistre | None: ...
    def cours_de(self, apprenant: str) -> tuple[str, ...]: ...


def parcours_bloque(depot: DossiersApprenant, apprenant: str, cours: str, aujourd_hui: date,
                    exempte: bool = False) -> bool:
    if exempte:
        return False
    d = depot.charger(apprenant, cours)
    return d is not None and bloque(d.dossier, aujourd_hui)


def cours_bloques(depot: DossiersApprenant, apprenant: str, aujourd_hui: date,
                  exempte: bool = False) -> tuple[str, ...]:
    """Parcours bloqués de l'apprenant (pour filtrer les listes)."""
    if exempte:
        return ()
    return tuple(c for c in depot.cours_de(apprenant) if parcours_bloque(depot, apprenant, c, aujourd_hui))


def redirection_paiement(cours: str) -> str:
    """Page de paiement du parcours ; le nom est encodé en un seul segment, il ne peut pas sortir du préfixe."""
    return PREFIXE_PAIEMENT + quote(cours, safe="")
