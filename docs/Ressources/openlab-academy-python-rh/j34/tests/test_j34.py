"""Journée 34 : importer, réimporter, et retomber sur le compte du cœur."""
import io

import pytest
from django.core.management import CommandError, call_command

from effectif.models import Poste, Salarie
from effectif.requetes import masse_salariale_par_poste
from rh.calculs import masse_salariale

CSV = """matricule,nom,poste,date_embauche,salaire_fcfa
A001,Awa Kone,RH,2024-03-01,250000
A002,Bakary Traore,Atelier,2023-11-15,180000
A003,Céline N'Guessan,RH,2022-06-30,420000
"""


def fichier(tmp_path, texte=CSV):
    """Écrit un fichier CSV de test et rend son chemin."""
    chemin = tmp_path / "effectif.csv"
    chemin.write_text(texte, encoding="utf-8")
    return str(chemin)


def importer(chemin):
    """Lance la commande et rend ce qu'elle a écrit sur la sortie."""
    sortie = io.StringIO()
    call_command("importer_effectif", chemin, stdout=sortie)
    return sortie.getvalue()


def test_l_import_cree_les_trois_salaries(tmp_path):
    importer(fichier(tmp_path))
    assert Salarie.objects.count() == 3


def test_l_import_cree_les_postes_manquants(tmp_path):
    importer(fichier(tmp_path))
    assert sorted(Poste.objects.values_list("libelle", flat=True)) == ["Atelier", "RH"]


def test_le_second_import_ne_cree_aucun_doublon(tmp_path):
    chemin = fichier(tmp_path)
    importer(chemin)
    sortie = importer(chemin)
    assert Salarie.objects.count() == 3
    assert "3 ignoré(s)" in sortie


def test_la_masse_en_base_egale_celle_du_coeur(tmp_path):
    importer(fichier(tmp_path))
    attendue = masse_salariale([250000, 180000, 420000])
    obtenue = sum(mesures["masse_fcfa"] for mesures in masse_salariale_par_poste().values())
    assert obtenue == attendue


def test_un_fichier_introuvable_arrete_la_commande(tmp_path):
    with pytest.raises(CommandError):
        importer(str(tmp_path / "absent.csv"))


def test_une_colonne_absente_est_nommee(tmp_path):
    tronque = "matricule,nom,poste,date_embauche\nA001,Awa,RH,2024-03-01\n"
    with pytest.raises(CommandError) as erreur:
        importer(fichier(tmp_path, tronque))
    assert "salaire_fcfa" in str(erreur.value)


def test_un_salaire_illisible_n_ecrit_rien(tmp_path):
    fautif = CSV.replace("250000", "250 000")
    with pytest.raises(CommandError):
        importer(fichier(tmp_path, fautif))
    assert Salarie.objects.count() == 0
