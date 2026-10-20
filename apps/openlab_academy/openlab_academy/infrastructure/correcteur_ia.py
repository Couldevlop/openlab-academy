"""Adaptateur du port CorrecteurIA : API `/v1/chat/completions` compatible OpenAI (llama.cpp server, Ollama, vLLM).

La clé d'accès ne quitte que l'en-tête Authorization : aucun message d'erreur ne la contient (les exceptions
d'origine ne sont ni recopiées ni chaînées), aucune redirection n'est suivie et chaque appel a un délai.
"""
from urllib.parse import urlsplit

import requests

from openlab_academy.application.controler import EtapeIndisponible


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
