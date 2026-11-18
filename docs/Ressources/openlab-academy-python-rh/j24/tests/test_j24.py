"""Journée 24 : une série juste, et un axe lisible."""
import pathlib

from rh.exemple import FICHES
from vue.graphiques import libelle_axe, serie_masse_par_poste


def test_la_serie_porte_un_poste_par_cle():
    assert sorted(serie_masse_par_poste(FICHES)) == ["Atelier", "RH"]


def test_la_serie_additionne_les_salaires_du_poste():
    assert serie_masse_par_poste(FICHES)["RH"] == 670000


def test_la_serie_est_dans_l_ordre_alphabetique():
    serie = serie_masse_par_poste(FICHES)
    assert list(serie) == sorted(serie)


def test_une_serie_vide_sur_un_effectif_vide():
    assert serie_masse_par_poste([]) == {}


def test_les_petits_montants_restent_en_fcfa():
    assert libelle_axe(9999) == "FCFA"


def test_le_seuil_des_milliers_est_inclus():
    assert libelle_axe(10000) == "milliers de FCFA"


def test_le_seuil_des_millions_est_inclus():
    assert libelle_axe(1_000_000) == "millions de FCFA"


def test_la_preparation_du_graphique_reste_sans_ecran():
    assert "streamlit" not in pathlib.Path("vue/graphiques.py").read_text(encoding="utf-8")


def test_l_ecran_traite_le_cas_vide():
    source = pathlib.Path("accueil.py").read_text(encoding="utf-8")
    assert "bar_chart" in source
    assert "st.info" in source
