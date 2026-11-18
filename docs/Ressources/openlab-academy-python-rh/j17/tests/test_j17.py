"""Journée 17 : montrer le nécessaire, et répondre 404 proprement."""
from fastapi.testclient import TestClient

from api.main import app

client = TestClient(app)


def test_la_liste_ne_montre_pas_les_salaires():
    for fiche in client.get("/salaries").json():
        assert "salaire_fcfa" not in fiche
        assert "date_embauche" not in fiche


def test_la_liste_montre_les_trois_champs_publics():
    assert sorted(client.get("/salaries").json()[0]) == ["matricule", "nom", "poste"]


def test_le_detail_montre_les_cinq_champs():
    reponse = client.get("/salaries/A001")
    assert reponse.status_code == 200
    assert sorted(reponse.json()) == ["date_embauche", "matricule", "nom", "poste", "salaire_fcfa"]


def test_le_detail_porte_le_bon_salaire():
    assert client.get("/salaries/A001").json()["salaire_fcfa"] == 250000


def test_un_matricule_inconnu_rend_404():
    reponse = client.get("/salaries/Z999")
    assert reponse.status_code == 404
    assert "Z999" in reponse.json()["detail"]


def test_le_schema_declare_les_modeles_de_sortie():
    chemins = client.get("/openapi.json").json()["paths"]
    assert "/salaries/{matricule}" in chemins
