"""Collecte et normalisation : quatre journaux de formats différents, un seul format d'événement.

Un SIEM ne sait rien faire de journaux hétérogènes. La première moitié du métier consiste à les
ramener à une forme commune, où « qui », « quoi », « d'où », « combien » occupent toujours la même
place. Le reste de la séance — corrélation, détection, tableau de bord — ne tient que sur ce travail.

L'événement normalisé est un dictionnaire à six clés, toujours les mêmes :

    {
        "horodatage": "2026-03-14T02:19:36Z",  # UTC, tel quel
        "source": "ssh",                        # web | ssh | pare-feu | annuaire
        "ip": "185.203.44.19",                  # adresse à l'origine, ou None
        "compte": "kone.a",                     # compte concerné, ou None
        "action": "connexion",                  # connexion | requete | transfert | privilege
        "resultat": "echec",                    # succes | echec | None
        "details": {...},                       # ce qui est propre à la source
    }

Corrigé : les quatre lecteurs. À lire après avoir rendu le vôtre.
"""
import csv
import pathlib

_ICI = pathlib.Path(__file__).resolve().parent
# le corrigé est rangé un cran plus bas que les journaux : on accepte les deux emplacements
JOURNAUX = next(d / "journaux" for d in (_ICI, _ICI.parent) if (d / "journaux").is_dir())


def _evenement(horodatage, source, action, ip=None, compte=None, resultat=None, **details):
    return {"horodatage": horodatage, "source": source, "ip": ip, "compte": compte,
            "action": action, "resultat": resultat, "details": details}


def lire_web(texte: str) -> list[dict]:
    """Portail : « date ip METHODE chemin code octets »."""
    evenements = []
    for ligne in texte.splitlines():
        if not ligne.strip():
            continue
        date, ip, methode, chemin, code, octets = ligne.split()
        evenements.append(_evenement(
            date, "web", "requete", ip=ip,
            resultat="succes" if code.startswith(("2", "3")) else "echec",
            methode=methode, chemin=chemin, code=int(code), octets=int(octets)))
    return evenements


def lire_ssh(texte: str) -> list[dict]:
    """Passerelle d'administration : « date ip compte resultat »."""
    evenements = []
    for ligne in texte.splitlines():
        if not ligne.strip():
            continue
        date, ip, compte, resultat = ligne.split()
        evenements.append(_evenement(date, "ssh", "connexion", ip=ip, compte=compte, resultat=resultat))
    return evenements


def lire_pare_feu(texte: str) -> list[dict]:
    """Pare-feu en sortie : CSV « date,source,destination,port,octets,action »."""
    evenements = []
    for ligne in csv.DictReader(texte.splitlines()):
        evenements.append(_evenement(
            ligne["date"], "pare-feu", "transfert", ip=ligne["source"],
            resultat="succes" if ligne["action"] == "autorise" else "echec",
            destination=ligne["destination"], port=int(ligne["port"]), octets=int(ligne["octets"])))
    return evenements


def lire_annuaire(texte: str) -> list[dict]:
    """Annuaire Windows : CSV « date,evenement,compte,poste,resultat ».

    Rendez une liste d'événements normalisés, un par ligne du CSV :
      - `action` vaut "connexion" pour l'événement 4624, "privilege" pour 4672 ;
      - `compte` et `resultat` viennent des colonnes du même nom ;
      - `ip` reste None : l'annuaire ne journalise pas l'adresse, il journalise le poste ;
      - rangez le poste et le numéro d'événement dans les détails (`poste=`, `evenement=`).

    Une détection de la séance a besoin du poste : sans lui, impossible de voir qu'un compte
    d'agence s'est connecté depuis un serveur sur lequel il n'a rien à faire.
    """
    evenements = []
    for ligne in csv.DictReader(texte.splitlines()):
        evenements.append(_evenement(
            ligne["date"], "annuaire",
            "privilege" if ligne["evenement"] == "4672" else "connexion",
            compte=ligne["compte"], resultat=ligne["resultat"],
            poste=ligne["poste"], evenement=int(ligne["evenement"])))
    return evenements


LECTEURS = {"web-portail.log": lire_web, "passerelle-ssh.log": lire_ssh,
            "pare-feu.csv": lire_pare_feu, "annuaire-windows.csv": lire_annuaire}


def collecter(dossier: pathlib.Path = JOURNAUX) -> list[dict]:
    """Tous les journaux, normalisés et remis dans l'ordre du temps — l'ordre du SIEM."""
    evenements = []
    for nom, lecteur in LECTEURS.items():
        evenements += lecteur((dossier / nom).read_text(encoding="utf-8"))
    return sorted(evenements, key=lambda e: e["horodatage"])


if __name__ == "__main__":
    tout = collecter()
    print(f"{len(tout)} événements collectés")
    for source in sorted({e['source'] for e in tout}):
        print(f"  {source:10} {sum(1 for e in tout if e['source'] == source):5}")
