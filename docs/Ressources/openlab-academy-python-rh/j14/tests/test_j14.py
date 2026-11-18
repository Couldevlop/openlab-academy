"""Journée 14 : vos tests sont-ils de vrais tests ?

Le harnais exécute chacune de vos vérifications sur l'implémentation correcte, où elle doit
passer, puis sur les trois fautives, où l'ensemble de vos vérifications doit prendre chacune.
"""
import importlib
import inspect
import pathlib

import pytest

import conges_correct
import mes_tests_conges

MES_TESTS = [valeur for nom, valeur in vars(mes_tests_conges).items()
             if nom.startswith("verifier_") and callable(valeur)]
FAUTIFS = sorted(chemin.stem for chemin in pathlib.Path().glob("conges_fautif_*.py"))


def detectee(verification, droit_aux_conges):
    """Rend True si la vérification échoue, par assertion, sur cette implémentation."""
    try:
        verification(droit_aux_conges)
    except AssertionError:
        return True
    return False


def test_les_trois_verifications_existent():
    assert len(MES_TESTS) == 3


def test_les_trois_implementations_fautives_sont_livrees():
    assert len(FAUTIFS) == 3


@pytest.mark.parametrize("verification", MES_TESTS, ids=lambda f: f.__name__)
def test_chaque_verification_contient_une_assertion(verification):
    assert "assert" in inspect.getsource(verification)


@pytest.mark.parametrize("verification", MES_TESTS, ids=lambda f: f.__name__)
def test_chaque_verification_passe_sur_l_implementation_correcte(verification):
    verification(conges_correct.droit_aux_conges)


@pytest.mark.parametrize("fautif", FAUTIFS)
def test_chaque_implementation_fautive_est_prise(fautif):
    droit_aux_conges = importlib.import_module(fautif).droit_aux_conges
    assert any(detectee(verification, droit_aux_conges) for verification in MES_TESTS)
