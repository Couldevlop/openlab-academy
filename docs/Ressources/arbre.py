"""Ce qu'un dossier source met dans une archive, et ce qu'il n'y met jamais.

Les constructeurs d'archives empaquettent un arbre de fichiers du dépôt. Deux pièges s'y cachent, et
tous deux se voient seulement dans la chaîne d'intégration, là où ils coûtent le plus cher :

  - **les dossiers de travail des outils** (`__pycache__`, `.pytest_cache`, `.venv`…). Ils
    apparaissent dès qu'on lance les tests dans l'arbre source, ils ne sont pas suivis par git, et
    ils partent dans l'archive construite en local sans exister sur le serveur. L'archive livrée ne
    correspond alors plus à la source, et la vérification échoue — en plus de livrer à l'apprenant
    le `lastfailed` de pytest, qui lui dit quels tests ratent avant même qu'il ait commencé ;
  - **les fins de ligne**. Git peut rendre le même fichier en CRLF sous Windows et en LF ailleurs ;
    sans normalisation, la même source produit deux archives différentes selon la machine.

Ce module tient la réponse aux deux, en un seul endroit, pour que le prochain constructeur d'archive
n'ait pas à la redécouvrir.
"""
import io
import pathlib
import zipfile

# dossiers de travail : jamais dans une archive, et jamais comparés
DOSSIERS_EXCLUS = {".venv", ".local", "__pycache__", ".pytest_cache", ".ruff_cache", ".mypy_cache",
                   ".git", "dist", "build", "node_modules"}
# fins de ligne laissées telles quelles : les normaliser corromprait le fichier
BINAIRES = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".ico", ".pdf", ".zip", ".woff", ".woff2"}


def retenu(chemin: pathlib.Path, racine: pathlib.Path) -> bool:
    """Vrai si le fichier a sa place dans une archive livrée."""
    relatif = chemin.relative_to(racine)
    return not (set(relatif.parts) & DOSSIERS_EXCLUS) and chemin.suffix != ".pyc"


def fichiers(racine: pathlib.Path) -> dict[str, bytes]:
    """Le contenu de l'arbre, chemin relatif par chemin relatif, fins de ligne normalisées."""
    contenu = {}
    for chemin in sorted(p for p in racine.rglob("*") if p.is_file()):
        if not retenu(chemin, racine):
            continue
        octets = chemin.read_bytes()
        if chemin.suffix.lower() not in BINAIRES:
            octets = octets.replace(b"\r\n", b"\n")
        contenu[chemin.relative_to(racine).as_posix()] = octets
    return contenu


SYSTEME = 0  # figé : zipfile écrirait 0 sous Windows et 3 ailleurs, et l'archive dépendrait du poste


def servi(octets: bytes) -> list[tuple]:
    """Ce qu'une archive sert, sa structure comprise, mais jamais ses octets compressés.

    Le compresseur ne rend pas les mêmes octets d'une version de zlib à l'autre : comparer les
    archives octet par octet ferait échouer la chaîne d'intégration sans que rien ait bougé. Tout
    le reste entre dans la comparaison, parce qu'une archive livrée se retouche sans que ses
    entrées changent de nom :

      - **une liste, jamais un dictionnaire.** Deux entrées de même nom s'y effacent l'une
        l'autre : une archive où `fiche.py` est écrit deux fois paraît alors identique à celle
        qui ne le porte qu'une fois, et les outils de décompression ne servent pas tous la même
        des deux ;
      - **les métadonnées.** Horodatage, droits et système d'origine sont figés par les
        constructeurs : tout écart signale une archive retouchée à la main, pas une
        reconstruction ;
      - **le décalage de la première entrée.** Des octets glissés devant une archive n'en
        changent aucune entrée, et la font pourtant lire autrement selon l'outil.

    Les entrées sont rendues dans l'ordre de l'archive, que les constructeurs trient déjà.
    """
    if not octets:
        return []
    try:
        with zipfile.ZipFile(io.BytesIO(octets)) as zip_:
            entrees = zip_.infolist()
            devant = entrees[0].header_offset if entrees else 0
            return [("octets devant l'archive", devant)] + [
                (info.filename, info.date_time, info.external_attr, info.create_system, zip_.read(info))
                for info in entrees]
    except (zipfile.BadZipFile, OSError) as souci:
        # une archive livrée illisible se signale comme un écart, elle ne fait pas tomber le script :
        # le constructeur doit pouvoir dire « à reconstruire » plutôt que s'arrêter sur une trace
        return [("archive illisible", str(souci))]
