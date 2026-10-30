"""Aide commune aux suites de test qui éprouvent autre chose que la visibilité."""
from contextlib import contextmanager
from unittest import mock

from openlab_academy.domain.lancement import PhaseLancement
from openlab_academy.entrypoints import lancement, lms
from openlab_academy.infrastructure import reglages_source_frappe


def sans_phase_de_lancement(test):
    """Ces suites éprouvent le blocage pour paiement : la phase de lancement du site (qui cacherait leurs parcours
    de test) est décochée le temps du test ; la visibilité a sa propre suite. Les refus et la source retenus pour la
    requête (cache de `lms`) sont oubliés avant et après : un refus calculé par un test précédent ne doit pas rester."""
    lms.vider_cache()
    test.addCleanup(lms.vider_cache)
    patch = mock.patch.object(reglages_source_frappe, "phase_lancement", return_value=PhaseLancement(False))
    patch.start()
    test.addCleanup(patch.stop)


@contextmanager
def inscription_libre():
    """Préparation de données seulement (jamais autour d'une assertion de refus) : l'inscription d'un test se fait
    sans refus (parcours fermé ou caché) ni rattachement à la cohorte-fenêtre ; ces comportements ont leur suite."""
    with mock.patch.object(lms, "refuser_inscription"), mock.patch.object(lancement, "rejoindre_cohorte"):
        yield
