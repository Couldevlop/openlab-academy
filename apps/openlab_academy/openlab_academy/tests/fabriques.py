"""Fabriques de données de test (domaine et format YAML brut)."""
import copy

from openlab_academy.domain.parcours import Bloc, Module, Niveau, Parcours, Projet


def projet(titre="P", apres_module="01", niveau=Niveau.GUIDE, **autres) -> Projet:
    champs = dict(
        titre=titre, duree_h=12, niveau=niveau, contexte="c", objectifs=("o",), fonctionnalites=("f",),
        stack=("s",), criteres_acceptation=("a",), exigences_specifiques=(), livrables=("l",),
        apres_module=apres_module,
    )
    champs.update(autres)
    return Projet(**champs)


def parcours(**autres) -> Parcours:
    champs = dict(
        title="T", short_introduction="s", description="d", tags=("x",), card_gradient="Blue",
        blocs=(Bloc("B1", (Module("01", "M", "c", "l"),)),),
        portfolio=tuple(projet() for _ in range(10)),
        capstone=projet(titre="Cap", apres_module=None, niveau=Niveau.AUTONOME, duree_h=60),
    )
    champs.update(autres)
    return Parcours(**champs)


def _projet_brut(num="01"):
    return {
        "titre": "P", "apres_module": num, "duree_h": 12, "niveau": "guide",
        "contexte": "c", "objectifs": ["o"], "fonctionnalites": ["f"], "stack": ["s"],
        "criteres_acceptation": ["a"], "exigences_specifiques": [], "livrables": ["l"],
    }


def question_brute() -> dict:
    return {"question": "Q ?", "options": ["a", "b", "c"], "bonnes": [2], "explication": "Parce que b."}


def parcours_brut() -> dict:
    cap = _projet_brut()
    cap.pop("apres_module")
    cap.update(titre="Cap", duree_h=60, niveau="autonome")
    return copy.deepcopy({
        "title": "T", "short_introduction": "s", "description": "d", "tags": ["x"],
        "blocs": [{"title": "B1", "modules": [{"num": "01", "title": "M", "contenu": "c", "livrable": "l",
                                               "quiz": [question_brute() for _ in range(5)],
                                               "mise_en_situation": "Cas pratique"}]}],
        "portfolio": [_projet_brut() for _ in range(10)],
        "capstone": cap,
    })
