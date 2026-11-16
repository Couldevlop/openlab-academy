"""Journée 29 : une administration utilisable, et aucun compte né d'une migration."""
import pathlib
from datetime import date

from django.contrib import admin
from django.contrib.auth import get_user_model
from effectif.models import Absence, Poste, Salarie


def test_les_trois_modeles_sont_enregistres():
    for modele in (Poste, Salarie, Absence):
        assert modele in admin.site._registry, modele


def test_la_liste_des_salaries_montre_les_quatre_colonnes():
    colonnes = admin.site._registry[Salarie].list_display
    assert tuple(colonnes) == ("matricule", "nom", "poste", "date_embauche")


def test_la_liste_des_salaries_se_filtre_et_se_cherche():
    reglages = admin.site._registry[Salarie]
    assert "poste" in reglages.list_filter
    assert "matricule" in reglages.search_fields


def test_la_liste_des_salaries_charge_le_poste_avec_elle():
    """Sans ce réglage, la liste d'administration relit le poste de chaque ligne."""
    assert "poste" in admin.site._registry[Salarie].list_select_related


def test_la_liste_d_administration_repond_a_l_equipe_rh(client):
    poste = Poste.objects.create(libelle="RH")
    Salarie.objects.create(matricule="A001", nom="Awa", poste=poste,
                           date_embauche=date(2024, 3, 1), salaire_fcfa=250000)
    get_user_model().objects.create_superuser("agent-rh", password="mot-de-passe-de-test-1")
    client.force_login(get_user_model().objects.get(username="agent-rh"))
    reponse = client.get("/admin/effectif/salarie/")
    assert reponse.status_code == 200
    assert "A001" in reponse.content.decode("utf-8")


def test_aucun_compte_n_est_cree_par_migration():
    assert get_user_model().objects.count() == 0


def test_aucune_migration_ne_cree_de_compte():
    for migration in pathlib.Path("effectif/migrations").glob("*.py"):
        texte = migration.read_text(encoding="utf-8")
        assert "create_superuser" not in texte, migration
        assert "set_password" not in texte, migration
