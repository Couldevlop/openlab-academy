#!/usr/bin/env python3
"""Repartit les modules de test de l'app en lots de cout comparable, pour les executer en parallele.

La suite tient en trois quarts d'heure sur un seul coureur, pour un delai de job de cinquante minutes :
le verdict devenait un tirage au sort. Deux lots ramenent chacun vers la demi-heure.

    usage : lots_de_tests.py <dossier des tests> --lot N --sur M [--compter]
            lots_de_tests.py <dossier des tests> --mesurer <journal de la CI>

La liste des modules est toujours lue sur le disque, jamais ecrite en dur : un module de test ajoute
entre dans un lot de lui-meme, et ne peut donc pas etre oublie en silence, ce qui serait le pire des
defauts d'une suite decoupee. La repartition est deterministe, memes lots pour une meme entree, pour
qu'un echec soit reproductible.

Le poids d'un module est **mesure**, pas devine : `couts_de_tests.json` porte le temps que chaque
module a reellement pris dans la chaine d'integration. L'estimation d'avant -- un cout par test, trente
fois plus cher si le nom du module portait `_frappe` ou `_api` -- se trompait d'un facteur deux cents
sur `test_branchement_reglages`, de cent sur `test_installation`, de soixante sur `test_annonce` : trois
modules d'integration que leur nom ne declarait pas, soit dix minutes de poids que le repartiteur ne
voyait pas. Elle ne sert plus que de dernier recours, pour un module jamais mesure.

Un module absent de la table n'est jamais ecarte : il recoit l'estimation, et le repartiteur le dit sur
la sortie d'erreur.

Un seul releve ne suffit pas : la table garde la **moyenne** des executions mesurees, pas la derniere.
Chaque nouveau releve s'y fond, et les executions fondues sont inscrites dedans :

    gh run view <id> --log | python .github/scripts/lots_de_tests.py <dossier> --mesurer - --execution <id>

Il faut dire ce que cette ponderation ne peut pas faire, sous peine de lui preter un pouvoir qu'elle
n'a pas. Les deux lots tournent sur deux coureurs distincts, dont la vitesse varie de pres de moitie.
A l'execution 44559182784, les treize modules du lot 2 ont **tous** mis au moins 1,10 fois leur temps
moyen, 1,44 fois a la mediane, quand ceux du lot 1 etaient a 1,05 : la suite entiere est passee de 42
a 55,9 min. Ce n'est pas du bruit par module, c'est une machine plus lente, et aucune ponderation ne
la rattrape -- les lots etaient prevus a 25,1 et 25,2 min, ils ont mis 27,1 et 37,0.

Ce que la table garantit est donc plus modeste, et c'etait le vrai defaut : aucun module ne pese deux
cents fois moins que son cout reel, donc aucun lot ne peut recevoir dix minutes de travail invisible.
L'equilibre en temps d'horloge se gagne ailleurs : en raccourcissant un lot, pas en affinant sa pesee.
C'est aussi la vraie raison de passer a trois lots -- non pour equilibrer, mais pour qu'un coureur
lent ne puisse plus approcher le delai de cinquante minutes.
"""
import argparse
import ast
import json
import pathlib
import re
import sys

PAQUET = "openlab_academy.tests"
TABLE = pathlib.Path(__file__).resolve().parent / "couts_de_tests.json"
# chaque module paie l'amorcage du site avant son premier test : un cout fixe que le temps mesure,
# qui ne compte que l'execution des tests, ne porte pas. Mesure a six secondes par module.
AMORCAGE = 6.0
# derniers recours, pour un module jamais mesure. Volontairement pessimistes : surestimer un module
# inconnu le pose seul dans son lot, le sous-estimer le fait tomber au mauvais endroit sans qu'on le voie.
ESTIMATION_INTEGRATION = 4.0
ESTIMATION_DOMAINE = 0.15

JOURNAL = re.compile(r"\[" + re.escape(PAQUET) + r"\.(test_[a-z0-9_]+)\] Ran (\d+) tests? in ([0-9.]+)s")


def tests_du_module(chemin: pathlib.Path) -> int:
    """Nombre de methodes de test du module, lues sans l'importer (frappe n'est pas installe ici)."""
    arbre = ast.parse(chemin.read_text(encoding="utf-8"))
    return sum(1 for noeud in ast.walk(arbre)
               if isinstance(noeud, ast.FunctionDef) and noeud.name.startswith("test_"))


def table() -> dict:
    """La table des couts, vide si le fichier manque."""
    if not TABLE.is_file():
        return {"mesure": {"executions": []}, "secondes": {}}
    return json.loads(TABLE.read_text(encoding="utf-8"))


def mesures() -> dict[str, float]:
    """Le temps moyen mesure de chaque module, vide si la table manque."""
    return table().get("secondes", {})


def estimation(module: str, nombre: int) -> float:
    """Poids d'un module jamais mesure, d'apres son nom et son nombre de tests."""
    integration = "_frappe" in module or "_api" in module
    return nombre * (ESTIMATION_INTEGRATION if integration else ESTIMATION_DOMAINE)


def modules(dossier: pathlib.Path, connus: dict[str, float] | None = None) -> dict[str, tuple[int, float]]:
    """Chaque module de test du dossier, avec son nombre de tests et son poids en secondes."""
    connus = mesures() if connus is None else connus
    trouves = {}
    for chemin in sorted(dossier.glob("test_*.py")):
        nombre = tests_du_module(chemin)
        if chemin.stem in connus:
            poids = connus[chemin.stem] + AMORCAGE
        else:
            poids = estimation(chemin.stem, nombre) + AMORCAGE
            print(f"{chemin.stem} : jamais mesure, poids estime a {poids:.1f}s. Refaire la table avec "
                  f"--mesurer apres la prochaine execution complete.", file=sys.stderr)
        trouves[chemin.stem] = (nombre, poids)
    return trouves


def repartir(trouves: dict[str, tuple[int, float]], sur: int) -> list[list[str]]:
    """Le module le plus couteux va au lot le moins charge. A cout egal, l'ordre alphabetique tranche,
    sans quoi deux executions pourraient repartir differemment et rendre un echec irreproductible."""
    lots: list[list[str]] = [[] for _ in range(sur)]
    charges = [0.0] * sur
    for module, (_, cout) in sorted(trouves.items(), key=lambda kv: (-kv[1][1], kv[0])):
        cible = min(range(sur), key=lambda i: (charges[i], i))
        lots[cible].append(module)
        charges[cible] += cout
    return lots


def mesurer(journal: str) -> dict[str, float]:
    """Le temps de chaque module, lu dans le journal d'une execution de la chaine d'integration.

    Un module execute deux fois dans le meme journal -- une reprise, deux lots qui se recoupent --
    garde le temps le plus long : le repartiteur doit se tromper du cote prudent.
    """
    releve: dict[str, float] = {}
    for module, _, secondes in JOURNAL.findall(journal):
        releve[module] = max(releve.get(module, 0.0), round(float(secondes), 1))
    return releve


def fondre(ancienne: dict, releve: dict[str, float], execution: str) -> dict:
    """La table mise a jour : moyenne du releve avec ce qui etait deja mesure.

    Un module que ce releve ne porte pas garde sa valeur : une execution incomplete ne doit pas
    effacer ce qu'on savait. Un module nouveau entre avec son premier temps.
    """
    executions = [e for e in ancienne.get("mesure", {}).get("executions", []) if e != execution]
    n = len(executions)
    secondes = dict(ancienne.get("secondes", {}))
    for module, temps in releve.items():
        ancien = secondes.get(module)
        secondes[module] = round(temps if ancien is None or n == 0 else (ancien * n + temps) / (n + 1), 1)
    return {"mesure": {"executions": executions + [execution], "amorcage_par_module_s": AMORCAGE},
            "secondes": dict(sorted(secondes.items()))}


def _ecrire_table(donnees: dict) -> None:
    TABLE.write_text(json.dumps(donnees, indent=2) + "\n", encoding="utf-8", newline="\n")


def main() -> int:
    # fin de ligne LF quelle que soit la plateforme : la liste est consommee par un shell, et un retour
    # chariot colle au nom du module le rendrait introuvable
    sys.stdout.reconfigure(newline="\n")

    a = argparse.ArgumentParser(description=__doc__)
    a.add_argument("dossier", type=pathlib.Path)
    a.add_argument("--lot", type=int)
    a.add_argument("--sur", type=int)
    a.add_argument("--compter", action="store_true")
    a.add_argument("--mesurer", metavar="JOURNAL",
                   help="refait la table des couts depuis un journal de la CI ; « - » pour l'entree standard")
    a.add_argument("--execution", metavar="ID",
                   help="identifiant de l'execution mesuree, inscrit dans la table : sans lui, la "
                        "provenance des couts se perd et on ne sait plus de quand ils datent")
    args = a.parse_args()

    if not args.dossier.is_dir():
        print(f"dossier de tests introuvable : {args.dossier}", file=sys.stderr)
        return 2

    if args.mesurer:
        texte = sys.stdin.read() if args.mesurer == "-" else pathlib.Path(args.mesurer).read_text(
            encoding="utf-8", errors="replace")
        releve = mesurer(texte)
        if not releve:
            print("aucun temps de module dans ce journal", file=sys.stderr)
            return 1
        presents = {c.stem for c in args.dossier.glob("test_*.py")}
        for absent in sorted(presents - set(releve)):
            print(f"{absent} : absent du journal, il gardera son estimation", file=sys.stderr)
        donnees = fondre(table(), releve, args.execution or args.mesurer)
        _ecrire_table(donnees)
        secondes, executions = donnees["secondes"], donnees["mesure"]["executions"]
        print(f"{TABLE.name} : {len(secondes)} modules, {sum(secondes.values()) / 60:.1f} min de tests, "
              f"moyenne de {len(executions)} execution(s)")
        return 0

    if args.lot is None or args.sur is None:
        print("--lot et --sur sont requis hors de --mesurer", file=sys.stderr)
        return 2
    if not 1 <= args.lot <= args.sur:
        print(f"lot {args.lot} hors de 1..{args.sur}", file=sys.stderr)
        return 2

    trouves = modules(args.dossier)
    if not trouves:
        print(f"aucun module test_*.py dans {args.dossier}", file=sys.stderr)
        return 1

    lots = repartir(trouves, args.sur)
    places = [module for lot in lots for module in lot]
    if len(places) != len(trouves) or len(set(places)) != len(trouves):
        print("repartition incomplete ou chevauchante", file=sys.stderr)
        return 1

    mien = sorted(lots[args.lot - 1])
    if args.compter:
        print(sum(trouves[m][0] for m in mien))
    else:
        for module in mien:
            print(f"{PAQUET}.{module}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
