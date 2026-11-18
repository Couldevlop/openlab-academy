"""Journée 32 : aucune page de l'effectif ne répond à un visiteur anonyme."""
from datetime import date

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

from effectif.models import Poste, Salarie



@pytest.fixture()
def agent():
    """Un compte de test, membre de l'équipe RH."""
    return get_user_model().objects.create_user("agent-rh")


@pytest.fixture()
def salarie():
    """Un salarié de test."""
    return Salarie.objects.create(matricule="A001", nom="Awa", poste=Poste.objects.create(
        libelle="RH"), date_embauche=date(2024, 3, 1), salaire_fcfa=250000)


@pytest.mark.parametrize("nom_de_route,arguments", [("salaries", ()),
                                                    ("embauche", ()),
                                                    ("fiche-salarie", ("A001",))])
def test_un_acces_anonyme_est_redirige(client, salarie, nom_de_route, arguments):
    reponse = client.get(reverse(nom_de_route, args=arguments))
    assert reponse.status_code == 302
    assert reverse("connexion") in reponse.headers["Location"]


@pytest.mark.parametrize("nom_de_route,arguments", [("salaries", ()),
                                                    ("embauche", ()),
                                                    ("fiche-salarie", ("A001",))])
def test_un_agent_connecte_est_servi(client, agent, salarie, nom_de_route, arguments):
    client.force_login(agent)
    assert client.get(reverse(nom_de_route, args=arguments)).status_code == 200


def test_un_post_anonyme_ne_cree_rien(client):
    poste = Poste.objects.create(libelle="RH")
    client.post(reverse("embauche"), data={"matricule": "B002", "nom": "Bakary",
                                           "poste": poste.pk, "date_embauche": "2024-03-01",
                                           "salaire_fcfa": 180000})
    assert Salarie.objects.count() == 0


def test_la_page_de_connexion_reste_ouverte(client):
    assert client.get(reverse("connexion")).status_code == 200
