"""Détection : trois règles à écrire sur les événements normalisés.

Une règle de détection n'est pas un filtre : c'est une hypothèse sur le comportement d'un attaquant,
écrite de façon qu'une machine puisse la vérifier. Elle se juge sur deux choses, et la seconde
compte autant que la première : ce qu'elle attrape, et ce qu'elle laisse passer sans crier.

Chaque règle rend une liste d'alertes. Une alerte est un dictionnaire :

    {"regle": "force-brute", "horodatage": "...", "acteur": "185.203.44.19", "compte": "kone.a",
     "resume": "60 échecs puis une réussite en 5 minutes"}

`verifier.py` lit ces alertes : gardez les clés telles quelles.
"""
from normaliser import collecter

FENETRE_MINUTES = 10          # durée pendant laquelle on regroupe des échecs
SEUIL_ECHECS = 10             # au-delà, ce n'est plus une faute de frappe
SEUIL_OCTETS = 100 * 1024 * 1024   # 100 Mo sortants : à partir de là, on veut savoir
HEURES_CREUSES = set(range(22, 24)) | set(range(0, 7))
RESEAU_INTERNE = "10.20."     # tout le reste est public, donc hors de l'agence


def minutes(horodatage: str) -> int:
    """Horodatage ISO ramené en minutes depuis le début de la journée — de quoi mesurer un écart."""
    heure, minute = int(horodatage[11:13]), int(horodatage[14:16])
    return heure * 60 + minute


def force_brute(evenements: list[dict]) -> list[dict]:
    """Essais répétés puis réussite sur le même compte. À VOUS.

    Cherchez, par couple (acteur, compte) : au moins SEUIL_ECHECS connexions en échec à l'intérieur
    d'une fenêtre de FENETRE_MINUTES, suivies d'une connexion réussie du même couple.

    Une seule alerte par couple, horodatée sur la réussite : c'est l'instant qui compte, c'est celui
    où l'attaquant entre. Les échecs sans réussite se signalent autrement — ils encombreraient la
    console de l'analyste sans rien lui apprendre.
    """
    raise NotImplementedError("force_brute : à écrire")


def fichier_depose(evenements: list[dict]) -> list[dict]:
    """Un fichier déposé sur le portail, puis rappelé. À VOUS.

    Un site rend des pages qu'il connaît. Si un chemin apparaît d'abord dans une requête qui dépose
    (POST, code 201) et revient ensuite dans des requêtes qui l'appellent, ce chemin n'était pas au
    programme : quelqu'un l'a ajouté, puis s'en sert.

    Une alerte par chemin, horodatée sur le dépôt, `acteur` = l'adresse qui a déposé, et le chemin
    dans le résumé.
    """
    raise NotImplementedError("fichier_depose : à écrire")


def exfiltration(evenements: list[dict]) -> list[dict]:
    """Un gros volume qui sort, la nuit, vers l'extérieur. À VOUS.

    Signalez les transferts de plus de SEUIL_OCTETS pendant les HEURES_CREUSES.

    Attention : la sauvegarde nocturne déplace davantage encore, et elle est légitime. Ce qui la
    distingue n'est ni l'heure ni le volume, mais la destination — elle reste dans RESEAU_INTERNE.
    Une règle qui la signale chaque nuit sera désactivée par le premier analyste fatigué, et ce jour-là
    plus rien ne gardera la porte.
    """
    raise NotImplementedError("exfiltration : à écrire")


REGLES = (force_brute, fichier_depose, exfiltration)


def analyser(evenements: list[dict] | None = None) -> list[dict]:
    """Passe les trois règles sur le corpus et rend les alertes, dans l'ordre du temps."""
    evenements = collecter() if evenements is None else evenements
    alertes = [alerte for regle in REGLES for alerte in regle(evenements)]
    return sorted(alertes, key=lambda a: a["horodatage"])


if __name__ == "__main__":
    for alerte in analyser():
        print(f"{alerte['horodatage']}  {alerte['regle']:16} {alerte['acteur']:18} {alerte['resume']}")
