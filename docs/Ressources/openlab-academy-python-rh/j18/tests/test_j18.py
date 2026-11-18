"""Journée 18 : créer une fiche, et refuser ce qui n'est pas acceptable."""
import pytest
from fastapi.testclient import TestClient

from api.main import app

NOUVEAU = {"matricule": "A010", "nom": "Fatou Diarra", "poste": "Comptabilité",
           "date_embauche": "2025-01-06", "salaire_fcfa": 300000}


@pytest.fixture()
def client():
    """Un client neuf par test : le dépôt est remis à son état d'exemple."""
    from rh.depot import DepotEffectif
    from rh.exemple import FICHES
    import api.main

    api.main.depot = DepotEffectif(FICHES)
    return TestClient(app)


def test_une_creation_reussie_rend_201(client):
    reponse = client.post("/salaries", json=NOUVEAU)
    assert reponse.status_code == 201
    assert reponse.json()["matricule"] == "A010"


def test_la_fiche_creee_apparait_dans_la_liste(client):
    client.post("/salaries", json=NOUVEAU)
    matricules = [fiche["matricule"] for fiche in client.get("/salaries").json()]
    assert "A010" in matricules


def test_le_meme_matricule_deux_fois_rend_409(client):
    client.post("/salaries", json=NOUVEAU)
    assert client.post("/salaries", json=NOUVEAU).status_code == 409


@pytest.mark.parametrize("champ,valeur", [("salaire_fcfa", -1),
                                          ("date_embauche", "2099-01-01"),
                                          ("poste", "")])
def test_les_valeurs_refusees_rendent_422(client, champ, valeur):
    assert client.post("/salaries", json={**NOUVEAU, champ: valeur}).status_code == 422


def test_un_champ_inconnu_est_refuse(client):
    assert client.post("/salaries", json={**NOUVEAU, "prime": 1}).status_code == 422


def test_un_corps_incomplet_rend_422(client):
    assert client.post("/salaries", json={"matricule": "A011"}).status_code == 422
