"""Domaine : les exercices d'une leçon s'ouvrent un délai réglé après sa première ouverture."""
import datetime
import math


class ExercicesVerrouilles(Exception):
    """Les exercices ne sont pas encore accessibles."""


def verifier_deblocage(ouverture: datetime.datetime | None, maintenant: datetime.datetime, delai_minutes: int) -> None:
    if ouverture is None:
        raise ExercicesVerrouilles("Exercices verrouillés : ouvrez d'abord la leçon et prenez le temps de l'étudier.")
    restant = ouverture + datetime.timedelta(minutes=delai_minutes) - maintenant
    if restant > datetime.timedelta(0):
        minutes = math.ceil(restant.total_seconds() / 60)
        raise ExercicesVerrouilles(
            f"Exercices verrouillés : étudiez la leçon encore {minutes} minute{'s' if minutes > 1 else ''}.")
