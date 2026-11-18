"""Journée 20 : l'état par poste, calculé par le cœur."""
import pathlib

import pytest
from fastapi.testclient import TestClient

import api.main
from rh.depot import DepotEffectif
from rh.exemple import FICHES


@pytest.fixture()
def client():
    """Un client neuf par test, dépôt remis à son état d'exemple."""
    api.main.depot = DepotEffectif(FICHES)
    return TestClient(api.main.app)


def test_l_etat_rend_un_poste_par_cle(client):
    etat = client.get("/etats/par-poste").json()
    assert sorted(etat) == ["Atelier", "RH"]


def test_l_etat_compte_les_salaries(client):
    assert client.get("/etats/par-poste").json()["RH"]["effectif"] == 2


def test_l_etat_additionne_la_masse(client):
    assert client.get("/etats/par-poste").json()["RH"]["masse_fcfa"] == 670000


def test_les_postes_sont_rendus_dans_l_ordre(client):
    etat = client.get("/etats/par-poste").json()
    assert list(etat) == sorted(etat)


def test_un_depot_vide_rend_un_etat_vide(client):
    api.main.depot = DepotEffectif([])
    assert client.get("/etats/par-poste").json() == {}


def test_le_calcul_vit_dans_le_coeur():
    assert "def etat_par_poste" in pathlib.Path("rh/calculs.py").read_text(encoding="utf-8")


def test_le_coeur_reste_sans_framework_web():
    for source in pathlib.Path("rh").glob("*.py"):
        texte = source.read_text(encoding="utf-8")
        assert "fastapi" not in texte, source
