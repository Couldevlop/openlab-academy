"""Journée 04 : masse salariale et plus haut salaire."""
import pytest

from paie import masse_salariale, plus_haut_salaire


def test_la_masse_d_un_effectif_vide_est_nulle():
    assert masse_salariale([]) == 0


def test_la_masse_d_un_seul_salaire_est_ce_salaire():
    assert masse_salariale([250000]) == 250000


def test_la_masse_additionne_tous_les_salaires():
    assert masse_salariale([250000, 180000, 420000]) == 850000


def test_le_plus_haut_salaire_d_un_seul_element():
    assert plus_haut_salaire([250000]) == 250000


def test_le_plus_haut_salaire_parmi_plusieurs():
    assert plus_haut_salaire([250000, 420000, 180000]) == 420000


def test_deux_salaires_ex_aequo_donnent_la_meme_valeur():
    assert plus_haut_salaire([420000, 420000, 180000]) == 420000


def test_un_effectif_vide_n_a_pas_de_plus_haut_salaire():
    with pytest.raises(ValueError):
        plus_haut_salaire([])
