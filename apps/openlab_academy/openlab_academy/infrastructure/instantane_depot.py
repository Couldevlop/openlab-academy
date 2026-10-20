"""Adaptateur : instantané d'un dépôt public (GitHub, GitLab) lu par leurs API officielles, sans exécuter de code.

Défense SSRF (OWASP A10) : seul un lien https vers un hôte autorisé, sans adresse IP, identifiants ni port non
standard, est accepté. Les requêtes ne partent que vers l'API officielle de l'hébergeur, construite à partir du
chemin validé (jamais vers le lien fourni), sans suivre de redirection et toujours avec un délai. Les lectures
sont bornées : nombre de fichiers, taille lue, durée totale et plafond de caractères.
"""
import ipaddress
import json
import re
import time
from collections.abc import Callable
from dataclasses import dataclass
from urllib.parse import quote, urlsplit

import requests

from openlab_academy.application.controler import EtapeIndisponible

DELAI_S = 10
BUDGET_S = 20  # durée totale d'un instantané pris pendant le rendu de l'apprenant
BUDGET_TACHE_S = 60  # durée totale d'un instantané repris en tâche de fond
JSON_MAX = 8 * 1024 * 1024
FICHIERS_MAX = 12
PAGES_MAX = 10
PAR_PAGE = 100
MORCEAU = 64 * 1024
API = {"github.com": "https://api.github.com/repos", "gitlab.com": "https://gitlab.com/api/v4/projects"}
_SEGMENT = re.compile(r"^[A-Za-z0-9_.-]{1,100}$")
_EMPREINTE = re.compile(r"^[0-9a-f]{40,64}$")
_REDIRECTIONS = {301, 302, 303, 307, 308}
EXCLUS = {"node_modules", "vendor", "dist", "build", ".git", ".venv", "venv", "__pycache__", "target", ".idea"}
MANIFESTES = {"package.json", "pyproject.toml", "requirements.txt", "setup.py", "pom.xml", "build.gradle",
              "build.gradle.kts", "go.mod", "cargo.toml", "composer.json", "gemfile", "makefile"}
SOURCES = {".py", ".js", ".ts", ".tsx", ".jsx", ".java", ".kt", ".go", ".rs", ".php", ".rb", ".cs", ".dart",
           ".sql", ".html", ".css", ".scss", ".vue", ".ipynb", ".r", ".md", ".yml", ".yaml", ".toml"}


class LienRefuse(ValueError):
    """Le lien rendu ne désigne pas un dépôt autorisé : aucune requête n'est faite."""


class DepotIntrouvable(Exception):
    """Le dépôt n'est pas lisible publiquement (inexistant, privé, déplacé ou vide) : la copie est à reprendre."""


class DepotIndisponible(EtapeIndisponible):
    """Réseau, délai ou API de l'hébergeur en échec : rien n'est reproché à l'apprenant."""


@dataclass(frozen=True)
class Lien:
    hote: str
    chemin: tuple[str, ...]


def _refuser(motif: str):
    raise LienRefuse(f"lien de dépôt refusé : {motif}")


def _segments(hote: str, chemin: str) -> tuple[str, ...]:
    segments = [s for s in chemin.split("/") if s]
    if hote == "gitlab.com" and "-" in segments:  # https://gitlab.com/groupe/projet/-/tree/main
        segments = segments[:segments.index("-")]
    elif hote == "github.com":
        segments = segments[:2]
    if segments and segments[-1].endswith(".git"):
        segments[-1] = segments[-1][:-4]
    if len(segments) < 2 or any(not _SEGMENT.match(s) or not s.strip(".") for s in segments):
        _refuser("chemin de dépôt invalide (propriétaire/nom attendus)")
    return tuple(segments)


def valider_lien(url, hotes: tuple[str, ...]) -> Lien:
    """Lien https vers un hôte autorisé et pris en charge ; tout le reste est refusé sans requête."""
    url = url if isinstance(url, str) else ""
    if any(c.isspace() or ord(c) < 32 or c == "\\" for c in url):
        _refuser("lien mal formé")
    parties = urlsplit(url)
    if parties.scheme != "https":
        _refuser("HTTPS obligatoire")
    if "@" in parties.netloc:
        _refuser("identifiants interdits dans le lien")
    try:
        port = parties.port
    except ValueError:
        _refuser("port invalide")
    if port not in (None, 443):
        _refuser("port non standard interdit")
    hote = parties.hostname or ""
    try:
        ipaddress.ip_address(hote)
    except ValueError:
        pass
    else:
        _refuser("adresse IP interdite")
    if hote not in {h.strip().lower() for h in hotes}:
        _refuser(f"hôte « {hote} » non autorisé (autorisés : {', '.join(hotes)})")
    if hote not in API:
        _refuser(f"hébergeur « {hote} » non pris en charge")
    return Lien(hote, _segments(hote, parties.path))


class _Client:
    """Appels bornés à l'API officielle d'un hébergeur, pour un dépôt validé."""

    ENTETES: dict[str, str] = {}

    def __init__(self, lien: Lien, delai_s: float, jeton: str = "", limite: float | None = None,
                 horloge: Callable[[], float] = time.monotonic):
        self._lien = lien
        self._delai = delai_s
        self._jeton = jeton
        self._limite = limite  # échéance totale (horloge monotone) de tous les appels ; None = délai par appel seul
        self._horloge = horloge

    def _autorisation(self) -> dict:
        return {}

    def _delai_appel(self) -> float:
        if self._limite is None:
            return self._delai
        reste = self._limite - self._horloge()
        if reste <= 0:
            raise DepotIndisponible("hébergeur : délai total dépassé")
        return min(self._delai, reste)

    def _get(self, url: str, params: dict | None = None, entetes: dict | None = None):
        delai = self._delai_appel()
        try:
            reponse = requests.get(url, params=params, timeout=delai, allow_redirects=False, stream=True,
                                   headers={**self.ENTETES, **self._autorisation(), **(entetes or {})})
        except requests.RequestException as erreur:
            raise DepotIndisponible(f"hébergeur injoignable ({type(erreur).__name__})") from None
        statut = reponse.status_code
        if statut != 200:
            reponse.close()
            if statut in _REDIRECTIONS:
                raise DepotIntrouvable("dépôt déplacé : rendez son adresse actuelle")
            if statut == 409:
                raise DepotIntrouvable("dépôt vide")
            if statut in (401, 404):
                raise DepotIntrouvable("dépôt introuvable ou privé")
            raise DepotIndisponible(f"hébergeur : réponse HTTP {statut}")
        return reponse

    @staticmethod
    def _lire(reponse, plafond: int) -> tuple[bytes, bool]:
        """Au plus `plafond` octets, puis la connexion est fermée ; le booléen dit si la réponse dépassait."""
        morceaux, total = [], 0
        try:
            for morceau in reponse.iter_content(MORCEAU):
                morceaux.append(morceau)
                total += len(morceau)
                if total > plafond:
                    break
        finally:
            reponse.close()
        return b"".join(morceaux)[:plafond], total > plafond

    def _json(self, url: str, params: dict | None = None, type_=dict):
        """Métadonnées bornées à JSON_MAX octets : au-delà, le dépôt est trop volumineux pour être évalué (motif)."""
        brut, deborde = self._lire(self._get(url, params), JSON_MAX)
        if deborde:
            raise DepotIntrouvable("dépôt trop volumineux pour être évalué")
        try:
            donnees = json.loads(brut.decode("utf-8"))
        except ValueError:
            raise DepotIndisponible("hébergeur : réponse illisible") from None
        if not isinstance(donnees, type_):
            raise DepotIndisponible("hébergeur : réponse inattendue")
        return donnees

    @staticmethod
    def _empreinte(valeur) -> str:
        if not isinstance(valeur, str) or not _EMPREINTE.match(valeur):
            raise DepotIndisponible("hébergeur : réponse inattendue")
        return valeur

    def lire(self, chemin: str, ref: str, plafond: int) -> str | None:
        """Texte d'un fichier lu au plus jusqu'au plafond ; None si binaire."""
        brut, _ = self._lire(self._fichier(chemin, ref), plafond)
        return None if b"\x00" in brut else brut.decode("utf-8", errors="replace")


class ClientGitHub(_Client):
    ENTETES = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}

    def _autorisation(self) -> dict:
        """Jeton facultatif de la console (quota de l'API relevé) ; il ne part que vers api.github.com."""
        return {"Authorization": f"Bearer {self._jeton}"} if self._jeton else {}

    @property
    def _base(self) -> str:
        return f"{API['github.com']}/{self._lien.chemin[0]}/{self._lien.chemin[1]}"

    def infos(self) -> str:
        """Branche par défaut d'un dépôt public."""
        donnees = self._json(self._base)
        if donnees.get("private") is not False:
            raise DepotIntrouvable("dépôt introuvable ou privé")
        return str(donnees.get("default_branch") or "main")

    def commit(self, branche: str) -> str:
        return self._empreinte(self._json(f"{self._base}/commits/{quote(branche, safe='')}").get("sha"))

    def arborescence(self, ref: str) -> list[tuple[str, int | None]]:
        arbre = self._json(f"{self._base}/git/trees/{self._empreinte(ref)}", {"recursive": "1"}).get("tree") or []
        return [(e["path"], e.get("size")) for e in arbre if e.get("type") == "blob"]

    def _fichier(self, chemin: str, ref: str):
        return self._get(f"{self._base}/contents/{quote(chemin)}", {"ref": ref},
                         {"Accept": "application/vnd.github.raw+json"})


class ClientGitLab(_Client):
    @property
    def _base(self) -> str:
        return f"{API['gitlab.com']}/{quote('/'.join(self._lien.chemin), safe='')}"

    def infos(self) -> str:
        donnees = self._json(self._base)
        if donnees.get("visibility", "public") != "public":
            raise DepotIntrouvable("dépôt introuvable ou privé")
        return str(donnees.get("default_branch") or "main")

    def commit(self, branche: str) -> str:
        return self._empreinte(self._json(f"{self._base}/repository/commits/{quote(branche, safe='')}").get("id"))

    def arborescence(self, ref: str) -> list[tuple[str, int | None]]:
        chemins: list[tuple[str, int | None]] = []
        for page in range(1, PAGES_MAX + 1):
            lot = self._json(f"{self._base}/repository/tree",
                             {"recursive": "true", "ref": self._empreinte(ref), "per_page": str(PAR_PAGE),
                              "page": str(page)}, list)
            chemins += [(e["path"], None) for e in lot if isinstance(e, dict) and e.get("type") == "blob"]
            if len(lot) < PAR_PAGE:
                break
        return chemins

    def _fichier(self, chemin: str, ref: str):
        return self._get(f"{self._base}/repository/files/{quote(chemin, safe='')}/raw", {"ref": ref})


def client_pour(lien: Lien, delai_s: float, jeton: str = "", limite: float | None = None,
                horloge: Callable[[], float] = time.monotonic) -> _Client:
    return {"github.com": ClientGitHub, "gitlab.com": ClientGitLab}[lien.hote](lien, delai_s, jeton, limite, horloge)


def _exclu(chemin: str) -> bool:
    return any(partie in EXCLUS for partie in chemin.split("/")[:-1])


def _rang(chemin: str) -> tuple:
    """Ordre de lecture : README, manifestes, tests, CI, .env.example, conteneur, puis sources (les plus courtes)."""
    nom = chemin.rsplit("/", 1)[-1].lower()
    racine = "/" not in chemin
    extension = "." + nom.rsplit(".", 1)[-1] if "." in nom else ""
    if racine and nom.startswith("readme"):
        rang = 0
    elif racine and nom in MANIFESTES:
        rang = 1
    elif re.search(r"(^|/)(tests?|spec|__tests__)/|(^|/)test_|[._-](test|spec)\.", chemin.lower()):
        rang = 2
    elif chemin.startswith(".github/workflows/") or nom == ".gitlab-ci.yml":
        rang = 3
    elif nom == ".env.example":
        rang = 4
    elif nom == "dockerfile" or re.match(r"^(docker-)?compose\.ya?ml$", nom):
        rang = 5
    elif extension in SOURCES:
        rang = 6
    else:
        return (9,)
    return (rang, chemin.count("/"), len(chemin), chemin)


class InstantaneDepot:
    """Port Instantane : (texte de l'instantané, commit figé) d'un dépôt public. Tous les appels tiennent dans
    `budget_s` : au-delà, l'instantané est abandonné (DepotIndisponible) et sera repris en tâche de fond."""

    def __init__(self, hotes: tuple[str, ...], plafond: int, delai_s: float = DELAI_S,
                 fichiers_max: int = FICHIERS_MAX, horloge: Callable[[], float] = time.monotonic, jeton: str = "",
                 budget_s: float = BUDGET_S):
        self._hotes = hotes
        self._plafond = plafond
        self._delai = delai_s
        self._fichiers_max = fichiers_max
        self._horloge = horloge
        self._jeton = jeton
        self._budget = budget_s

    def prendre(self, url: str) -> tuple[str, str]:
        lien = valider_lien(url, self._hotes)
        client = client_pour(lien, self._delai, self._jeton, self._horloge() + self._budget, self._horloge)
        commit = client.commit(client.infos())
        fichiers = sorted((c, t) for c, t in client.arborescence(commit) if not _exclu(c))
        arborescence = "\n".join(c for c, _ in fichiers)[:self._plafond // 4]
        texte = f"Dépôt : {url}\nCommit : {commit}\n\nArborescence :\n{arborescence}"
        cles = sorted(((c, t) for c, t in fichiers if _rang(c)[0] < 9), key=lambda f: _rang(f[0]))
        lus = 0
        for chemin, taille in cles:
            reste = self._plafond - len(texte)
            if reste <= 0 or lus >= self._fichiers_max:
                break
            if taille is not None and taille > self._plafond:
                continue
            lus += 1
            try:
                contenu = client.lire(chemin, commit, reste)
            except DepotIntrouvable:
                continue
            if contenu is not None:
                texte += f"\n\n=== {chemin} ===\n{contenu}"
        return texte[:self._plafond], commit
