"""Journée 13 : trois pannes, trois messages utiles."""
import pathlib

import pytest

from rh.erreurs import DonneeInvalide
from rh.fichiers import charger_effectif

COMPLET = """matricule,nom,poste,date_embauche,salaire_fcfa
A001,Awa Kone,RH,2024-03-01,250000
"""
SANS_SALAIRE = """matricule,nom,poste,date_embauche
A001,Awa Kone,RH,2024-03-01
"""
SALAIRE_ILLISIBLE = """matricule,nom,poste,date_embauche,salaire_fcfa
A001,Awa Kone,RH,2024-03-01,250 000
"""


def ecrire(tmp_path, texte):
    chemin = tmp_path / "effectif.csv"
    chemin.write_text(texte, encoding="utf-8")
    return chemin


def test_un_fichier_complet_se_charge(tmp_path):
    assert len(charger_effectif(ecrire(tmp_path, COMPLET))) == 1


def test_un_fichier_absent_leve_une_erreur_metier(tmp_path):
    with pytest.raises(DonneeInvalide) as erreur:
        charger_effectif(tmp_path / "absent.csv")
    assert "absent.csv" in str(erreur.value)


def test_une_colonne_manquante_est_nommee(tmp_path):
    with pytest.raises(DonneeInvalide) as erreur:
        charger_effectif(ecrire(tmp_path, SANS_SALAIRE))
    assert "salaire_fcfa" in str(erreur.value)


def test_un_salaire_illisible_cite_sa_ligne(tmp_path):
    with pytest.raises(DonneeInvalide) as erreur:
        charger_effectif(ecrire(tmp_path, SALAIRE_ILLISIBLE))
    assert "2" in str(erreur.value)


def test_la_cause_technique_est_conservee(tmp_path):
    with pytest.raises(DonneeInvalide) as erreur:
        charger_effectif(ecrire(tmp_path, SALAIRE_ILLISIBLE))
    assert erreur.value.__cause__ is not None


def test_aucun_except_nu_dans_le_projet():
    for source in pathlib.Path("rh").glob("*.py"):
        texte = source.read_text(encoding="utf-8")
        assert "except:" not in texte, source
