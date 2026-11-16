"""Journée 19 : le bon code, et rien de plus dans le message."""
import pytest
from fastapi.testclient import TestClient

import api.main
from rh.depot import DepotEffectif
from rh.erreurs import DonneeInvalide
from rh.exemple import FICHES


@pytest.fixture()
def client():
    """Un client neuf par test, dépôt remis à son état d'exemple."""
    api.main.depot = DepotEffectif(FICHES)
    return TestClient(api.main.app, raise_server_exceptions=False)


def test_les_conges_d_un_salarie_ancien_sont_ouverts(client):
    reponse = client.get("/salaries/A003/conges")
    assert reponse.status_code == 200
    assert reponse.json()["droit_ouvert"] is True


def test_les_conges_d_un_matricule_inconnu_rendent_404(client):
    assert client.get("/salaries/Z999/conges").status_code == 404


def test_une_date_illisible_rend_400_et_nomme_le_matricule(client):
    api.main.depot = DepotEffectif([{**FICHES[0], "date_embauche": "01/03/2024"}])
    reponse = client.get("/salaries/A001/conges")
    assert reponse.status_code == 400
    assert "A001" in reponse.json()["detail"]


def test_une_erreur_metier_est_traduite_en_400(client):
    @api.main.app.get("/essai-erreur-metier")
    def essai():
        raise DonneeInvalide("Colonne poste absente du fichier.")

    reponse = client.get("/essai-erreur-metier")
    assert reponse.status_code == 400
    assert reponse.json()["detail"] == "Colonne poste absente du fichier."


def test_une_panne_interne_ne_revele_rien(client):
    @api.main.app.get("/essai-panne")
    def essai():
        raise RuntimeError("mot de passe = secret")

    reponse = client.get("/essai-panne")
    assert reponse.status_code == 500
    corps = reponse.text
    assert "secret" not in corps
    assert "Traceback" not in corps
    assert "main.py" not in corps
