"""Journée 23 : trois indicateurs justes, calculés loin de l'écran."""
import pathlib

from rh.indicateurs import effectif_total, masse_salariale, salaire_median

EFFECTIF = [{"matricule": "A1", "nom": "A", "poste": "RH", "salaire_fcfa": 100000},
            {"matricule": "A2", "nom": "B", "poste": "RH", "salaire_fcfa": 200000},
            {"matricule": "A3", "nom": "C", "poste": "RH", "salaire_fcfa": 900000}]


def test_l_effectif_total_compte_les_fiches():
    assert effectif_total(EFFECTIF) == 3


def test_la_masse_additionne_les_salaires():
    assert masse_salariale(EFFECTIF) == 1200000


def test_la_mediane_d_un_effectif_impair():
    assert salaire_median(EFFECTIF) == 200000


def test_la_mediane_d_un_effectif_pair():
    assert salaire_median(EFFECTIF[:2]) == 150000


def test_la_mediane_ignore_un_salaire_extreme():
    assert salaire_median(EFFECTIF) == salaire_median(
        [*EFFECTIF[:2], {**EFFECTIF[2], "salaire_fcfa": 90_000_000}])


def test_un_effectif_vide_rend_des_indicateurs_nuls():
    assert (effectif_total([]), masse_salariale([]), salaire_median([])) == (0, 0, 0)


def test_les_indicateurs_vivent_dans_le_coeur():
    assert pathlib.Path("rh/indicateurs.py").is_file()
    assert "streamlit" not in pathlib.Path("rh/indicateurs.py").read_text(encoding="utf-8")


def test_l_ecran_affiche_les_trois_indicateurs():
    source = pathlib.Path("accueil.py").read_text(encoding="utf-8")
    assert source.count("st.metric") + source.count(".metric(") >= 3
