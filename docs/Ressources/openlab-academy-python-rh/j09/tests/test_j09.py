"""Journée 09 : les bornes de l'ancienneté."""
from datetime import date

import pytest

from dates import anciennete_en_mois


def test_le_jour_de_l_embauche_l_anciennete_est_nulle():
    assert anciennete_en_mois(date(2024, 3, 15), date(2024, 3, 15)) == 0


def test_le_mois_commence_ne_compte_pas():
    assert anciennete_en_mois(date(2024, 3, 15), date(2025, 3, 14)) == 11


def test_le_mois_revolu_compte():
    assert anciennete_en_mois(date(2024, 3, 15), date(2025, 3, 15)) == 12


def test_le_lendemain_du_mois_revolu():
    assert anciennete_en_mois(date(2024, 3, 15), date(2025, 3, 16)) == 12


def test_une_embauche_le_29_fevrier_reste_coherente():
    assert anciennete_en_mois(date(2024, 2, 29), date(2025, 2, 28)) == 11


def test_une_date_future_est_refusee():
    with pytest.raises(ValueError):
        anciennete_en_mois(date(2026, 1, 1), date(2025, 1, 1))


def test_le_resultat_est_un_entier():
    assert isinstance(anciennete_en_mois(date(2024, 1, 1), date(2025, 1, 1)), int)
