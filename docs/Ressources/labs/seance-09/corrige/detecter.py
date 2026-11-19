"""Corrigé des trois règles de la séance 09. À lire après avoir rendu les vôtres.

Les trois règles tiennent en une vingtaine de lignes chacune. Ce qui les rend justes n'est pas leur
longueur : c'est le soin mis à ce qu'elles ne crient pas pour rien.
"""
from normaliser import collecter

FENETRE_MINUTES = 10
SEUIL_ECHECS = 10
SEUIL_OCTETS = 100 * 1024 * 1024
HEURES_CREUSES = set(range(22, 24)) | set(range(0, 7))
RESEAU_INTERNE = "10.20."


def minutes(horodatage: str) -> int:
    heure, minute = int(horodatage[11:13]), int(horodatage[14:16])
    return heure * 60 + minute


def force_brute(evenements: list[dict]) -> list[dict]:
    connexions = [e for e in evenements if e["action"] == "connexion" and e["compte"]]
    par_couple: dict[tuple, list[dict]] = {}
    for evenement in connexions:
        par_couple.setdefault((evenement["ip"], evenement["compte"]), []).append(evenement)

    alertes = []
    for (acteur, compte), suite in par_couple.items():
        suite.sort(key=lambda e: e["horodatage"])
        echecs: list[int] = []
        for evenement in suite:
            instant = minutes(evenement["horodatage"])
            # la fenêtre glisse : on oublie les échecs trop vieux pour compter dans la même salve
            echecs = [t for t in echecs if instant - t <= FENETRE_MINUTES]
            if evenement["resultat"] == "echec":
                echecs.append(instant)
            elif evenement["resultat"] == "succes" and len(echecs) >= SEUIL_ECHECS:
                alertes.append({
                    "regle": "force-brute", "horodatage": evenement["horodatage"], "acteur": acteur,
                    "compte": compte,
                    "resume": f"{len(echecs)} échecs puis une réussite en {FENETRE_MINUTES} minutes"})
                break  # une alerte par couple : l'entrée est faite, le reste est du suivi d'intrusion
    return alertes


def fichier_depose(evenements: list[dict]) -> list[dict]:
    requetes = [e for e in evenements if e["action"] == "requete"]
    deposes = {e["details"]["chemin"]: e for e in requetes
               if e["details"]["methode"] == "POST" and e["details"]["code"] == 201}

    alertes = []
    for chemin, depot in deposes.items():
        rappels = [e for e in requetes if e["details"]["chemin"] == chemin
                   and e["horodatage"] > depot["horodatage"] and e["details"]["methode"] == "GET"]
        if rappels:
            alertes.append({
                "regle": "fichier-depose", "horodatage": depot["horodatage"], "acteur": depot["ip"],
                "compte": None,
                "resume": f"{chemin} déposé puis rappelé {len(rappels)} fois"})
    return alertes


def exfiltration(evenements: list[dict]) -> list[dict]:
    alertes = []
    for evenement in evenements:
        if evenement["action"] != "transfert":
            continue
        details = evenement["details"]
        # la destination d'abord : une sauvegarde interne, si volumineuse soit-elle, ne sort pas
        if details["destination"].startswith(RESEAU_INTERNE):
            continue
        if details["octets"] < SEUIL_OCTETS or int(evenement["horodatage"][11:13]) not in HEURES_CREUSES:
            continue
        alertes.append({
            "regle": "exfiltration", "horodatage": evenement["horodatage"], "acteur": evenement["ip"],
            "compte": None,
            "resume": f"{details['octets'] // (1024 * 1024)} Mo vers {details['destination']} "
                      f"port {details['port']}"})
    return alertes


REGLES = (force_brute, fichier_depose, exfiltration)


def analyser(evenements: list[dict] | None = None) -> list[dict]:
    evenements = collecter() if evenements is None else evenements
    alertes = [alerte for regle in REGLES for alerte in regle(evenements)]
    return sorted(alertes, key=lambda a: a["horodatage"])


if __name__ == "__main__":
    for alerte in analyser():
        print(f"{alerte['horodatage']}  {alerte['regle']:16} {alerte['acteur']:18} {alerte['resume']}")
