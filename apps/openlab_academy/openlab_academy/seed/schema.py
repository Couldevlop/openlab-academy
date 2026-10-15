"""Validation des fichiers de parcours, sans dépendance à Frappe."""
import pathlib
import re

import yaml

NIVEAUX = {"guide", "semi-guide", "autonome"}
PROJET_CHAMPS = ("titre", "duree_h", "niveau", "contexte", "objectifs", "fonctionnalites",
                 "stack", "criteres_acceptation", "exigences_specifiques", "livrables")
SALAIRE = re.compile(r"\d+\s*k\s*€", re.IGNORECASE)


class SeedError(ValueError):
    pass


def _exiger(obj: dict, champs, chemin: str, source: str) -> None:
    for champ in champs:
        if champ == "exigences_specifiques":
            manquant = champ not in obj
        else:
            manquant = obj.get(champ) in (None, "", [])
        if manquant:
            raise SeedError(f"{source}: {chemin}{champ} manquant")


def _projet(p: dict, chemin: str, source: str, modules: set[str] | None) -> None:
    _exiger(p, PROJET_CHAMPS, f"{chemin}.", source)
    if p["niveau"] not in NIVEAUX:
        raise SeedError(f"{source}: {chemin}.niveau '{p['niveau']}' hors {sorted(NIVEAUX)}")
    if modules is not None:
        _exiger(p, ("apres_module",), f"{chemin}.", source)
        if str(p["apres_module"]) not in modules:
            raise SeedError(f"{source}: {chemin}.apres_module: module '{p['apres_module']}' inexistant")


def validate(parcours: dict, source: str) -> None:
    if not isinstance(parcours, dict):
        raise SeedError(f"{source}: le fichier doit contenir un parcours (dictionnaire)")
    _exiger(parcours, ("title", "short_introduction", "description", "blocs", "portfolio", "capstone"), "", source)
    for champ in ("title", "short_introduction", "description"):
        if SALAIRE.search(str(parcours[champ])):
            raise SeedError(f"{source}: {champ}: rémunération en k€ interdite")
    modules: set[str] = set()
    for i, bloc in enumerate(parcours["blocs"]):
        _exiger(bloc, ("title", "modules"), f"blocs[{i}].", source)
        for j, m in enumerate(bloc["modules"]):
            _exiger(m, ("num", "title", "contenu", "livrable"), f"blocs[{i}].modules[{j}].", source)
            modules.add(str(m["num"]))
    if len(parcours["portfolio"]) != 10:
        raise SeedError(f"{source}: portfolio: 10 projets attendus, {len(parcours['portfolio'])} trouvés")
    for k, p in enumerate(parcours["portfolio"]):
        _projet(p, f"portfolio[{k}]", source, modules)
    _projet(parcours["capstone"], "capstone", source, None)


def load_dir(path: pathlib.Path) -> list[dict]:
    resultats = []
    for fichier in sorted(path.glob("*.yaml")):
        with fichier.open(encoding="utf-8") as f:
            try:
                data = yaml.safe_load(f)
            except yaml.YAMLError as e:
                raise SeedError(f"{fichier.name}: YAML invalide ou non sûr ({e.__class__.__name__})") from e
        validate(data, fichier.name)
        resultats.append(data)
    return resultats
