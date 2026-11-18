"""Journée 28 : une requête, pas une par ligne, et jamais de SQL bricolé."""
import pathlib
from datetime import date

from django.db import connection
from django.test.utils import CaptureQueriesContext

from effectif.models import Poste, Salarie
from effectif.requetes import masse_salariale_par_poste, salaries_du_poste


def effectif_de_demonstration():
    """Crée deux postes et trois salariés."""
    rh = Poste.objects.create(libelle="RH")
    atelier = Poste.objects.create(libelle="Atelier")
    Salarie.objects.create(matricule="A001", nom="Awa", poste=rh,
                           date_embauche=date(2024, 3, 1), salaire_fcfa=250000)
    Salarie.objects.create(matricule="A002", nom="Bakary", poste=atelier,
                           date_embauche=date(2023, 11, 15), salaire_fcfa=180000)
    Salarie.objects.create(matricule="A003", nom="Céline", poste=rh,
                           date_embauche=date(2022, 6, 30), salaire_fcfa=420000)


def test_la_masse_est_regroupee_par_poste():
    effectif_de_demonstration()
    assert masse_salariale_par_poste() == {
        "Atelier": {"effectif": 1, "masse_fcfa": 180000},
        "RH": {"effectif": 2, "masse_fcfa": 670000},
    }


def test_les_postes_sont_rendus_dans_l_ordre():
    effectif_de_demonstration()
    etat = masse_salariale_par_poste()
    assert list(etat) == sorted(etat)


def test_un_effectif_vide_rend_un_etat_vide():
    assert masse_salariale_par_poste() == {}


def test_l_agregat_ne_coute_qu_une_requete():
    effectif_de_demonstration()
    with CaptureQueriesContext(connection) as requetes:
        masse_salariale_par_poste()
    assert len(requetes) == 1


def test_lire_le_poste_des_salaries_ne_coute_rien_de_plus():
    effectif_de_demonstration()
    retenus = salaries_du_poste("RH")
    with CaptureQueriesContext(connection) as requetes:
        libelles = [agent.poste.libelle for agent in retenus]
    assert libelles == ["RH", "RH"]
    assert len(requetes) == 0


def test_aucune_requete_brute_dans_le_module():
    source = pathlib.Path("effectif/requetes.py").read_text(encoding="utf-8")
    for interdit in (".raw(", "cursor()", "cursor.execute", "extra("):
        assert interdit not in source, interdit
