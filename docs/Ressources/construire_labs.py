"""Construit les labs de cybersécurité livrés avec les séances.

    python docs/Ressources/construire_labs.py             # écrit les archives
    python docs/Ressources/construire_labs.py --verifier  # échoue si une archive a bougé
    python docs/Ressources/construire_labs.py --eprouver  # rouge sur le squelette, vert sur le corrigé

Chaque lab vit sous `labs/<nom>/` et part en `lab-<nom>.zip`. L'archive est déterministe : horodatage
figé, entrées triées, fins de ligne normalisées, pour qu'une reconstruction sans changement ne
produise aucun écart dans le dépôt.

`--eprouver` est la garantie qui compte pour l'apprenant, et elle vaut mieux qu'une relecture : les
tests livrés doivent échouer sur le squelette et passer sur le corrigé. Sans elle, un lab peut très
bien partir avec des tests déjà verts — un exercice qui ne demande rien — ou impossibles à rendre
verts. Le corrigé est éprouvé dans un dossier temporaire, jamais dans le dépôt.

Le dossier `corrige/` part dans l'archive : l'atelier du navigateur l'écarte de lui-même (voir
`atelier_api.IGNORES`), et l'apprenant qui travaille en local l'a sous la main pour comparer après
avoir rendu. Les fabricants de corpus (`fabriquer_journaux_*.py`) restent en dehors : ils posent
l'incident, les lire donnerait la réponse.
"""
import argparse
import io
import pathlib
import shutil
import subprocess
import sys
import tempfile
import zipfile

ICI = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(ICI))  # `python -I` ne met pas le dossier du script sur le chemin

import arbre  # noqa: E402  (l'import suit l'ajout du dossier au chemin)

LABS = ICI / "labs"
DESTINATION = ICI.parents[1] / "apps" / "openlab_academy" / "openlab_academy" / "data" / "ressources"
HORODATAGE = (1980, 1, 1, 0, 0, 0)  # figé : une archive ne change que si son contenu change


def fichiers(lab: pathlib.Path) -> dict[str, bytes]:
    """Le contenu du lab, prêt à empaqueter : voir `arbre` pour ce qui en est exclu, et pourquoi."""
    return arbre.fichiers(lab)


def archiver(contenu: dict[str, bytes]) -> bytes:
    tampon = io.BytesIO()
    with zipfile.ZipFile(tampon, "w", zipfile.ZIP_DEFLATED) as zip_:
        for chemin in sorted(contenu):
            info = zipfile.ZipInfo(chemin, HORODATAGE)
            info.external_attr = 0o644 << 16
            info.compress_type = zipfile.ZIP_DEFLATED
            zip_.writestr(info, contenu[chemin])
    return tampon.getvalue()


def entrees(octets: bytes) -> dict[str, bytes]:
    """Ce que l'archive sert, jamais ses octets compressés : le compresseur varie d'une version de
    Python à l'autre, et la chaîne d'intégration ne doit pas échouer pour cette raison."""
    if not octets:
        return {}
    with zipfile.ZipFile(io.BytesIO(octets)) as zip_:
        return {info.filename: zip_.read(info) for info in zip_.infolist()}


def eprouver(lab: pathlib.Path) -> list[str]:
    """Lance les tests du lab sur le squelette livré, puis sur le corrigé. Rend les écarts."""
    soucis = []
    with tempfile.TemporaryDirectory() as temporaire:
        banc = pathlib.Path(temporaire) / lab.name
        shutil.copytree(lab, banc)
        squelette = subprocess.run([sys.executable, "-m", "pytest", "-q"], cwd=banc,
                                   capture_output=True, text=True)
        if squelette.returncode == 0:
            soucis.append(f"{lab.name} : les tests passent sur le squelette (l'exercice ne demande rien)")

        for solution in sorted((banc / "corrige").glob("*.py")):
            shutil.copy(solution, banc / solution.name)
        corrige = subprocess.run([sys.executable, "-m", "pytest", "-q"], cwd=banc,
                                 capture_output=True, text=True)
        if corrige.returncode != 0:
            soucis.append(f"{lab.name} : les tests échouent sur le corrigé\n"
                          f"{corrige.stdout[-1500:]}")
    return soucis


def main() -> int:
    arguments = argparse.ArgumentParser(description=__doc__)
    arguments.add_argument("--verifier", action="store_true", help="échoue si une archive a bougé")
    arguments.add_argument("--eprouver", action="store_true", help="rouge au départ, vert sur le corrigé")
    options = arguments.parse_args()

    labs = sorted(d for d in LABS.iterdir() if d.is_dir()) if LABS.is_dir() else []
    if not labs:
        print(f"aucun lab sous {LABS}")
        return 1

    ecarts, soucis = [], []
    for lab in labs:
        archive = DESTINATION / f"lab-{lab.name}.zip"
        construite = archiver(fichiers(lab))
        if options.eprouver:
            soucis += eprouver(lab)
        if options.verifier:
            if entrees(archive.read_bytes() if archive.exists() else b"") != entrees(construite):
                ecarts.append(archive.name)
            continue
        archive.parent.mkdir(parents=True, exist_ok=True)
        archive.write_bytes(construite)
        print(f"{archive.relative_to(ICI.parents[1])} : {len(fichiers(lab))} fichiers, "
              f"{len(construite) // 1024} Ko")

    for souci in soucis:
        print(souci)
    if ecarts:
        print("archives à reconstruire : " + ", ".join(ecarts))
    if options.verifier and not ecarts:
        print(f"{len(labs)} lab(s) : archives identiques")
    return 1 if ecarts or soucis else 0


if __name__ == "__main__":
    raise SystemExit(main())
