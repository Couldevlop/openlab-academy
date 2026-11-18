"""Construit les schémas SVG du parcours et les dépose dans les ressources de l'application.

    python docs/Ressources/construire_schemas.py          # écrit les fichiers
    python docs/Ressources/construire_schemas.py --verifier  # échoue si un fichier livré diffère

Le second mode est celui de l'intégration continue : il prouve que les SVG versionnés sont bien ceux que le
code produit, donc qu'une figure corrigée dans le script ne peut pas rester absente du dépôt.
"""
import argparse
import hashlib
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent / "schemas"))

from figures import FIGURES  # noqa: E402  (le chemin doit être posé avant l'import)
from figures_python import FIGURES_PYTHON  # noqa: E402

DESTINATION = (pathlib.Path(__file__).resolve().parents[2]
               / "apps" / "openlab_academy" / "openlab_academy" / "data" / "ressources")


def construire() -> dict[str, str]:
    return {nom: fabrique().rendre() for nom, fabrique in sorted({**FIGURES, **FIGURES_PYTHON}.items())}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verifier", action="store_true",
                        help="ne rien écrire ; échouer si un fichier livré diffère du rendu")
    arguments = parser.parse_args()

    DESTINATION.mkdir(parents=True, exist_ok=True)
    ecarts = []
    for nom, contenu in construire().items():
        octets = contenu.encode("utf-8")
        fichier = DESTINATION / nom
        empreinte = hashlib.sha256(octets).hexdigest()[:12]
        if arguments.verifier:
            if not fichier.is_file() or fichier.read_bytes() != octets:
                ecarts.append(nom)
            else:
                print(f"  identique  {nom}  {empreinte}")
        else:
            fichier.write_bytes(octets)
            print(f"  écrit      {nom}  {len(octets):>6} octets  {empreinte}")

    if ecarts:
        print("\nFigures absentes ou différentes du rendu : " + ", ".join(ecarts), file=sys.stderr)
        print("Relancez le script sans --verifier, puis versionnez les fichiers.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
