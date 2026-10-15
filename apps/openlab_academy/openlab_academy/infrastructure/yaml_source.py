"""Adaptateur d'entrée : fichiers YAML de parcours -> entités du domaine."""
import pathlib

import yaml

from openlab_academy.domain.parcours import Bloc, Module, Niveau, Parcours, ParcoursInvalide, Projet

PARCOURS_DIR = pathlib.Path(__file__).parents[1] / "data" / "parcours"
_LISTES_PROJET = ("objectifs", "fonctionnalites", "stack", "criteres_acceptation", "livrables")


class FormatInvalide(ValueError):
    """Fichier de parcours mal formé ou contraire aux invariants du domaine."""


class _Lecteur:
    def __init__(self, source: str):
        self.source = source

    def exiger(self, obj: dict, champ: str, chemin: str):
        valeur = obj.get(champ)
        if valeur in (None, "", []):
            raise FormatInvalide(f"{self.source}: {chemin}{champ} manquant")
        return valeur

    def textes(self, valeurs, chemin: str) -> tuple[str, ...]:
        for i, v in enumerate(valeurs):
            if not isinstance(v, str):
                raise FormatInvalide(f"{self.source}: {chemin}[{i}] doit être un texte (« : » non quoté ?)")
        return tuple(valeurs)

    def module(self, m: dict, chemin: str) -> Module:
        return Module(*(str(self.exiger(m, c, chemin)) for c in ("num", "title", "contenu", "livrable")))

    def projet(self, p: dict, chemin: str, portfolio: bool) -> Projet:
        listes = {c: self.textes(self.exiger(p, c, chemin), f"{chemin}{c}") for c in _LISTES_PROJET}
        if "exigences_specifiques" not in p:
            raise FormatInvalide(f"{self.source}: {chemin}exigences_specifiques manquant")
        niveau = self.exiger(p, "niveau", chemin)
        try:
            niveau = Niveau(niveau)
        except ValueError:
            raise FormatInvalide(f"{self.source}: {chemin}niveau '{niveau}' inconnu") from None
        duree = self.exiger(p, "duree_h", chemin)
        if not isinstance(duree, int):
            raise FormatInvalide(f"{self.source}: {chemin}duree_h doit être un entier")
        apres = p.get("apres_module")
        return Projet(
            titre=str(self.exiger(p, "titre", chemin)), duree_h=duree, niveau=niveau,
            contexte=str(self.exiger(p, "contexte", chemin)),
            exigences_specifiques=self.textes(p["exigences_specifiques"] or (), f"{chemin}exigences_specifiques"),
            apres_module=None if apres is None else str(apres), **listes,
        )

    def parcours(self, d) -> Parcours:
        if not isinstance(d, dict):
            raise FormatInvalide(f"{self.source}: le fichier doit contenir un parcours (dictionnaire)")
        blocs = tuple(
            Bloc(str(self.exiger(b, "title", f"blocs[{i}].")),
                 tuple(self.module(m, f"blocs[{i}].modules[{j}].")
                       for j, m in enumerate(self.exiger(b, "modules", f"blocs[{i}]."))))
            for i, b in enumerate(self.exiger(d, "blocs", "")))
        portfolio = tuple(self.projet(p, f"portfolio[{k}].", True)
                          for k, p in enumerate(self.exiger(d, "portfolio", "")))
        return Parcours(
            title=str(self.exiger(d, "title", "")),
            short_introduction=str(self.exiger(d, "short_introduction", "")),
            description=str(self.exiger(d, "description", "")),
            tags=self.textes(d.get("tags") or (), "tags"), card_gradient=str(d.get("card_gradient", "Blue")),
            blocs=blocs, portfolio=portfolio,
            capstone=self.projet(self.exiger(d, "capstone", ""), "capstone.", False),
        )


def depuis_dict(d, source: str) -> Parcours:
    try:
        return _Lecteur(source).parcours(d)
    except ParcoursInvalide as e:
        raise FormatInvalide(f"{source}: {e}") from e


def charger_dossier(dossier: pathlib.Path) -> list[Parcours]:
    lot = []
    for fichier in sorted(dossier.glob("*.yaml")):
        try:
            data = yaml.safe_load(fichier.read_text(encoding="utf-8"))
        except yaml.YAMLError as e:
            raise FormatInvalide(f"{fichier.name}: YAML invalide ou non sûr ({e.__class__.__name__})") from e
        lot.append(depuis_dict(data, fichier.name))
    return lot
