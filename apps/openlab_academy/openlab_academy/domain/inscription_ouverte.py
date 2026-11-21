"""Domaine : une cohorte accueille-t-elle encore des inscriptions, et laquelle accueille celui qui arrive ?

C'est la seule question que le site public a le droit de poser. **Le visiteur choisit un parcours, jamais
une cohorte** : c'est le serveur qui désigne celle qui l'accueillera. Laisser le client la nommer
reviendrait à lui laisser dire « inscris-moi à celle-là », y compris close, pleine, ou appartenant à un
autre parcours — OWASP A01, et la plus facile des falsifications puisqu'il suffit de changer un
identifiant dans le formulaire.

**La date limite n'est pas décidée ici.** Elle l'est déjà par `inscription_permise`, qu'applique
`OuvrirDossier.verifier` au moment où l'inscription est réellement tentée. Ce module s'y range : ce que la
page annonce ouvert, le serveur doit l'accepter, et ce qu'elle annonce fermé, il doit le refuser. Une
seconde règle écrite ici aurait dérivé de la première à la première modification des réglages, et la
dérive se serait vue soit en vente perdue, soit en erreur au visage du visiteur.

Rien ici ne connaît Frappe : l'adaptateur lit la base et remplit des `Candidate`.
"""
import datetime
import enum
from dataclasses import dataclass

from openlab_academy.domain.echeancier import inscription_permise


class Etat(enum.Enum):
    """L'état d'une cohorte vis-à-vis des inscriptions, et ce qu'on en dit au visiteur.

    Chaque état porte sa phrase, parce qu'un refus muet envoie le visiteur ailleurs. Elles sont ici, et
    non dans le gabarit, pour que le test puisse exiger qu'aucun état n'en manque.
    """
    OUVERTE = "Les inscriptions sont ouvertes."
    FERMEE_COMPLETE = "Cette session est complète. Inscrivez-vous à la prochaine, dès son ouverture."
    FERMEE_TARDIVE = "Les inscriptions à cette session sont closes. La prochaine ouvrira bientôt."
    FERMEE_PASSEE = "Cette session est terminée."
    FERMEE_RETIREE = "Les inscriptions ne sont pas encore ouvertes."

    @property
    def message(self) -> str:
        return self.value

    @property
    def ouverte(self) -> bool:
        return self is Etat.OUVERTE


OUVERTE = Etat.OUVERTE
FERMEE_COMPLETE = Etat.FERMEE_COMPLETE
FERMEE_TARDIVE = Etat.FERMEE_TARDIVE
FERMEE_PASSEE = Etat.FERMEE_PASSEE
FERMEE_RETIREE = Etat.FERMEE_RETIREE

TARDIVE_PAR_DEFAUT = 2  # mois ; la valeur réglée prime, celle-ci n'est qu'un filet


@dataclass(frozen=True)
class Candidate:
    """Une cohorte vue sous l'angle des inscriptions, et rien d'autre.

    `libre` distingue la fenêtre d'accès libre de la promotion à dates fixes. La différence n'est pas
    cosmétique : une promotion a des séances communes, que le retardataire ne rattrape pas ; une fenêtre
    n'en a aucune, et se rejoint tant qu'elle dure.
    """
    identifiant: str
    titre: str
    debut: datetime.date
    fin: datetime.date
    places: int
    inscrits: int
    publiee: bool
    libre: bool

    @property
    def places_restantes(self) -> int:
        return max(self.places - self.inscrits, 0)


def etat_de(cohorte: Candidate, aujourd_hui: datetime.date,
            tardive_mois: int = TARDIVE_PAR_DEFAUT) -> Etat:
    """L'état d'une cohorte, dans l'ordre où les refus comptent.

    Le retrait passe en premier : une cohorte dépubliée ne doit laisser filtrer ni sa date ni son
    remplissage. Vient ensuite ce qui est définitif — elle est terminée —, puis la date limite, puis le
    remplissage. Cet ordre décide de la phrase que lit le visiteur.
    """
    if not cohorte.publiee:
        return FERMEE_RETIREE
    if aujourd_hui > cohorte.fin:
        return FERMEE_PASSEE
    if not cohorte.libre and not inscription_permise(cohorte.debut, aujourd_hui, tardive_mois):
        return FERMEE_TARDIVE
    if cohorte.places_restantes <= 0:
        return FERMEE_COMPLETE
    return OUVERTE


def cohorte_d_accueil(cohortes, aujourd_hui: datetime.date,
                      tardive_mois: int = TARDIVE_PAR_DEFAUT) -> Candidate | None:
    """Celle qui accueillera le visiteur : la plus proche parmi les ouvertes, ou rien.

    La plus proche, parce qu'on vient pour commencer, pas pour attendre le trimestre suivant. À dates
    égales, l'identifiant tranche : sans ce second critère, deux visiteurs de la même page se verraient
    proposer deux cohortes différentes selon l'ordre où la base les rend.
    """
    ouvertes = [c for c in cohortes if etat_de(c, aujourd_hui, tardive_mois).ouverte]
    if not ouvertes:
        return None
    return min(ouvertes, key=lambda c: (c.debut, c.identifiant))


def etat_du_parcours(cohortes, aujourd_hui: datetime.date,
                     tardive_mois: int = TARDIVE_PAR_DEFAUT) -> Etat:
    """Ce que la page du parcours annonce, quand aucune cohorte n'accueille.

    On prend l'état le moins décourageant des cohortes publiées : « complet » vaut mieux que « terminée »,
    parce qu'il dit qu'il y a eu de la demande et qu'il y aura une suite. Sans aucune cohorte publiée, on
    reste sur « pas encore ouvertes », qui est la vérité.
    """
    if any(etat_de(c, aujourd_hui, tardive_mois).ouverte for c in cohortes):
        return OUVERTE
    rang = (FERMEE_COMPLETE, FERMEE_TARDIVE, FERMEE_PASSEE, FERMEE_RETIREE)
    etats = {etat_de(c, aujourd_hui, tardive_mois) for c in cohortes}
    return next((etat for etat in rang if etat in etats), FERMEE_RETIREE)
