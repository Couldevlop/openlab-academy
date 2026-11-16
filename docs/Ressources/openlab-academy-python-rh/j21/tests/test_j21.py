"""Journée 21 : les données préparées, et un écran qui ne calcule pas."""
import pathlib

from rh.exemple import FICHES
from vue.donnees import COLONNES, colonnes_affichees

ECRAN = pathlib.Path("accueil.py")


def test_les_trois_colonnes_publiques_sont_rendues():
    assert list(colonnes_affichees(FICHES)[0]) == list(COLONNES)


def test_le_salaire_n_est_jamais_affiche():
    for ligne in colonnes_affichees(FICHES):
        assert "salaire_fcfa" not in ligne


def test_toutes_les_lignes_sont_rendues():
    assert len(colonnes_affichees(FICHES)) == len(FICHES)


def test_un_effectif_vide_rend_une_liste_vide():
    assert colonnes_affichees([]) == []


def test_l_ecran_porte_un_titre_et_une_legende():
    source = ECRAN.read_text(encoding="utf-8")
    assert "st.title" in source
    assert "st.caption" in source


def test_l_ecran_appelle_la_preparation_des_donnees():
    assert "colonnes_affichees" in ECRAN.read_text(encoding="utf-8")


def test_l_ecran_ne_calcule_rien():
    source = ECRAN.read_text(encoding="utf-8")
    assert "for " not in source
    assert "sum(" not in source
