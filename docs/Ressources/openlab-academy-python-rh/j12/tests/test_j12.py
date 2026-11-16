"""Journée 12 : lire un CSV sans casser les accents, et sans salir le cœur."""
import pathlib

from rh.fichiers import charger_effectif

CSV = """matricule,nom,poste,date_embauche,salaire_fcfa
A001,Awa Kone,RH,2024-03-01,250000
A003,Céline N'Guessan,RH,2022-06-30,420000
"""


def fichier(tmp_path):
    chemin = tmp_path / "effectif.csv"
    chemin.write_text(CSV, encoding="utf-8")
    return chemin


def test_toutes_les_fiches_sont_lues(tmp_path):
    assert len(charger_effectif(fichier(tmp_path))) == 2


def test_les_accents_sont_intacts(tmp_path):
    assert charger_effectif(fichier(tmp_path))[1]["nom"] == "Céline N'Guessan"


def test_le_salaire_est_un_entier(tmp_path):
    assert charger_effectif(fichier(tmp_path))[0]["salaire_fcfa"] == 250000


def test_les_cinq_champs_sont_presents(tmp_path):
    fiche = charger_effectif(fichier(tmp_path))[0]
    assert sorted(fiche) == ["date_embauche", "matricule", "nom", "poste", "salaire_fcfa"]


def test_le_coeur_ignore_les_fichiers():
    source = pathlib.Path("rh/calculs.py").read_text(encoding="utf-8")
    assert "import csv" not in source
    assert "pathlib" not in source
