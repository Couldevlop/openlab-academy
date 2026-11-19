"""Construit l'archive du socle distribuée aux apprenants, depuis le dépôt de départ du formateur.

Usage, depuis la racine du projet :

    python docs/Ressources/construire_archive_socle.py

Les supports de séance du formateur, l'environnement virtuel et les états locaux sont exclus. L'archive est écrite
dans les ressources de l'application, d'où la publication la joint à la leçon en fichier privé.
"""
import hashlib
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


def construire() -> pathlib.Path:
    if not SOURCE.is_dir():
        raise SystemExit(f"dépôt de départ introuvable : {SOURCE}")
    CIBLE.mkdir(parents=True, exist_ok=True)
    archive = CIBLE / NOM
    fichiers = sorted(c for c in SOURCE.rglob("*") if c.is_file() and retenu(c))
    # date fixe et compression stable : la même source produit la même archive, donc la même empreinte
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as zip_:
        for fichier in fichiers:
            info = zipfile.ZipInfo(f"{PREFIXE}/{fichier.relative_to(SOURCE).as_posix()}", (2026, 11, 12, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            zip_.writestr(info, fichier.read_bytes())
    return archive


if __name__ == "__main__":
    chemin = construire()
    empreinte = hashlib.sha256(chemin.read_bytes()).hexdigest()
    with zipfile.ZipFile(chemin) as zip_:
        nombre = len(zip_.namelist())
    print(f"{chemin.relative_to(RACINE)} : {nombre} fichiers, {chemin.stat().st_size} octets")
    print(f"sha256 : {empreinte}")
