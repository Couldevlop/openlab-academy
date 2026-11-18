"""Journée 33 : la donnée refusée ne part pas sur le réseau."""
from datetime import date

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.urls import reverse

from effectif.models import Poste, Salarie
from effectif.roles import GROUPE_MANAGER, GROUPE_RH, voit_les_salaires

SALAIRE = 777777


@pytest.fixture()
def salarie():
    """Un salarié dont le salaire est reconnaissable dans une réponse."""
    return Salarie.objects.create(matricule="A001", nom="Awa", poste=Poste.objects.create(
        libelle="RH"), date_embauche=date(2024, 3, 1), salaire_fcfa=SALAIRE)


def compte(nom, groupe=None, superutilisateur=False):
    """Crée un compte de test, éventuellement membre d'un groupe."""
    modele = get_user_model()
    # force_login installe la session sans verifier d'identifiants : aucun mot de passe
    # n'est necessaire, et aucun ne doit etre ecrit en dur.
    utilisateur = (modele.objects.create_superuser(nom)
                   if superutilisateur
                   else modele.objects.create_user(nom))
    if groupe:
        utilisateur.groups.add(Group.objects.get_or_create(name=groupe)[0])
    return utilisateur


def test_l_equipe_rh_voit_les_salaires():
    assert voit_les_salaires(compte("rh", GROUPE_RH)) is True


def test_le_manager_ne_voit_pas_les_salaires():
    assert voit_les_salaires(compte("manager", GROUPE_MANAGER)) is False


def test_un_compte_sans_groupe_ne_voit_pas_les_salaires():
    assert voit_les_salaires(compte("simple")) is False


def test_le_superutilisateur_voit_les_salaires():
    assert voit_les_salaires(compte("patron", superutilisateur=True)) is True


def test_la_fiche_vue_par_le_manager_ne_contient_aucun_montant(client, salarie):
    client.force_login(compte("manager", GROUPE_MANAGER))
    reponse = client.get(reverse("fiche-salarie", args=["A001"]))
    assert reponse.status_code == 200
    assert str(SALAIRE) not in reponse.content.decode("utf-8")


def test_la_fiche_vue_par_l_equipe_rh_contient_le_montant(client, salarie):
    client.force_login(compte("rh", GROUPE_RH))
    reponse = client.get(reverse("fiche-salarie", args=["A001"]))
    assert str(SALAIRE) in reponse.content.decode("utf-8")


def test_la_liste_vue_par_le_manager_ne_contient_pas_la_masse(client, salarie):
    client.force_login(compte("manager", GROUPE_MANAGER))
    reponse = client.get(reverse("salaries"))
    assert reponse.context["etat"] == {}
    assert str(SALAIRE) not in reponse.content.decode("utf-8")


def test_la_liste_vue_par_l_equipe_rh_contient_la_masse(client, salarie):
    client.force_login(compte("rh", GROUPE_RH))
    reponse = client.get(reverse("salaries"))
    assert reponse.context["etat"]["RH"]["masse_fcfa"] == SALAIRE


def test_le_manager_voit_quand_meme_les_noms(client, salarie):
    client.force_login(compte("manager", GROUPE_MANAGER))
    assert "Awa" in client.get(reverse("salaries")).content.decode("utf-8")
