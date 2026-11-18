"""Journée 30 : deux pages, le bon contexte, et un nombre de requêtes qui ne dérive pas."""
from datetime import date

from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.urls import reverse

from effectif.models import Poste, Salarie


def dix_salaries():
    """Crée dix salariés sur deux postes."""
    rh = Poste.objects.create(libelle="RH")
    atelier = Poste.objects.create(libelle="Atelier")
    for numero in range(10):
        Salarie.objects.create(matricule=f"A{numero:03d}", nom=f"Agent {numero}",
                               poste=rh if numero % 2 else atelier,
                               date_embauche=date(2024, 3, 1), salaire_fcfa=200000 + numero)


def test_la_liste_repond_et_utilise_son_gabarit(client):
    dix_salaries()
    reponse = client.get(reverse("salaries"))
    assert reponse.status_code == 200
    assert "effectif/liste.html" in [gabarit.name for gabarit in reponse.templates]


def test_la_liste_porte_les_salaries_et_l_etat(client):
    dix_salaries()
    contexte = client.get(reverse("salaries")).context
    assert len(contexte["salaries"]) == 10
    assert sorted(contexte["etat"]) == ["Atelier", "RH"]


def test_la_fiche_d_un_salarie_repond(client):
    dix_salaries()
    reponse = client.get(reverse("fiche-salarie", args=["A001"]))
    assert reponse.status_code == 200
    assert reponse.context["salarie"].matricule == "A001"


def test_un_matricule_inconnu_rend_404(client):
    assert client.get(reverse("fiche-salarie", args=["Z999"])).status_code == 404


def test_la_liste_vide_s_affiche_sans_erreur(client):
    reponse = client.get(reverse("salaries"))
    assert reponse.status_code == 200
    assert "Aucun salarié" in reponse.content.decode("utf-8")


def test_la_liste_ne_multiplie_pas_les_requetes(client):
    dix_salaries()
    with CaptureQueriesContext(connection) as requetes:
        client.get(reverse("salaries"))
    assert len(requetes) <= 4, [requete["sql"] for requete in requetes]
