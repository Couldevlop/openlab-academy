"""Construit les archives du fil rouge : les carnets d'exercices, et le dépôt des autres séances.

Un carnet est du code, pas une pièce jointe : son contenu vit dans
`docs/Ressources/notebooks/cellules.py`, le dépôt qui l'accompagne est rejoué depuis le
parcours lui-même, et l'archive produite est déterministe, octet pour octet. Deux
exécutions donnent le même fichier, une correction se lit dans un diff, et personne n'a
besoin d'un compte ni d'un outil extérieur pour rouvrir un carnet dans deux ans.

    python docs/Ressources/construire_notebooks.py            # écrit les archives
    python docs/Ressources/construire_notebooks.py --verifier  # échoue si elles ont bougé

Le dépôt livré est extrait des blocs de code du parcours dont le titre nomme un fichier,
jusqu'à la séance concernée : ce que l'apprenant ouvre est exactement ce que le cours lui a
fait écrire. Toute séance qui écrit une partie du fil rouge repart donc avec un
téléchargement : son carnet quand elle en a un, son dépôt sinon.
"""
from __future__ import annotations

import hashlib
import io
import json
import pathlib
import re
import sys
import zipfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent / "notebooks"))

import yaml  # noqa: E402

from cellules import AMORCE, SEANCES  # noqa: E402

RACINE = pathlib.Path(__file__).resolve().parents[2]
APPLICATION = RACINE / "apps/openlab_academy/openlab_academy"
PARCOURS = APPLICATION / "data/parcours/06-ia-agentique.yaml"
SOCLE = APPLICATION / "data/ressources/socle-ia-agentique-v0.3.0.zip"
DESTINATION = APPLICATION / "data/ressources"
PREFIXE_SOCLE = "openlab-academy-agentic-starter"

CHEMIN_FICHIER = re.compile(r"^([\w./-]+\.(?:py|md|json|csv|txt))(?:\s+et\s+([\w./-]+\.py))?\b")
DEPUIS_LE_SOCLE = ["data/factures_fictives.csv", "contracts/contrats_outils.json"]
# Le cours ecrit parfois un fichier avant celui dont il depend : actions.py, ecrit en
# seance 5, importe l'etat ecrit en seance 8. Le carnet livre donc ces dependances,
# sans quoi le depot ne s'importe pas.
COMPLEMENTS = {"06": ["recouvrement/etat.py", "recouvrement/trace.py"],
               "07": ["recouvrement/etat.py", "recouvrement/trace.py"]}
HORODATAGE = (2026, 1, 1, 0, 0, 0)  # date fixe : l'archive ne doit pas changer avec l'heure
# La séance 5 garde l'archive de départ du socle : son dépôt de fin de séance en est le sous-ensemble.
SANS_DEPOT = {"05"}


def _parcours() -> dict:
    return yaml.safe_load(PARCOURS.read_text(encoding="utf-8"))


def _modules(donnees: dict):
    for bloc in donnees["blocs"]:
        yield from bloc["modules"]


def depot(donnees: dict, jusqua: int) -> dict[str, str]:
    """Les fichiers du fil rouge tels qu'ils existent à la fin de la séance demandée."""
    fichiers: dict[str, str] = {}
    attendus = set(COMPLEMENTS.get(f"{jusqua:02d}", ()))
    for module in _modules(donnees):
        tardif = int(module["num"]) > jusqua
        for section in module.get("cours") or []:
            for code in section.get("code") or []:
                trouve = CHEMIN_FICHIER.match(code["titre"])
                if not trouve or trouve.group(2):
                    continue
                if tardif and trouve.group(1) not in attendus:
                    continue
                fichiers[trouve.group(1)] = code["source"]
    with zipfile.ZipFile(SOCLE) as archive:
        for chemin in DEPUIS_LE_SOCLE:
            fichiers[chemin] = archive.read(f"{PREFIXE_SOCLE}/{chemin}").decode("utf-8-sig")
    if jusqua >= 9:
        fichiers["contracts/contrats_outils.json"] = _contrats_complets(
            donnees, fichiers["contracts/contrats_outils.json"])
    return fichiers


def _contrats_complets(donnees: dict, brut: str) -> str:
    """Le sixième outil arrive en séance 9 : son contrat rejoint le fichier du socle."""
    contrats = json.loads(brut)
    connus = {outil["name"] for outil in contrats["tools"]}
    for module in _modules(donnees):
        for section in module.get("cours") or []:
            for code in section.get("code") or []:
                if code["langage"] != "json" or "contrats_outils.json" not in code["titre"]:
                    continue
                ajout = json.loads(code["source"])
                if ajout["name"] not in connus:
                    contrats["tools"].append(ajout)
                    connus.add(ajout["name"])
    return json.dumps(contrats, ensure_ascii=False, indent=2) + "\n"


def seances_du_fil_rouge(donnees: dict) -> dict[str, str]:
    """{num: titre} des séances qui écrivent un fichier du fil rouge : chacune a droit à un téléchargement."""
    seances = {}
    for module in _modules(donnees):
        ecrit = any(CHEMIN_FICHIER.match(code["titre"])
                    for section in module.get("cours") or []
                    for code in section.get("code") or [])
        if ecrit:
            seances[module["num"]] = module["title"]
    return seances


def carnet(num: str, titre_module: str) -> str:
    """Le carnet au format Jupyter, sans sortie enregistrée et sans identifiant aléatoire."""
    titre, introduction, blocs = SEANCES[num]
    cellules = [
        _markdown(f"# Séance {int(num)} — {titre}\n\n{introduction}\n\n"
                  "Les cellules s'exécutent dans l'ordre, hors ligne, sans clé ni service "
                  "distant. Le dépôt du fil rouge est livré dans la même archive : ouvrez ce "
                  "carnet depuis sa racine."),
        _code(AMORCE),
    ]
    for texte, code in blocs:
        cellules.append(_markdown(texte))
        if code:
            cellules.append(_code(code))
    carnet = {
        "cells": cellules,
        "metadata": {
            "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
            "language_info": {"name": "python"},
            "openlab": {"parcours": "IA agentique", "seance": num, "titre": titre_module},
        },
        "nbformat": 4,
        "nbformat_minor": 5,
    }
    return json.dumps(carnet, ensure_ascii=False, indent=1, sort_keys=True) + "\n"


def _markdown(texte: str) -> dict:
    return {"cell_type": "markdown", "metadata": {}, "source": _lignes(texte)}


def _code(source: str) -> dict:
    return {"cell_type": "code", "execution_count": None, "metadata": {},
            "outputs": [], "source": _lignes(source)}


def _lignes(texte: str) -> list[str]:
    lignes = texte.split("\n")
    return [ligne + "\n" for ligne in lignes[:-1]] + [lignes[-1]]


def lisezmoi(num: str, titre: str) -> str:
    return (f"# Carnet d'exercices — séance {int(num)}\n\n"
            f"{titre}\n\n"
            "## Pour démarrer\n\n"
            "```bash\n"
            "python -m venv .venv && . .venv/bin/activate   # Windows : .venv\\\\Scripts\\\\activate\n"
            "pip install jupyterlab pydantic pytest\n"
            f"jupyter lab seance-{num}.ipynb\n"
            "```\n\n"
            "Le dépôt du fil rouge est livré à côté du carnet, dans l'état où le cours le laisse "
            f"à la fin de la séance {int(num)}. Ouvrez le carnet depuis cette racine : les chemins "
            "`data/`, `connaissances/` et `contracts/` en dépendent.\n\n"
            "## Ce qu'il contient\n\n"
            "- `seance-" + num + ".ipynb` : le carnet, à exécuter dans l'ordre ;\n"
            "- `recouvrement/`, `tests/` : le code du fil rouge, identique à celui du cours ;\n"
            "- `data/`, `connaissances/`, `contracts/` : les données du fil rouge, fictives.\n\n"
            "Aucune cellule n'appelle de service distant et aucune clé n'est nécessaire.\n"
            "Rien n'est envoyé : la seule écriture possible est une relance simulée, locale.\n")


def lisezmoi_depot(num: str, titre: str) -> str:
    windows = "# Windows : .venv" + chr(92) + "Scripts" + chr(92) + "activate"
    return "\n".join([
        f"# Dépôt du fil rouge — séance {int(num)}", "",
        titre, "",
        "Le code de l'agent de recouvrement, dans l'état où le cours le laisse à la fin de la "
        f"séance {int(num)} : ni plus, ni moins que ce que la séance vous a fait écrire.", "",
        "## Pour l'ouvrir", "",
        "```bash",
        f"python -m venv .venv && . .venv/bin/activate   {windows}",
        "pip install pydantic pytest",
        "python -m pytest",
        "```", "",
        "Lancez les commandes depuis cette racine : les chemins `data/`, `connaissances/` et "
        "`contracts/` en dépendent. Certaines séances ajoutent une dépendance (LangGraph, CrewAI, "
        "le client MCP) : le cours le dit au moment où elle sert.", "",
        "Aucun appel à un service distant n'est nécessaire, et aucune clé : les données sont fictives.",
        "",
    ])


def archive_depot(num: str, donnees: dict) -> bytes:
    """Le dépôt seul, pour une séance du fil rouge sans carnet d'exercices rédigé."""
    titre = next(m["title"] for m in _modules(donnees) if m["num"] == num)
    contenu = {"LISEZMOI.md": lisezmoi_depot(num, titre)}
    contenu.update(depot(donnees, int(num)))
    return _zip(f"depot-seance-{num}", contenu)


def archive(num: str, donnees: dict) -> bytes:
    titre = next(m["title"] for m in _modules(donnees) if m["num"] == num)
    contenu = {f"seance-{num}.ipynb": carnet(num, titre), "LISEZMOI.md": lisezmoi(num, titre)}
    contenu.update(depot(donnees, int(num)))
    return _zip(f"carnet-seance-{num}", contenu)


def _zip(racine: str, contenu: dict[str, str]) -> bytes:
    tampon = io.BytesIO()
    with zipfile.ZipFile(tampon, "w", zipfile.ZIP_DEFLATED) as zip_:
        for chemin in sorted(contenu):
            info = zipfile.ZipInfo(f"{racine}/{chemin}", HORODATAGE)
            info.external_attr = 0o644 << 16
            info.compress_type = zipfile.ZIP_DEFLATED
            zip_.writestr(info, contenu[chemin].encode("utf-8"))
    return tampon.getvalue()


def main() -> int:
    verifier = "--verifier" in sys.argv
    donnees = _parcours()
    ecarts = 0
    autres = sorted(set(seances_du_fil_rouge(donnees)) - set(SEANCES) - SANS_DEPOT)
    travaux = [(f"carnet-seance-{num}.zip", archive(num, donnees)) for num in sorted(SEANCES)]
    travaux += [(f"depot-seance-{num}.zip", archive_depot(num, donnees)) for num in autres]
    for nom, contenu in travaux:
        cible = DESTINATION / nom
        empreinte = hashlib.sha256(contenu).hexdigest()[:12]
        if verifier:
            actuel = cible.read_bytes() if cible.exists() else b""
            etat = "identique" if actuel == contenu else "DIFFERENT"
            ecarts += etat == "DIFFERENT"
            print(f"  {etat:10} {cible.name}  {empreinte}")
        else:
            cible.write_bytes(contenu)
            print(f"  écrit      {cible.name}  {len(contenu):6} octets  {empreinte}")
    if verifier and ecarts:
        print(f"{ecarts} archive(s) à reconstruire : "
              "python docs/Ressources/construire_notebooks.py")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
