"""Construit l'archive du socle distribuée aux apprenants, depuis le dépôt de départ du formateur.

Usage, depuis la racine du projet :

    python docs/Ressources/construire_archive_socle.py             # écrit l'archive
    python docs/Ressources/construire_archive_socle.py --verifier  # échoue si elle a dérivé

Les supports de séance du formateur, l'environnement virtuel et les états locaux sont exclus. L'archive est écrite
dans les ressources de l'application, d'où la publication la joint à la leçon en fichier privé.

`--verifier` est la seule chose qui empêche l'archive de mentir. Sans elle, une évolution du socle source
reste invisible : l'archive déjà livrée continue d'être servie, et l'apprenant travaille sur une version
que plus personne ne lit. La comparaison porte sur les entrées servies, jamais sur les octets compressés,
qui varient d'une version de Python à l'autre.
"""
import argparse
import hashlib
import io
import pathlib
import sys
import zipfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))  # `python -I` : chemin du script

import arbre  # noqa: E402  (l'import suit l'ajout du dossier au chemin)

RACINE = pathlib.Path(__file__).resolve().parents[2]
SOURCE = RACINE / "docs" / "Ressources" / "openlab-academy-agentic-starter"
CIBLE = RACINE / "apps" / "openlab_academy" / "openlab_academy" / "data" / "ressources"
NOM = "socle-ia-agentique-v0.3.0.zip"
PREFIXE = "openlab-academy-agentic-starter"
CRLF, LF = b"\r\n", b"\n"

DOSSIERS_EXCLUS = arbre.DOSSIERS_EXCLUS  # une seule liste pour toutes les archives du dépôt
# supports du formateur : déroulés minutés et indices graduels, qui ne sont pas distribués aux apprenants
FICHIERS_EXCLUS = {"docs/SUPPORTS.md"}


def retenu(chemin: pathlib.Path) -> bool:
    relatif = chemin.relative_to(SOURCE).as_posix()
    parties = chemin.relative_to(SOURCE).parts
    if any(p in DOSSIERS_EXCLUS or p.endswith(".egg-info") for p in parties):
        return False
    if chemin.suffix in {".pyc", ".pyo"}:
        return False
    if relatif in FICHIERS_EXCLUS or relatif.startswith("docs/TP_SEANCE_"):
        return False
    return True


def assembler() -> bytes:
    """Les octets de l'archive, sans rien écrire."""
    if not SOURCE.is_dir():
        raise SystemExit(f"dépôt de départ introuvable : {SOURCE}")
    tampon = io.BytesIO()
    # date fixe, entrées triées, fins de ligne normalisées : la même source rend la même archive sur
    # toute machine. Sans la normalisation, l'archive construite sous Windows diffère de celle du
    # serveur sur chaque fichier texte, et sa vérification n'a plus aucun sens.
    with zipfile.ZipFile(tampon, "w", zipfile.ZIP_DEFLATED) as zip_:
        for fichier in sorted(c for c in SOURCE.rglob("*") if c.is_file() and retenu(c)):
            info = zipfile.ZipInfo(f"{PREFIXE}/{fichier.relative_to(SOURCE).as_posix()}", (2026, 11, 12, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            info.create_system = arbre.SYSTEME
            octets = fichier.read_bytes()
            if fichier.suffix.lower() not in arbre.BINAIRES:
                octets = octets.replace(CRLF, LF)
            zip_.writestr(info, octets)
    return tampon.getvalue()


def construire() -> pathlib.Path:
    CIBLE.mkdir(parents=True, exist_ok=True)
    archive = CIBLE / NOM
    archive.write_bytes(assembler())
    return archive


def main() -> int:
    arguments = argparse.ArgumentParser(description=__doc__)
    arguments.add_argument("--verifier", action="store_true", help="échoue si l'archive a dérivé")
    options = arguments.parse_args()

    construite = assembler()
    if options.verifier:
        livree = CIBLE / NOM
        if arbre.servi(livree.read_bytes() if livree.is_file() else b"") != arbre.servi(construite):
            print(f"archive à reconstruire : {NOM}")
            return 1
        print(f"{NOM} : identique à la source")
        return 0

    chemin = construire()
    print(f"{chemin.relative_to(RACINE)} : {len(arbre.servi(construite)) - 1} fichiers, "
          f"{chemin.stat().st_size} octets")
    print(f"sha256 : {hashlib.sha256(construite).hexdigest()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
