"""Journée 16 : deux routes de lecture, et un cœur qui ignore le web."""
import pathlib

from fastapi.testclient import TestClient

from api.main import app

client = TestClient(app)


def test_la_route_de_sante_repond():
    reponse = client.get("/sante")
    assert reponse.status_code == 200
    assert reponse.json() == {"etat": "ok"}


def test_la_liste_rend_les_trois_fiches():
    reponse = client.get("/salaries")
    assert reponse.status_code == 200
    assert len(reponse.json()) == 3


def test_la_liste_est_triee_par_matricule():
    matricules = [fiche["matricule"] for fiche in client.get("/salaries").json()]
    assert matricules == sorted(matricules)


def test_une_route_inconnue_rend_404():
    assert client.get("/inconnue").status_code == 404


def test_le_coeur_ignore_le_web():
    for source in pathlib.Path("rh").glob("*.py"):
        assert "fastapi" not in source.read_text(encoding="utf-8"), source
