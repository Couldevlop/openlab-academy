"""Adaptateurs du port Canal : e-mail (file d'attente Frappe), SMS (API Orange), WhatsApp (API Cloud de Meta).

Les secrets (secret client Orange, jeton d'accès Orange, jeton WhatsApp) ne quittent que les en-têtes des requêtes :
aucun message d'erreur ne les contient, ni le numéro du destinataire (les exceptions d'origine ne sont ni recopiées
ni chaînées), aucune redirection n'est suivie et chaque appel a un délai.
"""
import base64
import html
import re
from collections.abc import Callable
from urllib.parse import urlsplit

import requests

from openlab_academy.application.rappels import DestinataireInjoignable, Destinataire, EnvoiImpossible, Message

DELAI_S = 15
JETON_ORANGE = "https://api.orange.com/oauth/v3/token"
SMS_ORANGE = "https://api.orange.com/smsmessaging/v1/outbound/tel%3A%2B{expediteur}/requests"
WHATSAPP = "https://graph.facebook.com/v21.0/{phone_id}/messages"
_CHIFFRES = re.compile(r"[0-9]{3,20}")


def url_jeton_valide(url: str) -> bool:
    """URL du jeton SMS : vide (adresse Orange par défaut) ou https sur `orange.com` ou un de ses sous-domaines,
    sans identifiants ; le secret client n'est ainsi jamais envoyé ailleurs."""
    url = (url or "").strip()
    if not url:
        return True
    try:
        parties = urlsplit(url)
        hote = parties.hostname or ""
        parties.port  # noqa: B018 — un port illisible lève ValueError
    except ValueError:
        return False
    return (parties.scheme == "https" and "@" not in parties.netloc
            and (hote == "orange.com" or hote.endswith(".orange.com")))


def _une_ligne(texte: str) -> str:
    return " ".join(texte.split())


def _numero(destinataire: Destinataire) -> str:
    """Numéro E.164 sans « + » ni espaces ; DestinataireInjoignable s'il manque ou n'est pas un numéro."""
    numero = re.sub(r"\s+", "", destinataire.telephone or "").removeprefix("+")
    if not _CHIFFRES.fullmatch(numero):
        raise DestinataireInjoignable("aucun numéro de téléphone")
    return numero


def _poster(canal: str, url: str, **options) -> requests.Response:
    try:
        return requests.post(url, timeout=DELAI_S, allow_redirects=False, **options)
    except requests.RequestException as erreur:
        raise EnvoiImpossible(f"{canal} injoignable ({type(erreur).__name__})") from None


class CanalEmail:
    nom = "email"

    def __init__(self, sendmail: Callable[..., object], compte_sortant: Callable[[], bool] = lambda: True):
        self._sendmail = sendmail
        self._compte_sortant = compte_sortant

    def disponible(self) -> bool:
        """Faux sans compte d'envoi par défaut : rappel `ignore` au lieu d'un échec quotidien."""
        return bool(self._compte_sortant())

    def envoyer(self, destinataire: Destinataire, message: Message) -> None:
        if not destinataire.email:
            raise DestinataireInjoignable("aucune adresse e-mail")
        self._sendmail(recipients=[destinataire.email], subject=message.sujet, message=html.escape(message.texte, quote=False),
                       delayed=True)  # corps HTML : titre et nom ne peuvent rien injecter


class CanalSms:
    """SMS Orange : jeton OAuth `client_credentials` (gardé le temps de la tâche), puis envoi du texte."""
    nom = "sms"

    def __init__(self, url_jeton: str, client_id: str, secret: str, expediteur: str):
        self._url_jeton = (url_jeton or "").strip() or JETON_ORANGE
        self._client = (client_id or "").strip()
        self._secret = secret or ""
        self._expediteur = re.sub(r"\s+", "", expediteur or "").removeprefix("+")
        self._acces = ""

    def __repr__(self) -> str:
        return f"CanalSms(expediteur={self._expediteur!r})"

    def disponible(self) -> bool:
        return bool(self._client and self._secret and self._expediteur)

    def _jeton(self) -> str:
        if self._acces:
            return self._acces
        if not url_jeton_valide(self._url_jeton):
            raise EnvoiImpossible("SMS : URL du jeton invalide")
        identite = base64.b64encode(f"{self._client}:{self._secret}".encode()).decode()
        reponse = _poster("SMS", self._url_jeton, data={"grant_type": "client_credentials"},
                          headers={"Authorization": f"Basic {identite}", "Accept": "application/json"})
        if reponse.status_code != 200:
            raise EnvoiImpossible(f"SMS : jeton refusé (HTTP {reponse.status_code})")
        try:
            acces = reponse.json().get("access_token")
        except (ValueError, AttributeError):
            acces = None
        if not isinstance(acces, str) or not acces:
            raise EnvoiImpossible("SMS : jeton illisible")
        self._acces = acces
        return acces

    def envoyer(self, destinataire: Destinataire, message: Message) -> None:
        numero = _numero(destinataire)
        if not _CHIFFRES.fullmatch(self._expediteur):
            raise EnvoiImpossible("SMS : expéditeur invalide")
        reponse = _poster("SMS", SMS_ORANGE.format(expediteur=self._expediteur),
                          headers={"Authorization": f"Bearer {self._jeton()}"},
                          json={"outboundSMSMessageRequest": {
                              "address": f"tel:+{numero}", "senderAddress": f"tel:+{self._expediteur}",
                              "outboundSMSTextMessage": {"message": message.texte}}})
        if reponse.status_code != 201:
            if reponse.status_code == 401:
                self._acces = ""  # jeton expiré : redemandé au prochain envoi
            raise EnvoiImpossible(f"SMS : réponse HTTP {reponse.status_code}")


class CanalWhatsApp:
    """Message `template` approuvé (langue `fr`) ; paramètres : nom, montant, date."""
    nom = "whatsapp"

    def __init__(self, phone_id: str, jeton: str, modele: str):
        self._phone_id = (phone_id or "").strip()
        self._jeton = jeton or ""
        self._modele = (modele or "").strip()

    def __repr__(self) -> str:
        return f"CanalWhatsApp(phone_id={self._phone_id!r}, modele={self._modele!r})"

    def disponible(self) -> bool:
        return bool(self._phone_id and self._jeton and self._modele)

    def envoyer(self, destinataire: Destinataire, message: Message) -> None:
        numero = _numero(destinataire)
        if not _CHIFFRES.fullmatch(self._phone_id):
            raise EnvoiImpossible("WhatsApp : identifiant du numéro invalide")
        reponse = _poster("WhatsApp", WHATSAPP.format(phone_id=self._phone_id),
                          headers={"Authorization": f"Bearer {self._jeton}"},
                          json={"messaging_product": "whatsapp", "to": numero, "type": "template",
                                "template": {"name": self._modele, "language": {"code": "fr"}, "components": [
                                    {"type": "body", "parameters": [{"type": "text", "text": _une_ligne(p)}
                                                                    for p in message.parametres]}]}})
        if reponse.status_code != 200:
            raise EnvoiImpossible(f"WhatsApp : réponse HTTP {reponse.status_code}")
