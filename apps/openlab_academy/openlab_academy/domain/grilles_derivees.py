"""Domaine : grille par défaut d'un exercice, dérivée des réglages quand le parcours n'en fournit pas.

Mise en situation et livrable : grille générique (réglages de l'évaluation).
Projet et capstone : barème des réglages ; les critères d'acceptation du projet alimentent la rubrique
« Fonctionnel », les exigences (communes puis spécifiques) la rubrique « Qualité & tests ». Si une rubrique
manque au barème, les contrôles passent au premier critère (acceptation) ou au dernier (qualité).
"""
from openlab_academy.domain.grille import Grille, grille_generique, grille_projet
from openlab_academy.domain.parcours import Projet
from openlab_academy.domain.reglages import Reglages
from openlab_academy.domain.reglages_evaluation import ReglagesEvaluation, TypeExercice

RUBRIQUE_ACCEPTATION = "Fonctionnel"
RUBRIQUE_QUALITE = "Qualité & tests"


def grille_par_defaut(type_: TypeExercice, projet: Projet | None, reglages: Reglages,
                      evaluation: ReglagesEvaluation) -> Grille:
    if type_ in (TypeExercice.MISE_EN_SITUATION, TypeExercice.LIVRABLE):
        return grille_generique(evaluation.grille_generique, evaluation.niveaux_generiques)
    if projet is None:
        raise ValueError(f"un exercice de type « {type_.value} » exige son projet")
    noms = [c.nom for c in reglages.bareme]
    acceptation = RUBRIQUE_ACCEPTATION if RUBRIQUE_ACCEPTATION in noms else noms[0]
    qualite = RUBRIQUE_QUALITE if RUBRIQUE_QUALITE in noms else noms[-1]
    controles: dict[str, tuple[str, ...]] = {}
    for rubrique, textes in ((acceptation, projet.criteres_acceptation),
                             (qualite, reglages.exigences_communes + projet.exigences_specifiques)):
        controles[rubrique] = controles.get(rubrique, ()) + tuple(textes)
    return grille_projet(reglages.bareme, controles, evaluation.niveaux_generiques)
