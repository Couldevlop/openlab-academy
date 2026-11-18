"""Journée 08 : regrouper et filtrer sans toucher à l'effectif."""
import copy

from effectifs import filtrer_par_salaire, par_poste

EFFECTIF = [
    {"nom": "Awa", "poste": "RH", "salaire_fcfa": 250000},
    {"nom": "Bakary", "poste": "Atelier", "salaire_fcfa": 180000},
    {"nom": "Céline", "poste": "RH", "salaire_fcfa": 420000},
]


def test_le_regroupement_rassemble_les_noms_par_poste():
    assert par_poste(EFFECTIF) == {"RH": ["Awa", "Céline"], "Atelier": ["Bakary"]}


def test_le_regroupement_d_un_effectif_vide():
    assert par_poste([]) == {}


def test_le_filtre_inclut_la_borne_exacte():
    noms = [fiche["nom"] for fiche in filtrer_par_salaire(EFFECTIF, 250000)]
    assert noms == ["Awa", "Céline"]


def test_le_filtre_peut_ne_rien_rendre():
    assert filtrer_par_salaire(EFFECTIF, 500000) == []


def test_le_filtre_rend_tout_quand_le_minimum_est_nul():
    assert len(filtrer_par_salaire(EFFECTIF, 0)) == 3


def test_l_effectif_d_origine_n_a_pas_bouge():
    avant = copy.deepcopy(EFFECTIF)
    par_poste(EFFECTIF)
    filtrer_par_salaire(EFFECTIF, 200000)
    assert EFFECTIF == avant
