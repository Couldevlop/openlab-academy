"""Journée 31 : rien n'entre en base sans avoir été validé côté serveur."""
import pathlib
from datetime import date

from django.urls import reverse

from effectif.models import Poste, Salarie


def poste():
    """Crée le poste utilisé par les tests."""
    return Poste.objects.create(libelle="RH")


def corps(**remplacements):
    """Rend un corps de formulaire valide, modifiable champ par champ."""
    return {"matricule": "A001", "nom": "Awa Kone", "poste": poste().pk,
            "date_embauche": "2024-03-01", "salaire_fcfa": 250000, **remplacements}


def test_le_formulaire_s_affiche(client):
    reponse = client.get(reverse("embauche"))
    assert reponse.status_code == 200
    assert "formulaire" in reponse.context


def test_le_gabarit_porte_la_protection_csrf():
    gabarit = pathlib.Path("effectif/templates/effectif/embauche.html")
    assert "csrf_token" in gabarit.read_text(encoding="utf-8")


def test_une_embauche_valide_cree_le_salarie(client):
    reponse = client.post(reverse("embauche"), data=corps())
    assert reponse.status_code == 302
    assert Salarie.objects.filter(matricule="A001").exists()


def test_un_salaire_negatif_ne_cree_rien(client):
    reponse = client.post(reverse("embauche"), data=corps(salaire_fcfa=-1))
    assert reponse.status_code == 200
    assert Salarie.objects.count() == 0


def test_une_date_future_ne_cree_rien(client):
    reponse = client.post(reverse("embauche"), data=corps(date_embauche="2099-01-01"))
    assert reponse.status_code == 200
    assert Salarie.objects.count() == 0


def test_un_corps_vide_ne_cree_rien(client):
    assert client.post(reverse("embauche"), data={}).status_code == 200
    assert Salarie.objects.count() == 0


def test_un_matricule_deja_pris_est_refuse_meme_ecrit_autrement(client):
    poste_rh = Poste.objects.create(libelle="Atelier")
    Salarie.objects.create(matricule="A001", nom="Awa", poste=poste_rh,
                           date_embauche=date(2024, 3, 1), salaire_fcfa=250000)
    reponse = client.post(reverse("embauche"), data=corps(matricule="a001"))
    assert reponse.status_code == 200
    assert Salarie.objects.count() == 1


def test_le_matricule_est_normalise_en_majuscules(client):
    client.post(reverse("embauche"), data=corps(matricule="b002"))
    assert Salarie.objects.filter(matricule="B002").exists()
