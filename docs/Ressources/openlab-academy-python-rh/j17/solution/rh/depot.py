"""Le dépôt : il garde les fiches, et ne sait rien du HTTP."""
from rh.erreurs import DejaPris, Introuvable


class DepotEffectif:
    """Un effectif gardé en mémoire, interrogeable par matricule."""

    def __init__(self, fiches=()):
        self._fiches = {}
        for fiche in fiches:
            self.ajouter(fiche)

    def lister(self):
        """Rend toutes les fiches, triées par matricule."""
        return [dict(self._fiches[matricule]) for matricule in sorted(self._fiches)]

    def lire(self, matricule):
        """Rend la fiche demandée, ou lève Introuvable."""
        if matricule not in self._fiches:
            raise Introuvable(f"Aucun salarié au matricule {matricule}.")
        return dict(self._fiches[matricule])

    def ajouter(self, fiche):
        """Ajoute une fiche, ou lève DejaPris si le matricule existe déjà."""
        matricule = fiche["matricule"]
        if matricule in self._fiches:
            raise DejaPris(f"Le matricule {matricule} est déjà attribué.")
        self._fiches[matricule] = dict(fiche)
        return dict(fiche)
