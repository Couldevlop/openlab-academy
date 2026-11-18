#!/usr/bin/env python3
"""Repartit les modules de test de l'app en lots de cout comparable, pour les executer en parallele.

La suite tient en une heure sur un seul coureur, soit exactement le delai du job : le verdict devenait un
tirage au sort. Deux lots ramenent chacun vers la demi-heure.

La liste des modules est toujours lue sur le disque, jamais ecrite en dur : un module de test ajoute entre
dans un lot de lui-meme, et ne peut donc pas etre oublie en silence, ce qui serait le pire des defauts d'une
suite decoupee. La repartition est deterministe, memes lots pour une meme entree, pour qu'un echec soit
reproductible, et ponderee : un test d'integration sur site reel coute environ trente fois un test de
domaine, et une repartition au nombre de modules mettrait tout le poids d'un cote.

    usage : lots_de_tests.py <dossier des tests> --lot N --sur M [--compter]

Sans --compter, ecrit les modules du lot, un par ligne, en nom pointe. Avec, ecrit le nombre de tests
attendus du lot : le job s'en sert pour verifier qu'aucun module n'a ete execute a vide.
"""
import argparse
import ast
import pathlib
import sys

PAQUET = "openlab_academy.tests"
# un test sur site reel paie la creation d'un parcours complet ; un test de domaine ne paie rien
COUT_INTEGRATION = 4.0
COUT_DOMAINE = 0.15


def _integration(module: str) -> bool:
    return "_frappe" in module or "_api" in module


def tests_du_module(chemin: pathlib.Path) -> int:
    """Nombre de methodes de test du module, lues sans l'importer (frappe n'est pas installe ici)."""
    arbre = ast.parse(chemin.read_text(encoding="utf-8"))
    return sum(1 for noeud in ast.walk(arbre)
               if isinstance(noeud, ast.FunctionDef) and noeud.name.startswith("test_"))


def modules(dossier: pathlib.Path) -> dict[str, tuple[int, float]]:
    """Chaque module de test du dossier, avec son nombre de tests et son cout estime."""
    trouves = {}
    for chemin in sorted(dossier.glob("test_*.py")):
        nombre = tests_du_module(chemin)
        cout = nombre * (COUT_INTEGRATION if _integration(chemin.stem) else COUT_DOMAINE)
        trouves[chemin.stem] = (nombre, cout)
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


def main() -> int:
    # fin de ligne LF quelle que soit la plateforme : la liste est consommee par un shell, et un retour
    # chariot colle au nom du module le rendrait introuvable
    sys.stdout.reconfigure(newline="\n")

    a = argparse.ArgumentParser()
    a.add_argument("dossier", type=pathlib.Path)
    a.add_argument("--lot", type=int, required=True)
    a.add_argument("--sur", type=int, required=True)
    a.add_argument("--compter", action="store_true")
    args = a.parse_args()

    if not 1 <= args.lot <= args.sur:
        print(f"lot {args.lot} hors de 1..{args.sur}", file=sys.stderr)
        return 2
    if not args.dossier.is_dir():
        print(f"dossier de tests introuvable : {args.dossier}", file=sys.stderr)
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
