"""Vérifie votre travail et délivre le code à joindre au livrable.

    python verifier.py

Le code n'est pas une note : il atteste que vos trois règles, passées sur le corpus livré, ont trouvé
l'incident et rien d'autre. Le reste du livrable — la chronologie de l'intrusion, ce que vous auriez
collecté en plus, ce que vous auriez gardé et combien de temps — se rédige et se corrige à la main.
"""
import hashlib

import detecter

ATTENDU = (
    ("force-brute", "2026-03-14T02:19:36Z", "185.203.44.19"),
    ("fichier-depose", "2026-03-14T02:23:07Z", "185.203.44.19"),
    ("exfiltration", "2026-03-14T02:41:22Z", "10.20.3.11"),
)
SEL = "openlab-academy/lab-seance-09"


def empreinte(alertes) -> str:
    matiere = SEL + "|" + "|".join(f"{r}@{h}@{a}" for r, h, a in alertes)
    return hashlib.sha256(matiere.encode("utf-8")).hexdigest()[:12].upper()


def main() -> int:
    try:
        alertes = detecter.analyser()
    except NotImplementedError as manque:
        print(f"Règle non écrite : {manque}")
        return 1

    trouve = tuple((a["regle"], a["horodatage"], a["acteur"]) for a in alertes)
    for ligne in alertes:
        print(f"  {ligne['horodatage']}  {ligne['regle']:16} {ligne['acteur']:18} {ligne['resume']}")

    if trouve == ATTENDU:
        print(f"\nTrois alertes, les bonnes, et aucune fausse. Code du lab : {empreinte(ATTENDU)}")
        return 0

    manquantes = [r for r in ATTENDU if r not in trouve]
    en_trop = [r for r in trouve if r not in ATTENDU]
    print()
    for regle, horodatage, acteur in manquantes:
        print(f"Manque : {regle} à {horodatage} ({acteur})")
    for regle, horodatage, acteur in en_trop:
        print(f"En trop : {regle} à {horodatage} ({acteur}) — une fausse alerte coûte aussi cher")
    print("\nPas de code tant que le compte n'y est pas.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
