"""Cas d'usage côté apprenant : retour sur sa copie, auto-évaluation, relectures confiées.

L'apprenant ne voit que ce qui le concerne : sa copie et ses relectures. Une relecture ne nomme jamais l'auteur de
la copie relue ; la proposition IA n'est jamais montrée avant la publication du formateur ; la note reste masquée
tant que l'apprenant n'a pas terminé ses relectures (sauf dispense), comme sur Coursera.
"""
from collections.abc import Callable
from typing import Protocol

from openlab_academy.application.corriger import (
    AccesRefuse, CorrectionRefusee, GENERAL, note_masquee, synthese, valider_niveaux)
from openlab_academy.application.pairs import DepotRelectures, Relecture, StatutRelecture
from openlab_academy.application.soumettre_copie import Contenu, Exercice
from openlab_academy.domain.copie import Copie, Proposition, Statut
from openlab_academy.domain.grille import Grille
from openlab_academy.domain.reglages_evaluation import Chaine

EN_COURS = "Votre copie est en cours de correction."
MASQUEE = "Votre note sera visible dès que vous aurez terminé vos relectures."
PROVISOIRE = "Note provisoire, en attente de validation par le formateur."
VISIBLES = (StatutRelecture.A_FAIRE, StatutRelecture.FAITE)


class DepotRetours(Protocol):
    def copie(self, copie_id: str) -> Copie: ...
    def grille(self, copie_id: str) -> Grille: ...
    def propositions(self, copie_id: str) -> list[Proposition]: ...
    def resultat(self, copie_id: str) -> tuple[float, int, bool]: ...
    def dispensee(self, copie_id: str) -> bool: ...


class ConsulterRetour:
    def __init__(self, depot: DepotRetours, relectures: DepotRelectures, chaine: Callable[[Copie], Chaine]):
        self._depot = depot
        self._relectures = relectures
        self._chaine = chaine

    def executer(self, apprenant: str, copie_id: str) -> dict:
        copie = self._depot.copie(copie_id)
        if copie.apprenant != apprenant:
            raise AccesRefuse("cette copie n'est pas la vôtre")
        base = {"copie": copie_id, "exercice": copie.exercice, "statut": copie.statut.value,
                "provisoire": copie.statut == Statut.PROVISOIRE, "masquee": False, "note": None, "note_sur": None,
                "reussite": None, "criteres": [], "commentaire_general": "", "message": EN_COURS}
        if copie.statut not in (Statut.PUBLIEE, Statut.PROVISOIRE):
            return base
        chaine = self._chaine(copie)
        if note_masquee(chaine, copie, self._depot.dispensee(copie_id),
                        self._relectures.relectures(copie.exercice, copie.cohorte)):
            return {**base, "masquee": True, "message": MASQUEE}
        grille = self._depot.grille(copie_id)
        s = synthese(self._depot.propositions(copie_id))
        if copie.statut == Statut.PUBLIEE:
            note, note_sur, reussite = self._depot.resultat(copie_id)
            niveaux, message = s.formateur.niveaux if s.formateur else {}, ""
        else:
            niveaux, note_sur, message = s.niveaux_provisoires() or {}, chaine.note_sur, PROVISOIRE
            note = s.note_provisoire(grille, note_sur)
            reussite = None if note is None else note >= chaine.seuil_reussite
        commentaires = s.formateur.commentaires if s.formateur else {}
        criteres = []
        for c in grille.criteres:
            niveau = niveaux.get(c.code)
            criteres.append({
                "code": c.code, "libelle": c.libelle, "poids": c.poids, "niveau": niveau,
                "niveau_libelle": c.niveaux[niveau].libelle if niveau is not None else "",
                "auto_evaluation": s.auto_evaluation.niveaux.get(c.code) if s.auto_evaluation else None,
                "commentaire": commentaires.get(c.code, ""),
                "pairs": [p.commentaires[c.code] for p in s.pairs if p.commentaires.get(c.code)]})
        return {**base, "note": note, "note_sur": note_sur, "reussite": reussite, "criteres": criteres,
                "commentaire_general": commentaires.get(GENERAL, ""), "message": message}


class DepotAutoEvaluation(Protocol):
    def exercice(self, exercice: str) -> Exercice | None: ...
    def inscrit(self, apprenant: str, exercice: str) -> bool: ...
    def derniere_copie(self, apprenant: str, exercice: str) -> Copie | None: ...
    def auto_evaluation(self, apprenant: str, exercice: str) -> dict[str, int] | None: ...
    def enregistrer_auto_evaluation(self, apprenant: str, exercice: str, niveaux: dict[str, int]) -> None: ...


class AutoEvaluer:
    """Avant le rendu, l'apprenant se positionne sur la grille ; après un renvoi, il peut se repositionner."""

    def __init__(self, depot: DepotAutoEvaluation):
        self._depot = depot

    def _exercice(self, apprenant: str, exercice: str) -> Exercice:
        trouve = self._depot.exercice(exercice)
        if trouve is None or not self._depot.inscrit(apprenant, exercice):
            raise AccesRefuse("exercice hors de vos cours")
        return trouve

    def _modifiable(self, apprenant: str, exercice: str) -> bool:
        copie = self._depot.derniere_copie(apprenant, exercice)
        return copie is None or copie.statut == Statut.RENVOYEE

    def consulter(self, apprenant: str, exercice: str) -> dict:
        trouve = self._exercice(apprenant, exercice)
        return {"exercice": exercice, "grille": trouve.grille.vers_dict(),
                "niveaux": self._depot.auto_evaluation(apprenant, exercice),
                "modifiable": self._modifiable(apprenant, exercice)}

    def enregistrer(self, apprenant: str, exercice: str, niveaux) -> None:
        trouve = self._exercice(apprenant, exercice)
        niveaux = valider_niveaux(trouve.grille, niveaux)
        if not self._modifiable(apprenant, exercice):
            raise CorrectionRefusee("auto-évaluation close : votre copie est déjà rendue")
        self._depot.enregistrer_auto_evaluation(apprenant, exercice, niveaux)


class DepotRelecturesVues(Protocol):
    def copie(self, copie_id: str) -> Copie: ...
    def grille(self, copie_id: str) -> Grille: ...
    def contenu(self, copie_id: str) -> Contenu: ...
    def texte_lisible(self, copie_id: str) -> str: ...
    def consigne(self, exercice: str) -> str: ...


class DepotRelecturesDuRelecteur(DepotRelectures, Protocol):
    def relectures_du_relecteur(self, relecteur: str) -> list[Relecture]: ...


class ConsulterRelectures:
    """Relectures confiées à un apprenant, sans rien qui identifie l'auteur (ni nom, ni e-mail, ni copie, ni lien)."""

    def __init__(self, depot: DepotRelecturesVues, relectures: DepotRelecturesDuRelecteur):
        self._depot = depot
        self._relectures = relectures

    def _miennes(self, relecteur: str) -> list[tuple[Relecture, str, int, int]]:
        visibles = [(r, self._depot.copie(r.copie).exercice) for r in self._relectures.relectures_du_relecteur(relecteur)
                    if r.statut in VISIBLES]
        totaux: dict[str, int] = {}
        rangs = []
        for r, exercice in visibles:
            totaux[exercice] = totaux.get(exercice, 0) + 1
            rangs.append((r, exercice, totaux[exercice]))
        return [(r, exercice, rang, totaux[exercice]) for r, exercice, rang in rangs]

    def mes_relectures(self, relecteur: str) -> list[dict]:
        return [{"relecture": r.id, "exercice": exercice, "statut": r.statut.value, "echeance": r.echeance,
                 "rang": rang, "total": total} for r, exercice, rang, total in self._miennes(relecteur)]

    def relecture(self, relecteur: str, relecture_id: str) -> dict:
        trouvee = next((m for m in self._miennes(relecteur) if m[0].id == relecture_id), None)
        if trouvee is None:
            raise AccesRefuse("relecture non attribuée")
        r, exercice, rang, total = trouvee
        return {"relecture": r.id, "exercice": exercice, "consigne": self._depot.consigne(exercice),
                "contenu": self._depot.texte_lisible(r.copie), "grille": self._depot.grille(r.copie).vers_dict(),
                "statut": r.statut.value, "echeance": r.echeance, "rang": rang, "total": total,
                "anonymat_garanti": not self._depot.contenu(r.copie).rendu_par_lien}
