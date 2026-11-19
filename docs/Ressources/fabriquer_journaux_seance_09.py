"""Fabrique le corpus de journaux du lab de la séance 09 (journalisation et SIEM).

    python docs/Ressources/fabriquer_journaux_seance_09.py

Ce script **ne part pas** dans l'archive de l'apprenant : il pose l'incident que le lab demande de
retrouver, et le lire donnerait la réponse. Il écrit quatre journaux dans le dossier source du lab,
que `construire_labs.py` empaquette ensuite tels quels.

Le tirage est à graine fixe : relancer le script sans l'avoir modifié réécrit exactement les mêmes
fichiers, donc la même archive. Les horodatages sont en UTC, comme ce que produit un collecteur.

L'histoire plantée, en trois temps, le 14 mars :
  1. 02:14 → 02:19  soixante échecs SSH depuis 185.203.44.19 sur le compte kone.a, puis une réussite ;
  2. 02:23          dépôt d'un fichier .php dans /uploads/ sur le portail, puis appels successifs ;
  3. 02:41          412 Mo sortants du serveur web vers cette même adresse, port 443.
Le bruit autour est volontairement traître : des échecs de connexion honnêtes (des fautes de frappe),
des 404 banals, et une sauvegarde nocturne qui déplace 900 Mo — mais vers une adresse interne. Une
règle d'exfiltration écrite à la va-vite se déclenche dessus : c'est le piège de la séance.
"""
import pathlib
import random

ICI = pathlib.Path(__file__).resolve().parent
JOURNAUX = ICI / "labs" / "seance-09" / "journaux"
GRAINE = 20260314

JOUR = "2026-03-14"
INTERNES = ["10.20.3.11", "10.20.3.12", "10.20.4.25", "10.20.4.31", "10.20.5.7"]
COMPTES = ["awa.toure", "kone.a", "yao.n", "diaby.s", "bamba.k", "sauvegarde"]
PAGES = ["/", "/connexion", "/tableau-de-bord", "/transferts", "/clients", "/rapports/mensuel",
         "/static/app.css", "/static/app.js", "/api/soldes", "/api/transferts"]
ATTAQUANT = "185.203.44.19"
COMPTE_VISE = "kone.a"
WEB = "10.20.3.11"
SAUVEGARDE_CIBLE = "10.20.9.5"  # baie interne : une exfiltration vers elle n'en est pas une


def horodatage(heure: int, minute: int, seconde: int) -> str:
    return f"{JOUR}T{heure:02d}:{minute:02d}:{seconde:02d}Z"


def ecrire(nom: str, lignes: list[str]) -> None:
    JOURNAUX.mkdir(parents=True, exist_ok=True)
    chemin = JOURNAUX / nom
    chemin.write_text("\n".join(lignes) + "\n", encoding="utf-8", newline="\n")
    print(f"{chemin.relative_to(ICI.parents[1])} : {len(lignes)} lignes")


def journal_web(de: random.Random) -> list[str]:
    """Portail de l'agence, format proche d'un access log : date, ip, méthode, chemin, code, octets."""
    lignes = []
    for heure in range(24):
        # le portail travaille aux heures de bureau ; la nuit reste calme, ce qui rend l'intrusion visible
        passages = de.randint(40, 90) if 7 <= heure <= 19 else de.randint(2, 8)
        for _ in range(passages):
            minute, seconde = de.randint(0, 59), de.randint(0, 59)
            page = de.choice(PAGES)
            code = 200 if de.random() > 0.08 else de.choice([301, 404, 404, 500])
            lignes.append(f"{horodatage(heure, minute, seconde)} {de.choice(INTERNES)} "
                          f"GET {page} {code} {de.randint(300, 9000)}")
    # 1) le dépôt du fichier, puis 2) ses appels : le même chemin revient, ce qu'aucune page ne fait
    lignes.append(f"{horodatage(2, 23, 7)} {ATTAQUANT} POST /uploads/avatar.php 201 1843")
    for minute, seconde in ((23, 41), (24, 12), (27, 3), (33, 50), (40, 18)):
        lignes.append(f"{horodatage(2, minute, seconde)} {ATTAQUANT} GET /uploads/avatar.php 200 "
                      f"{de.randint(120, 4200)}")
    return sorted(lignes)


def journal_ssh(de: random.Random) -> list[str]:
    """Passerelle d'administration : date, ip, compte, resultat."""
    lignes = []
    for heure in range(7, 20):
        for _ in range(de.randint(1, 4)):
            lignes.append(f"{horodatage(heure, de.randint(0, 59), de.randint(0, 59))} "
                          f"{de.choice(INTERNES)} {de.choice(COMPTES)} succes")
    # des échecs honnêtes : une faute de frappe, jamais plus de deux de suite, toujours en journée
    for heure, compte in ((9, "awa.toure"), (11, "diaby.s"), (14, "yao.n"), (16, "bamba.k")):
        minute = de.randint(0, 58)
        lignes.append(f"{horodatage(heure, minute, de.randint(0, 59))} {de.choice(INTERNES)} {compte} echec")
        if de.random() > 0.5:
            lignes.append(f"{horodatage(heure, minute + 1, de.randint(0, 59))} {de.choice(INTERNES)} "
                          f"{compte} echec")
        lignes.append(f"{horodatage(heure, minute + 1, 59)} {de.choice(INTERNES)} {compte} succes")
    # 1) la salve, puis la réussite : soixante échecs en cinq minutes, depuis une adresse publique
    seconde = 0
    for numero in range(60):
        minute, seconde = 14 + numero // 12, (seconde + 5) % 60
        lignes.append(f"{horodatage(2, minute, seconde)} {ATTAQUANT} {COMPTE_VISE} echec")
    lignes.append(f"{horodatage(2, 19, 36)} {ATTAQUANT} {COMPTE_VISE} succes")
    return sorted(lignes)


def journal_pare_feu(de: random.Random) -> list[str]:
    """Pare-feu en sortie : date, source, destination, port, octets, action."""
    lignes = ["date,source,destination,port,octets,action"]
    for heure in range(24):
        for _ in range(de.randint(5, 15)):
            octets = de.randint(1_000, 900_000) if 7 <= heure <= 19 else de.randint(1_000, 60_000)
            lignes.append(f"{horodatage(heure, de.randint(0, 59), de.randint(0, 59))},"
                          f"{de.choice(INTERNES)},{de.choice(['41.207.9.3', '197.234.18.7', '8.8.8.8'])},"
                          f"{de.choice([443, 443, 443, 80, 53])},{octets},autorise")
    # le piège : la sauvegarde nocturne déplace 900 Mo, mais vers la baie interne
    lignes.append(f"{horodatage(1, 5, 0)},10.20.4.25,{SAUVEGARDE_CIBLE},445,943_718_400,autorise"
                  .replace("_", ""))
    # 3) la sortie : 412 Mo du serveur web vers l'adresse de l'attaquant, en pleine nuit
    lignes.append(f"{horodatage(2, 41, 22)},{WEB},{ATTAQUANT},443,432013312,autorise")
    return [lignes[0]] + sorted(lignes[1:])


def journal_annuaire(de: random.Random) -> list[str]:
    """Annuaire Windows : date, evenement, compte, poste, resultat."""
    lignes = ["date,evenement,compte,poste,resultat"]
    for heure in range(7, 20):
        for _ in range(de.randint(3, 9)):
            compte = de.choice(COMPTES)
            lignes.append(f"{horodatage(heure, de.randint(0, 59), de.randint(0, 59))},4624,{compte},"
                          f"POSTE-{de.randint(10, 40)},succes")
    # le compte repris sert ensuite depuis le serveur web : la trace qui relie les deux journaux
    lignes.append(f"{horodatage(2, 26, 11)},4624,{COMPTE_VISE},SRV-WEB-01,succes")
    lignes.append(f"{horodatage(2, 28, 45)},4672,{COMPTE_VISE},SRV-WEB-01,succes")
    return [lignes[0]] + sorted(lignes[1:])


def main() -> None:
    de = random.Random(GRAINE)
    ecrire("web-portail.log", journal_web(de))
    ecrire("passerelle-ssh.log", journal_ssh(de))
    ecrire("pare-feu.csv", journal_pare_feu(de))
    ecrire("annuaire-windows.csv", journal_annuaire(de))


if __name__ == "__main__":
    main()
