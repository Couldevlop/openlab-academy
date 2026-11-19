"""Construit les dépôts du jour du parcours « Bases de Python, jour après jour ».

    python docs/Ressources/construire_depots_python.py            # écrit les archives
    python docs/Ressources/construire_depots_python.py --verifier  # échoue si une archive a bougé
    python docs/Ressources/construire_depots_python.py --eprouver  # rouge au départ, vert sur la solution

Chaque journée donne une archive `depot-python-jNN.zip` qui contient l'énoncé, le squelette à
compléter, les tests livrés, le corrigé de la veille et un fichier de prise en main. Les archives
sont déterministes : horodatage figé et entrées triées, pour qu'une reconstruction sans changement
ne produise aucun écart dans le dépôt.

`--eprouver` est la garantie qui compte pour l'apprenant : les tests d'une journée doivent échouer
sur le squelette livré et passer sur la solution de référence. Il exige pytest, qui n'est pas
installé dans l'image de l'application ; il se lance donc à la main ou dans un environnement
d'intégration qui en dispose.
"""
import argparse
import hashlib
import io
import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
import zipfile

ICI = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(ICI))  # `python -I` ne met pas le dossier du script sur le chemin

import arbre  # noqa: E402  (l'import suit l'ajout du dossier au chemin)

SOURCE = ICI / "openlab-academy-python-rh"
DESTINATION = (ICI.parents[1] / "apps" / "openlab_academy" / "openlab_academy" / "data" / "ressources")
EMPREINTES = DESTINATION.parent / "depots-python.json"  # livré avec l'application : le test y lit
HORODATAGE = (1980, 1, 1, 0, 0, 0)  # figé : une archive ne change que si son contenu change
# le carnet d'une semaine est joint au dépôt de son premier jour : l'apprenant l'a dès le lundi
SEMAINES = {1: 1, 6: 2, 11: 3, 16: 4, 21: 5, 26: 6, 31: 7}

LISEZ_MOI = """# Dépôt de la journée {numero}

Trois commandes, dans ce dossier.

1. Installer l'outil de test, une seule fois :
   - Windows : `py -m pip install pytest`
   - macOS et Linux : `python3 -m pip install pytest`
2. Lancer les tests : `python -m pytest`
3. Lancer votre programme : `python {programme}`

Les tests échouent au départ : c'est voulu. Votre challenge consiste à les faire passer.

Le dossier `corrige/` contient la solution de la journée précédente. Comparez-la à la vôtre
seulement après avoir rendu votre propre version.

Données entièrement fictives : aucun fichier de paie réel ne doit entrer dans ce dossier.
"""


def octets(fichier: pathlib.Path) -> bytes:
    """Contenu d'un fichier du dépôt source, fins de ligne normalisées.

    Git peut rendre le dépôt source en CRLF sous Windows et en LF ailleurs ; sans cette
    normalisation, la même source produirait deux archives différentes selon la machine.
    """
    return fichier.read_bytes().replace(b"\r\n", b"\n")


def journees() -> list[pathlib.Path]:
    return sorted(dossier for dossier in SOURCE.glob("j[0-9][0-9]") if dossier.is_dir())


def _programme(journee: pathlib.Path) -> str:
    """Nom du fichier que l'apprenant exécute, pour le fichier de prise en main."""
    fichiers = sorted(p.relative_to(journee / "depart").as_posix()
                      for p in (journee / "depart").rglob("*.py") if p.name != "__init__.py")
    return fichiers[0] if fichiers else "main.py"


def contenu(journee: pathlib.Path) -> dict[str, bytes]:
    """{chemin dans l'archive: octets} d'une journée, corrigé de la veille compris."""
    numero = journee.name[1:]
    entrees: dict[str, bytes] = {
        "enonce.md": octets(journee / "enonce.md"),
        "LISEZ-MOI.md": LISEZ_MOI.format(numero=numero, programme=_programme(journee)).encode("utf-8"),
    }
    for racine, prefixe in ((journee / "depart", ""), (journee / "tests", "tests/")):
        for fichier in sorted(racine.rglob("*")):
            # un pytest lancé dans l'arbre source y laisse des dossiers de travail : ils ne sont pas
            # suivis par git, et partiraient dans l'archive construite en local, pas dans celle du serveur
            if fichier.is_file() and arbre.retenu(fichier, racine):
                entrees[prefixe + fichier.relative_to(racine).as_posix()] = octets(fichier)
    carnet = SOURCE / "carnets" / f"semaine-{SEMAINES.get(int(numero), 0)}.md"
    if carnet.is_file():
        # le carnet d'entraînement arrive le premier jour de sa semaine, pour servir toute la semaine
        entrees[carnet.name] = octets(carnet)
    veille = SOURCE / f"j{int(numero) - 1:02d}" / "solution"
    if veille.is_dir():
        for fichier in sorted(veille.rglob("*")):
            if fichier.is_file() and arbre.retenu(fichier, veille):
                entrees["corrige/" + fichier.relative_to(veille).as_posix()] = octets(fichier)
    return entrees


def archive(entrees: dict[str, bytes]) -> bytes:
    """Zip déterministe : entrées triées, horodatage figé, aucune métadonnée de système."""
    tampon = io.BytesIO()
    with zipfile.ZipFile(tampon, "w", zipfile.ZIP_DEFLATED) as zip_:
        for nom in sorted(entrees):
            info = zipfile.ZipInfo(nom, date_time=HORODATAGE)
            info.external_attr = 0o644 << 16
            info.create_system = arbre.SYSTEME
            zip_.writestr(info, entrees[nom])
    return tampon.getvalue()


def construire() -> dict[str, bytes]:
    return {f"depot-python-{journee.name}.zip": archive(contenu(journee)) for journee in journees()}


def eprouver(interpreteur: str = sys.executable, retenues: list[str] | None = None) -> list[str]:
    """Lance les tests d'une journée sur le squelette puis sur la solution.

    Rend la liste des journées fautives : celles dont le squelette passe (le challenge ne
    prouverait rien) ou dont la solution de référence échoue (le corrigé serait faux).
    """
    fautives = []
    for journee in journees():
        if retenues and journee.name not in retenues:
            continue
        for source, attendu_vert in ((journee / "depart", False), (journee / "solution", True)):
            with tempfile.TemporaryDirectory() as temporaire:
                travail = pathlib.Path(temporaire)
                shutil.copytree(source, travail, dirs_exist_ok=True)
                shutil.copytree(journee / "tests", travail / "tests", dirs_exist_ok=True)
                environnement = dict(os.environ, PYTHONPATH=str(travail), PYTHONDONTWRITEBYTECODE="1")
                execution = subprocess.run(
                    [interpreteur, "-m", "pytest", "-q", "--no-header", "-p", "no:cacheprovider"],
                    cwd=travail, capture_output=True, text=True, env=environnement)
                if (execution.returncode == 0) != attendu_vert:
                    fautives.append(f"{journee.name} / {source.name} : "
                                    f"code {execution.returncode}, attendu "
                                    f"{'vert' if attendu_vert else 'rouge'}")
    return fautives


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verifier", action="store_true",
                        help="ne rien écrire ; échouer si une archive livrée diffère du rendu")
    parser.add_argument("--eprouver", action="store_true",
                        help="lancer les tests de chaque journée sur le squelette puis la solution")
    parser.add_argument("--python", default=sys.executable, metavar="CHEMIN",
                        help="interpréteur qui exécute les tests ; utile pour les journées Django, "
                             "qui demandent un environnement où Django est installé")
    parser.add_argument("--journees", default="", metavar="j26,j27",
                        help="n'éprouver que ces journées, séparées par des virgules")
    arguments = parser.parse_args()

    if arguments.eprouver:
        retenues = [nom.strip() for nom in arguments.journees.split(",") if nom.strip()]
        fautives = eprouver(arguments.python, retenues)
        for ligne in fautives:
            print(f"  FAUTIF    {ligne}")
        nombre = len(retenues) if retenues else len(journees())
        print(f"{nombre} journées éprouvées, {len(fautives)} fautives.")
        return 1 if fautives else 0

    DESTINATION.mkdir(parents=True, exist_ok=True)
    empreintes, ecarts = {}, []
    for nom, octets in construire().items():
        fichier = DESTINATION / nom
        empreintes[nom] = hashlib.sha256(octets).hexdigest()
        if arguments.verifier:
            livree = fichier.read_bytes() if fichier.is_file() else b""
            if arbre.servi(livree) != arbre.servi(octets):
                ecarts.append(nom)
            continue
        fichier.write_bytes(octets)
        print(f"  écrit     {nom}    {len(octets)} octets  {empreintes[nom][:12]}")

    if arguments.verifier:
        attendues = json.loads(EMPREINTES.read_text(encoding="utf-8")) if EMPREINTES.is_file() else {}
        # l'empreinte porte sur le fichier livré : c'est lui que l'application sert et que le test relit
        ecarts += [f"{nom} (empreinte)" for nom in empreintes
                   if not (DESTINATION / nom).is_file()
                   or attendues.get(nom) != hashlib.sha256((DESTINATION / nom).read_bytes()).hexdigest()]
        for nom in sorted(set(ecarts)):
            print(f"  ECART     {nom}")
        print(f"{len(empreintes)} archives vérifiées, {len(set(ecarts))} écarts.")
        return 1 if ecarts else 0

    EMPREINTES.write_text(json.dumps(empreintes, indent=2, sort_keys=True) + "\n", encoding="utf-8",
                          newline="\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
