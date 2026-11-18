"""Journée 22 : filtrer juste, et garder la préparation pure."""
import pathlib

from rh.exemple import FICHES
from vue.donnees import filtrer, postes


def test_les_postes_sont_tries_et_sans_doublon():
    assert postes(FICHES) == ["Atelier", "RH"]


def test_les_postes_d_un_effectif_vide():
    assert postes([]) == []


def test_le_filtre_sur_un_poste():
    retenues = filtrer(FICHES, poste="RH")
    assert {fiche["poste"] for fiche in retenues} == {"RH"}


def test_tous_les_postes_ne_filtrent_rien():
    assert len(filtrer(FICHES, poste=None)) == len(FICHES)


def test_le_filtre_inclut_la_borne_exacte():
    retenues = filtrer(FICHES, salaire_minimum=250000)
    assert sorted(fiche["matricule"] for fiche in retenues) == ["A001", "A003"]


def test_les_deux_filtres_se_combinent():
    retenues = filtrer(FICHES, poste="RH", salaire_minimum=300000)
    assert [fiche["matricule"] for fiche in retenues] == ["A003"]


def test_un_minimum_trop_haut_ne_rend_rien():
    assert filtrer(FICHES, salaire_minimum=10_000_000) == []


def test_la_preparation_reste_sans_ecran():
    source = pathlib.Path("vue/donnees.py").read_text(encoding="utf-8")
    assert "streamlit" not in source


def test_l_ecran_propose_les_deux_filtres():
    source = pathlib.Path("accueil.py").read_text(encoding="utf-8")
    assert "selectbox" in source
    assert "number_input" in source
