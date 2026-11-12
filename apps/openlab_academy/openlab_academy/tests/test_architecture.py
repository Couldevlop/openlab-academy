"""Garde-fou d'architecture hexagonale : une couche ne dépend jamais d'une couche plus externe.

Le test est pur (analyse statique, aucun site Frappe) : il lit les imports de chaque module de l'app et les
compare aux dépendances autorisées. Il échoue aussi si l'analyseur cesse de détecter une violation, ce qui
éviterait un garde-fou devenu silencieux.
"""
import ast
import tempfile
import unittest
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
APP = RACINE.name

# Du plus interne au plus externe. Une couche n'importe que les couches qui la précèdent.
COUCHES = ("domain", "application", "infrastructure", "entrypoints")

# Dépendances externes interdites par couche : le domaine et l'application ignorent le cadre technique.
CADRE_INTERDIT = {"domain": ("frappe",), "application": ("frappe",)}


def _modules_importes(chemin):
    """Noms de modules importés par un fichier Python, en notation pointée."""
    arbre = ast.parse(chemin.read_text(encoding="utf-8"), filename=str(chemin))
    noms = set()
    for noeud in ast.walk(arbre):
        if isinstance(noeud, ast.Import):
            noms.update(alias.name for alias in noeud.names)
        elif isinstance(noeud, ast.ImportFrom) and noeud.level == 0 and noeud.module:
            noms.add(noeud.module)
    return noms


def _racine(nom):
    return nom.split(".")[0]


def _couche_visee(nom):
    """Couche de l'app désignée par un import absolu, sinon None."""
    morceaux = nom.split(".")
    if len(morceaux) >= 2 and morceaux[0] == APP and morceaux[1] in COUCHES:
        return morceaux[1]
    return None


def violations(racine=RACINE, couches=COUCHES):
    """Imports d'une couche vers une couche plus externe, ou vers un cadre technique interdit."""
    trouvees = []
    for rang, couche in enumerate(couches):
        dossier = racine / couche
        if not dossier.is_dir():
            continue
        autorisees = set(couches[: rang + 1])
        for chemin in sorted(dossier.rglob("*.py")):
            for nom in sorted(_modules_importes(chemin)):
                visee = _couche_visee(nom)
                if visee is not None and visee not in autorisees:
                    trouvees.append(f"{couche}/{chemin.name} importe la couche {visee}")
                elif _racine(nom) in CADRE_INTERDIT.get(couche, ()):
                    trouvees.append(f"{couche}/{chemin.name} importe {_racine(nom)}")
    return trouvees


class TestArchitecture(unittest.TestCase):
    def test_aucune_dependance_vers_une_couche_plus_externe(self):
        """Le domaine ignore l'application, l'infrastructure et Frappe ; l'application ignore l'infrastructure."""
        self.assertEqual([], violations())

    def test_l_analyseur_detecte_une_violation(self):
        """Preuve que le garde-fou mord : un domaine qui importe Frappe et l'infrastructure est signalé."""
        with tempfile.TemporaryDirectory() as dossier:
            faux = Path(dossier)
            (faux / "domain").mkdir()
            (faux / "domain" / "fuite.py").write_text(
                f"import frappe\nfrom {APP}.infrastructure import depot_frappe\n", encoding="utf-8"
            )
            constats = violations(racine=faux)
        self.assertIn("domain/fuite.py importe la couche infrastructure", constats)
        self.assertIn("domain/fuite.py importe frappe", constats)
