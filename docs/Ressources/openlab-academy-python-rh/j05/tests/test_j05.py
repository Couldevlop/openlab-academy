"""Journée 05 : le module de calculs, et son silence."""
import contextlib
import io

import pytest

from rh import calculs

NOMS = ("salaire_annuel", "formater_fcfa", "droit_aux_conges",
        "masse_salariale", "plus_haut_salaire")


def test_les_cinq_fonctions_existent():
    for nom in NOMS:
        assert callable(getattr(calculs, nom))


def test_chaque_fonction_porte_une_docstring():
    for nom in NOMS:
        assert getattr(calculs, nom).__doc__


def test_les_comportements_des_journees_precedentes_sont_conserves():
    assert calculs.salaire_annuel(250000, [100000, 150000]) == 3250000
    assert calculs.droit_aux_conges(12) is True
    assert calculs.masse_salariale([250000, 180000]) == 430000
    assert calculs.plus_haut_salaire([250000, 180000]) == 250000


def test_une_anciennete_negative_est_toujours_refusee():
    with pytest.raises(ValueError):
        calculs.droit_aux_conges(-1)


def test_le_module_n_affiche_rien():
    sortie = io.StringIO()
    with contextlib.redirect_stdout(sortie):
        calculs.masse_salariale([250000, 180000])
        calculs.formater_fcfa(250000)
    assert sortie.getvalue() == ""
