"""Inscriptions : un parcours payant se suit par une cohorte, dont l'inscription ouvre le dossier de paiement.

L'inscription directe au parcours (autonomie du LMS) n'est permise que pour un parcours gratuit (MOOC), un membre de
l'équipe (rôle jamais bloqué), l'administrateur qui inscrit lui-même un apprenant, ou l'inscription que la cohorte crée
pour ses parcours. Une cohorte ne facture qu'un parcours : deux parcours payants dans une même cohorte sont refusés
(le second n'aurait pas de dossier)."""
from collections.abc import Sequence
from dataclasses import dataclass

from openlab_academy.application.ports_paiement import ParcoursGratuits

HORS_COHORTE = "Inscrivez-vous à une cohorte de ce parcours."
PLUSIEURS_PAYANTS = ("Cette cohorte regroupe plusieurs parcours payants : inscription impossible, contactez "
                     "l'intendance.")


class InscriptionRefusee(Exception):
    pass


@dataclass(frozen=True)
class InscriptionDirecte:
    cours: str
    membre_exempte: bool  # rôle jamais bloqué (équipe)
    par_administrateur: bool  # l'administrateur en session inscrit lui-même l'apprenant
    via_cohorte: bool  # créée par l'inscription à une cohorte qui porte ce parcours


def verifier_inscription_directe(gratuits: ParcoursGratuits, demande: InscriptionDirecte) -> None:
    if demande.membre_exempte or demande.par_administrateur or demande.via_cohorte:
        return
    if not gratuits.gratuit(demande.cours):
        raise InscriptionRefusee(HORS_COHORTE)


def parcours_facture(gratuits: ParcoursGratuits, cours: Sequence[str]) -> str | None:
    """Parcours de la cohorte qui porte le dossier : son seul parcours payant, sinon le premier (gratuit : aucun
    dossier) ; None pour une cohorte sans parcours."""
    payants = [c for c in cours if not gratuits.gratuit(c)]
    if len(payants) > 1:
        raise InscriptionRefusee(PLUSIEURS_PAYANTS)
    return payants[0] if payants else (cours[0] if cours else None)
