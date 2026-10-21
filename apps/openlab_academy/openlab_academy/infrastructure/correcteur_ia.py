"""Adaptateur du port CorrecteurIA : API `/v1/chat/completions` compatible OpenAI (llama.cpp server, Ollama, vLLM).

La clé d'accès ne quitte que l'en-tête Authorization : aucun message d'erreur ne la contient (les exceptions
d'origine ne sont ni recopiées ni chaînées), aucune redirection n'est suivie et chaque appel a un délai.
Elle ne circule en HTTP clair que vers un hôte local ou interne (conteneur voisin, adresse privée).
"""
import ipaddress
import re
from urllib.parse import urlsplit

import requests

from openlab_academy.application.controler import EtapeIndisponible

_NUMERIQUE = re.compile(r"0x[0-9a-f]*|[0-9]+", re.IGNORECASE)


def _interne(hote: str) -> bool:
    """Hôte local ou interne (localhost, nom de conteneur sans point, adresse privée) : HTTP clair toléré.
    Un hôte numérique sans point (`134744072`, `0x7f000001`), que la résolution système lit comme une IPv4, n'est
    jamais interne."""
    if _NUMERIQUE.fullmatch(hote):
        return False
    if hote == "localhost" or "." not in hote and ":" not in hote:
        return True
    try:
        adresse = ipaddress.ip_address(hote)
    except ValueError:
        return False
    adresse = getattr(adresse, "ipv4_mapped", None) or adresse  # ::ffff:8.8.8.8 est jugée sur 8.8.8.8
    return adresse.is_private or adresse.is_loopback


class CorrecteurIndisponible(EtapeIndisponible):
    """Service d'IA injoignable, trop lent ou réponse inexploitable ; message sans secret."""


class CorrecteurCompatibleOpenAI:
    def __init__(self, url: str, cle: str, delai_s: float):
        self._url = url
        self._cle = cle
        self._delai = delai_s

    def __repr__(self) -> str:
        return f"CorrecteurCompatibleOpenAI(url={self._url!r})"

    def _point(self) -> str:
        parties = urlsplit(self._url or "")
        if parties.scheme not in ("http", "https") or not parties.hostname or "@" in parties.netloc:
            raise CorrecteurIndisponible("service IA : URL invalide (http ou https sans identifiants)")
        if self._cle and parties.scheme == "http" and not _interne(parties.hostname):
            raise CorrecteurIndisponible("service IA : clé refusée en HTTP clair vers un hôte public (HTTPS requis)")
        return f"{self._url.rstrip('/')}/v1/chat/completions"

    def proposer(self, messages: list[dict], modele: str) -> str:
        url = self._point()
        entetes = {"Content-Type": "application/json"}
        if self._cle:
            entetes["Authorization"] = f"Bearer {self._cle}"
        corps = {"model": modele, "messages": messages, "temperature": 0, "response_format": {"type": "json_object"}}
        try:
            reponse = requests.post(url, json=corps, headers=entetes, timeout=self._delai, allow_redirects=False)
        except requests.RequestException as erreur:
            raise CorrecteurIndisponible(f"service IA injoignable ({type(erreur).__name__})") from None
        if reponse.status_code != 200:
            raise CorrecteurIndisponible(f"service IA : réponse HTTP {reponse.status_code}")
        try:
            donnees = reponse.json()
        except ValueError:
            raise CorrecteurIndisponible("service IA : réponse illisible") from None
        try:
            contenu = donnees["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError):
            raise CorrecteurIndisponible("service IA : réponse inattendue") from None
        if not isinstance(contenu, str):
            raise CorrecteurIndisponible("service IA : réponse sans texte")
        return contenu
