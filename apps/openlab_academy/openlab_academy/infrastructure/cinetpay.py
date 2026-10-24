"""Adaptateur du port Passerelle : CinetPay (API checkout v2), francs CFA (XOF).

La clé API ne quitte que le corps des requêtes vers CinetPay et la clé secrète ne sert qu'au calcul du jeton de
notification : aucun message d'erreur ne les contient (les exceptions d'origine ne sont ni recopiées ni chaînées),
aucune redirection n'est suivie et chaque appel a un délai. Un jeton valide ne suffit pas à confirmer un paiement :
le cas d'usage interroge toujours `/v2/payment/check`.
"""
import hashlib
import hmac
import re
from decimal import Decimal, InvalidOperation
from urllib.parse import urlsplit

import requests

from openlab_academy.application.paiements import PaiementIndisponible
from openlab_academy.application.ports_paiement import Client, Verification

INITIATION = "https://api-checkout.cinetpay.com/v2/payment"
VERIFICATION = "https://api-checkout.cinetpay.com/v2/payment/check"
DELAI_S = 15
CHAMPS_JETON = (
    "cpm_site_id", "cpm_trans_id", "cpm_trans_date", "cpm_amount", "cpm_currency", "signature", "payment_method",
    "cel_phone_num", "cpm_phone_prefixe", "cpm_language", "cpm_version", "cpm_payment_config", "cpm_page_action",
    "cpm_custom", "cpm_designation", "cpm_error_message",
)
_STATUTS = {"ACCEPTED": "confirme", "REFUSED": "echoue", "CANCELED": "echoue"}
_INTERDITS = re.compile(r"[^\w .-]+|_+")  # CinetPay refuse les caractères spéciaux dans la description


class PasserelleCinetPay:
    def __init__(self, site_id: str, api_key: str, secret: str):
        self._site = site_id or ""
        self._cle = api_key or ""
        self._secret = secret or ""

    def __repr__(self) -> str:
        return f"PasserelleCinetPay(site_id={self._site!r})"

    def disponible(self) -> bool:
        return bool(self._site and self._cle and self._secret)

    def _appeler(self, url: str, corps: dict) -> dict:
        if not self.disponible():
            raise PaiementIndisponible("CinetPay : passerelle non configurée")
        try:
            reponse = requests.post(url, json=corps, timeout=DELAI_S, allow_redirects=False)
        except requests.RequestException as erreur:
            raise PaiementIndisponible(f"CinetPay injoignable ({type(erreur).__name__})") from None
        if reponse.status_code != 200:
            raise PaiementIndisponible(f"CinetPay : réponse HTTP {reponse.status_code}")
        try:
            donnees = reponse.json()
        except ValueError:
            raise PaiementIndisponible("CinetPay : réponse illisible") from None
        if not isinstance(donnees, dict):
            raise PaiementIndisponible("CinetPay : réponse inattendue")
        return donnees

    def initier(self, transaction: str, montant: int, description: str, client: Client, retour: str,
                notification: str) -> str:
        corps = {
            "apikey": self._cle, "site_id": self._site, "transaction_id": transaction, "amount": montant,
            "currency": "XOF", "description": " ".join(_INTERDITS.sub(" ", description).split()),
            "notify_url": notification, "return_url": retour, "channels": "ALL", "lang": "fr",
        }
        for champ, valeur in (("customer_name", client.nom), ("customer_surname", client.prenom),
                              ("customer_email", client.email), ("customer_phone_number", client.telephone)):
            if valeur:
                corps[champ] = valeur
        donnees = self._appeler(INITIATION, corps)
        if str(donnees.get("code")) != "201":
            raise PaiementIndisponible(f"CinetPay : refus de l'initiation (code {str(donnees.get('code'))[:10]})")
        try:
            url = donnees["data"]["payment_url"]
        except (KeyError, TypeError):
            raise PaiementIndisponible("CinetPay : réponse inattendue") from None
        if not isinstance(url, str) or urlsplit(url).scheme != "https" or not urlsplit(url).hostname:
            raise PaiementIndisponible("CinetPay : URL de paiement invalide")
        return url

    def verifier(self, transaction: str) -> Verification:
        donnees = self._appeler(VERIFICATION, {"apikey": self._cle, "site_id": self._site,
                                               "transaction_id": transaction})
        data = donnees.get("data")
        if not isinstance(data, dict):
            raise PaiementIndisponible("CinetPay : réponse inattendue")
        if data.get("currency") not in (None, "XOF"):
            raise PaiementIndisponible("CinetPay : devise inattendue")
        try:
            montant = Decimal(str(data.get("amount")))
        except InvalidOperation:
            raise PaiementIndisponible("CinetPay : montant illisible") from None
        if not montant.is_finite() or montant != montant.to_integral_value():
            raise PaiementIndisponible("CinetPay : montant non entier")
        return Verification(_STATUTS.get(data.get("status"), "en_attente"), int(montant))

    def jeton_valide(self, corps: dict, x_token: str | None) -> bool:
        """HMAC SHA-256 (hexadécimal, clé secrète) des champs `cpm_*` concaténés dans l'ordre documenté, comparé à
        temps constant ; le site doit être le nôtre. Un champ absent compte pour une chaîne vide."""
        if not self._secret or not x_token or str(corps.get("cpm_site_id", "")) != self._site:
            return False
        donnees = "".join(str(corps.get(champ) or "") for champ in CHAMPS_JETON)
        attendu = hmac.new(self._secret.encode(), donnees.encode(), hashlib.sha256).hexdigest()
        return hmac.compare_digest(attendu.encode(), x_token.encode("utf-8", "replace"))
