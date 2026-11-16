"""Journée 27 : les trois modèles, leurs contraintes, et la migration à jour."""
from datetime import date

import pytest
from django.core.management import call_command
from django.db import IntegrityError, transaction

from effectif.models import Absence, Poste, Salarie


def salarie(matricule="A001"):
    """Crée un salarié de test, poste compris."""
    poste, _ = Poste.objects.get_or_create(libelle="RH")
    return Salarie.objects.create(matricule=matricule, nom="Awa Kone", poste=poste,
                                  date_embauche=date(2024, 3, 1), salaire_fcfa=250000)


def test_un_salarie_se_cree():
    assert salarie().pk is not None


def test_le_matricule_est_unique():
    salarie()
    with pytest.raises(IntegrityError), transaction.atomic():
        salarie()


def test_le_libelle_du_poste_est_unique():
    Poste.objects.create(libelle="Atelier")
    with pytest.raises(IntegrityError), transaction.atomic():
        Poste.objects.create(libelle="Atelier")


def test_une_absence_normale_se_cree():
    absence = Absence.objects.create(salarie=salarie(), date_debut=date(2025, 1, 6),
                                     date_fin=date(2025, 1, 10))
    assert absence.pk is not None


def test_une_absence_finissant_avant_son_debut_est_refusee_en_base():
    with pytest.raises(IntegrityError), transaction.atomic():
        Absence.objects.create(salarie=salarie(), date_debut=date(2025, 1, 10),
                               date_fin=date(2025, 1, 6))


def test_un_poste_utilise_ne_peut_pas_etre_supprime():
    from django.db.models import ProtectedError
    agent = salarie()
    with pytest.raises(ProtectedError):
        agent.poste.delete()


def test_aucune_migration_ne_manque():
    call_command("makemigrations", "effectif", "--check", "--dry-run", verbosity=0)
