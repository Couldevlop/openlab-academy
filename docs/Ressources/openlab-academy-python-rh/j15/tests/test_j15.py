"""Journée 15 : la validation a lieu à la frontière, et nulle part ailleurs."""
import pathlib

import pytest

from rh.erreurs import DonneeInvalide
from rh.fichiers import charger_effectif

ENTETE = "matricule,nom,poste,date_embauche,salaire_fcfa\n"
CORRECT = ENTETE + "A001,Awa Kone,RH,2024-03-01,250000\n"
SALAIRE_NEGATIF = ENTETE + "A001,Awa Kone,RH,2024-03-01,-5\n"
DATE_FUTURE = ENTETE + "A001,Awa Kone,RH,2099-01-01,250000\n"
POSTE_VIDE = ENTETE + "A001,Awa Kone,,2024-03-01,250000\n"


def ecrire(tmp_path, texte):
    chemin = tmp_path / "effectif.csv"
    chemin.write_text(texte, encoding="utf-8")
    return chemin


def test_une_fiche_correcte_passe(tmp_path):
    fiches = charger_effectif(ecrire(tmp_path, CORRECT))
    assert fiches[0]["salaire_fcfa"] == 250000
    assert fiches[0]["date_embauche"] == "2024-03-01"


@pytest.mark.parametrize("contenu,champ", [(SALAIRE_NEGATIF, "salaire_fcfa"),
                                           (DATE_FUTURE, "date_embauche"),
                                           (POSTE_VIDE, "poste")])
def test_les_trois_refus_nomment_leur_champ(tmp_path, contenu, champ):
    with pytest.raises(DonneeInvalide) as erreur:
        charger_effectif(ecrire(tmp_path, contenu))
    assert champ in str(erreur.value)


def test_le_coeur_reste_sans_validation():
    source = pathlib.Path("rh/calculs.py").read_text(encoding="utf-8")
    assert "pydantic" not in source
    assert "isinstance" not in source
