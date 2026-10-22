"""Canaux de rappel (HTTP simulé) : corps exacts SMS Orange et WhatsApp, disponibilité, aucun jeton divulgué."""
import base64
import traceback
import unittest
from unittest import mock

import requests

from openlab_academy.application.rappels import DestinataireInjoignable, Destinataire, EnvoiImpossible, Message
from openlab_academy.infrastructure.canaux import (
    JETON_ORANGE, CanalEmail, CanalSms, CanalWhatsApp)
from openlab_academy.tests.http_simule import Reponse

POST = "requests.post"
CLIENT_ID, SECRET_SMS, JETON_WA = "client-orange", "secret-orange-789", "EAAG-jeton-wa-321"
AYA = Destinataire("aya@x.ci", "+2250700000000", "Aya Kouassi")
MESSAGE = Message("Rappel de paiement : Parcours IA", "Rappel OpenLab Academy : 50 000 FCFA ...",
                  ("Aya Kouassi", "50 000", "10/11/2026"))
SMS_URL = "https://api.orange.com/smsmessaging/v1/outbound/tel%3A%2B2250000/requests"


def sms(url_jeton="", client=CLIENT_ID, secret=SECRET_SMS, expediteur="+2250000"):
    return CanalSms(url_jeton, client, secret, expediteur)


def whatsapp(phone_id="1234567890", jeton=JETON_WA, modele="rappel_paiement"):
    return CanalWhatsApp(phone_id, jeton, modele)


def jeton_orange(statut=200, json=None):
    return Reponse(statut, json={"token_type": "Bearer", "access_token": "acces-orange-555", "expires_in": 3600}
                   if json is None else json)


class Routeur:
    """Réponses par URL, dans l'ordre ; consigne chaque appel."""

    def __init__(self, **reponses):
        self.reponses = {cle: list(v) if isinstance(v, list) else [v] for cle, v in reponses.items()}
        self.appels = []

    def __call__(self, url, **options):
        self.appels.append((url, options))
        cle = "jeton" if "oauth" in url else "envoi"
        reponse = self.reponses[cle].pop(0) if len(self.reponses[cle]) > 1 else self.reponses[cle][0]
        if isinstance(reponse, Exception):
            raise reponse
        return reponse


def sans_secret(test, erreur):
    texte = "".join(traceback.format_exception(erreur))
    for secret in (SECRET_SMS, JETON_WA, "acces-orange-555", base64.b64encode(f"{CLIENT_ID}:{SECRET_SMS}".encode()).decode(),
                   "0700000000"):
        test.assertNotIn(secret, texte)
    test.assertIsNone(erreur.__cause__)
    test.assertTrue(erreur.__suppress_context__ or erreur.__context__ is None)


class TestCanalEmail(unittest.TestCase):
    def test_file_d_attente(self):
        envois = []
        canal = CanalEmail(lambda **kw: envois.append(kw))
        self.assertTrue(canal.disponible())
        self.assertEqual(canal.nom, "email")
        canal.envoyer(AYA, MESSAGE)
        self.assertEqual(envois, [{"recipients": ["aya@x.ci"], "subject": MESSAGE.sujet, "message": MESSAGE.texte,
                                   "delayed": True}])

    def test_sans_adresse(self):
        with self.assertRaises(DestinataireInjoignable):
            CanalEmail(lambda **kw: None).envoyer(Destinataire("", "+2250700000000", "Aya"), MESSAGE)


class TestCanalSms(unittest.TestCase):
    def test_disponible_si_les_trois_champs_sont_saisis(self):
        self.assertTrue(sms().disponible())
        self.assertEqual(sms().nom, "sms")
        for champs in ({"client": ""}, {"secret": ""}, {"expediteur": " "}):
            self.assertFalse(sms(**champs).disponible(), champs)

    def test_jeton_puis_envoi_corps_exacts(self):
        routeur = Routeur(jeton=jeton_orange(), envoi=Reponse(201, json={}))
        with mock.patch(POST, routeur):
            sms().envoyer(AYA, MESSAGE)
        (url_jeton, jeton), (url_envoi, envoi) = routeur.appels
        self.assertEqual(url_jeton, JETON_ORANGE)
        self.assertEqual(jeton["data"], {"grant_type": "client_credentials"})
        self.assertEqual(jeton["headers"], {
            "Authorization": "Basic " + base64.b64encode(f"{CLIENT_ID}:{SECRET_SMS}".encode()).decode(),
            "Accept": "application/json"})
        self.assertEqual(url_envoi, SMS_URL)
        self.assertEqual(envoi["headers"], {"Authorization": "Bearer acces-orange-555"})
        self.assertEqual(envoi["json"], {"outboundSMSMessageRequest": {
            "address": "tel:+2250700000000", "senderAddress": "tel:+2250000",
            "outboundSMSTextMessage": {"message": MESSAGE.texte}}})
        for _, options in routeur.appels:
            self.assertEqual((options["timeout"], options["allow_redirects"]), (15, False))

    def test_url_de_jeton_reglee_et_jeton_reutilise(self):
        routeur = Routeur(jeton=jeton_orange(), envoi=Reponse(201, json={}))
        canal = sms(url_jeton=" https://api.orange.com/oauth/v3/token-ci ")
        with mock.patch(POST, routeur):
            canal.envoyer(AYA, MESSAGE)
            canal.envoyer(AYA, MESSAGE)
        self.assertEqual([u for u, _ in routeur.appels],
                         ["https://api.orange.com/oauth/v3/token-ci", SMS_URL, SMS_URL])

    def test_sans_numero(self):
        with mock.patch(POST) as post, self.assertRaises(DestinataireInjoignable):
            sms().envoyer(Destinataire("aya@x.ci", "", "Aya"), MESSAGE)
        post.assert_not_called()

    def test_expediteur_invalide(self):
        with mock.patch(POST) as post, self.assertRaisesRegex(EnvoiImpossible, "expéditeur invalide"):
            sms(expediteur="225/../x").envoyer(AYA, MESSAGE)
        post.assert_not_called()

    def test_url_de_jeton_non_https_refusee(self):
        with mock.patch(POST) as post, self.assertRaisesRegex(EnvoiImpossible, "URL du jeton invalide"):
            sms(url_jeton="http://api.orange.com/oauth").envoyer(AYA, MESSAGE)
        post.assert_not_called()

    def test_erreurs_sans_secret(self):
        cas = [
            (Routeur(jeton=requests.Timeout(f"secret {SECRET_SMS}")), "SMS injoignable \\(Timeout\\)"),
            (Routeur(jeton=jeton_orange(401)), "SMS : jeton refusé \\(HTTP 401\\)"),
            (Routeur(jeton=Reponse(200, texte="<html>")), "SMS : jeton illisible"),
            (Routeur(jeton=jeton_orange(json=["x"])), "SMS : jeton illisible"),
            (Routeur(jeton=jeton_orange(json={"access_token": ""})), "SMS : jeton illisible"),
            (Routeur(jeton=jeton_orange(), envoi=Reponse(400, json={"jeton": "acces-orange-555"})),
             "SMS : réponse HTTP 400"),
            (Routeur(jeton=jeton_orange(), envoi=requests.ConnectionError("acces-orange-555")),
             "SMS injoignable \\(ConnectionError\\)"),
        ]
        for routeur, motif in cas:
            with self.subTest(motif=motif), mock.patch(POST, routeur), self.assertRaisesRegex(EnvoiImpossible, motif) as e:
                sms().envoyer(AYA, MESSAGE)
            sans_secret(self, e.exception)

    def test_jeton_expire_redemande(self):
        routeur = Routeur(jeton=jeton_orange(), envoi=[Reponse(401, json={}), Reponse(201, json={})])
        canal = sms()
        with mock.patch(POST, routeur):
            with self.assertRaises(EnvoiImpossible):
                canal.envoyer(AYA, MESSAGE)
            canal.envoyer(AYA, MESSAGE)
        self.assertEqual(sum("oauth" in u for u, _ in routeur.appels), 2)

    def test_repr_sans_secret(self):
        self.assertNotIn(SECRET_SMS, repr(sms()))


class TestCanalWhatsApp(unittest.TestCase):
    def test_disponible_si_numero_jeton_et_modele(self):
        self.assertTrue(whatsapp().disponible())
        self.assertEqual(whatsapp().nom, "whatsapp")
        for champs in ({"phone_id": ""}, {"jeton": ""}, {"modele": ""}):
            self.assertFalse(whatsapp(**champs).disponible(), champs)

    def test_corps_exact(self):
        with mock.patch(POST, return_value=Reponse(200, json={"messages": [{"id": "wamid"}]})) as post:
            whatsapp().envoyer(AYA, MESSAGE)
        (url,), options = post.call_args
        self.assertEqual(url, "https://graph.facebook.com/v21.0/1234567890/messages")
        self.assertEqual(options["headers"], {"Authorization": f"Bearer {JETON_WA}"})
        self.assertEqual(options["json"], {
            "messaging_product": "whatsapp", "to": "2250700000000", "type": "template",
            "template": {"name": "rappel_paiement", "language": {"code": "fr"}, "components": [
                {"type": "body", "parameters": [{"type": "text", "text": "Aya Kouassi"},
                                                {"type": "text", "text": "50 000"},
                                                {"type": "text", "text": "10/11/2026"}]}]}})
        self.assertEqual((options["timeout"], options["allow_redirects"]), (15, False))

    def test_sans_numero(self):
        with mock.patch(POST) as post, self.assertRaises(DestinataireInjoignable):
            whatsapp().envoyer(Destinataire("aya@x.ci", "", "Aya"), MESSAGE)
        post.assert_not_called()

    def test_identifiant_invalide(self):
        with mock.patch(POST) as post, self.assertRaisesRegex(EnvoiImpossible, "identifiant du numéro invalide"):
            whatsapp(phone_id="12/../me").envoyer(AYA, MESSAGE)
        post.assert_not_called()

    def test_erreurs_sans_secret(self):
        for effet, motif in ((requests.Timeout(JETON_WA), "WhatsApp injoignable \\(Timeout\\)"),
                             (Reponse(401, json={"error": JETON_WA}), "WhatsApp : réponse HTTP 401")):
            with self.subTest(motif=motif), mock.patch(POST, side_effect=[effet]), \
                    self.assertRaisesRegex(EnvoiImpossible, motif) as e:
                whatsapp().envoyer(AYA, MESSAGE)
            sans_secret(self, e.exception)

    def test_repr_sans_secret(self):
        self.assertNotIn(JETON_WA, repr(whatsapp()))


if __name__ == "__main__":
    unittest.main()
