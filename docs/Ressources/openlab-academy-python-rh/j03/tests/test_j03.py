"""Journée 03 : les bornes de la règle des congés."""
import pytest

from conges import droit_aux_conges


def test_aucun_droit_a_l_embauche():
    assert droit_aux_conges(0) is False


def test_aucun_droit_a_onze_mois():
    assert droit_aux_conges(11) is False


def test_le_droit_s_ouvre_a_douze_mois_exactement():
    assert droit_aux_conges(12) is True


def test_le_droit_reste_ouvert_a_treize_mois():
    assert droit_aux_conges(13) is True


def test_une_anciennete_negative_est_refusee():
    with pytest.raises(ValueError):
        droit_aux_conges(-1)
