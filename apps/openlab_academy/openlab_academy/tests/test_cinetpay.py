"""Adaptateur CinetPay (HTTP simulé) : corps exacts, statuts, jeton de notification, clés jamais divulguées."""
import hashlib
import hmac
import traceback
import unittest
from unittest import mock

import requests

from openlab_academy.application.paiements import PaiementIndisponible
from openlab_academy.application.ports_paiement import Client, Verification
from openlab_academy.infrastructure.cinetpay import CHAMPS_JETON, PasserelleCinetPay
from openlab_academy.tests.http_simule import Reponse

SITE, CLE, SECRET = "105890", "cle-api-secrete-123", "secret-hmac-456"
POST = "requests.post"
CLIENT = Client(nom="Kouassi", prenom="Aya", email="aya@x.ci", telephone="+2250700000000")


def passerelle(site=SITE, cle=CLE, secret=SECRET):
    return PasserelleCinetPay(site, cle, secret)


def initiation(code="201", url="https://checkout.cinetpay.com/payment/abc"):
    return Reponse(json={"code": code, "message": "CREATED", "data": {"payment_token": "t", "payment_url": url}})


def verification(statut="ACCEPTED", montant="100000", devise="XOF"):
    return Reponse(json={"code": "00", "message": "SUCCES",
                         "data": {"amount": montant, "currency": devise, "status": statut}})


def initier(p=None, montant=10000):
    return (p or passerelle()).initier("OLA-d1-1", montant, "Frais d'inscription #1 / parcours_ia & co", CLIENT,
                                       "https://academy.ci/retour?cours=c", "https://academy.ci/notif")


def notification(**autres):
    corps = {"cpm_site_id": SITE, "cpm_trans_id": "OLA-d1-1", "cpm_trans_date": "2026-10-22 10:00:00",
             "cpm_amount": "10000", "cpm_currency": "XOF", "signature": "sig", "payment_method": "OM",
             "cel_phone_num": "0700000000", "cpm_phone_prefixe": "225", "cpm_language": "fr", "cpm_version": "V4",
             "cpm_payment_config": "SINGLE", "cpm_page_action": "PAYMENT", "cpm_custom": "",
             "cpm_designation": "Frais", "cpm_error_message": "SUCCES"}
    corps.update(autres)
    return corps


def jeton(corps, secret=SECRET):
    donnees = "".join(str(corps.get(c, "")) for c in CHAMPS_JETON)
    return hmac.new(secret.encode(), donnees.encode(), hashlib.sha256).hexdigest()


class TestInitier(unittest.TestCase):
    def test_corps_exact_et_url_de_paiement(self):
        with mock.patch(POST, return_value=initiation()) as post:
            url = initier()
        self.assertEqual(url, "https://checkout.cinetpay.com/payment/abc")
        (point,), options = post.call_args
        self.assertEqual(point, "https://api-checkout.cinetpay.com/v2/payment")
        self.assertEqual(options["json"], {
            "apikey": CLE, "site_id": SITE, "transaction_id": "OLA-d1-1", "amount": 10000, "currency": "XOF",
            "description": "Frais d inscription 1 parcours ia co", "notify_url": "https://academy.ci/notif",
            "return_url": "https://academy.ci/retour?cours=c", "channels": "ALL", "lang": "fr",
            "customer_name": "Kouassi", "customer_surname": "Aya", "customer_email": "aya@x.ci",
            "customer_phone_number": "+2250700000000"})
        self.assertEqual(options["timeout"], 15)
        self.assertIs(options["allow_redirects"], False)

    def test_champs_client_absents_omis(self):
        with mock.patch(POST, return_value=initiation()) as post:
            passerelle().initier("T", 5000, "d", Client(email="aya@x.ci"), "https://r", "https://n")
        corps = post.call_args.kwargs["json"]
        self.assertEqual(corps["customer_email"], "aya@x.ci")
        for champ in ("customer_name", "customer_surname", "customer_phone_number"):
            self.assertNotIn(champ, corps)

    def test_echecs_indisponibles_sans_cle_ni_secret(self):
        cas = {
            "Timeout": requests.Timeout(f"lent apikey={CLE} {SECRET}"),
            "ConnectionError": requests.ConnectionError(f"refus {CLE}"),
            "HTTP 500": Reponse(500, json={"error": CLE}),
            "HTTP 302": Reponse(302),
            "illisible": Reponse(texte=f"<html>{CLE}</html>"),
            "refus": initiation(code="608"),
            "inattendue": Reponse(json={"code": "201", "data": None}),
            "URL de paiement": initiation(url="http://evil.example/pay"),
        }
        for motif, effet in cas.items():
            with self.subTest(motif=motif), mock.patch(POST, side_effect=[effet]):
                with self.assertRaisesRegex(PaiementIndisponible, motif) as attrape:
                    initier()
                texte = "".join(traceback.format_exception(attrape.exception))
                self.assertNotIn(CLE, texte)
                self.assertNotIn(SECRET, texte)

    def test_non_configuree_refuse_sans_requete(self):
        with mock.patch(POST) as post:
            for p in (passerelle(site=""), passerelle(cle=""), passerelle(secret="")):
                with self.subTest(p=p):
                    self.assertFalse(p.disponible())
                    with self.assertRaises(PaiementIndisponible):
                        initier(p)
                    with self.assertRaises(PaiementIndisponible):
                        p.verifier("T")
        post.assert_not_called()
        self.assertTrue(passerelle().disponible())

    def test_representation_sans_secret(self):
        self.assertNotIn(CLE, repr(passerelle()))
        self.assertNotIn(SECRET, repr(passerelle()))


class TestVerifier(unittest.TestCase):
    def test_corps_exact_et_statut_accepte(self):
        with mock.patch(POST, return_value=verification()) as post:
            self.assertEqual(passerelle().verifier("OLA-d1-1"), Verification("confirme", 100000))
        (point,), options = post.call_args
        self.assertEqual(point, "https://api-checkout.cinetpay.com/v2/payment/check")
        self.assertEqual(options["json"], {"apikey": CLE, "site_id": SITE, "transaction_id": "OLA-d1-1"})
        self.assertEqual((options["timeout"], options["allow_redirects"]), (15, False))

    def test_statuts(self):
        for brut, attendu in (("REFUSED", "echoue"), ("CANCELED", "echoue"), ("WAITING_CUSTOMER_PAYMENT", "en_attente"),
                              (None, "en_attente")):
            with self.subTest(brut=brut), mock.patch(POST, return_value=verification(statut=brut, montant=5000)):
                self.assertEqual(passerelle().verifier("T"), Verification(attendu, 5000))

    def test_montant_entier_lu_en_chaine_ou_nombre(self):
        for brut in ("100000", 100000, "100000.0"):
            with self.subTest(brut=brut), mock.patch(POST, return_value=verification(montant=brut)):
                self.assertEqual(passerelle().verifier("T").montant, 100000)

    def test_reponses_inexploitables(self):
        cas = {
            "ConnectionError": requests.ConnectionError(f"x {CLE}"),
            "HTTP 400": Reponse(400, json={"message": CLE}),
            "illisible": Reponse(texte="pas du json"),
            "inattendue": Reponse(json={"code": "00", "data": []}),
            "réponse inattendue": Reponse(json=["x"]),
            "montant": verification(montant="12.5"),
            "montant ": verification(montant="abc"),
            "devise": verification(devise="EUR"),
        }
        for motif, effet in cas.items():
            with self.subTest(motif=motif), mock.patch(POST, side_effect=[effet]):
                with self.assertRaisesRegex(PaiementIndisponible, motif.strip()) as attrape:
                    passerelle().verifier("T")
                self.assertNotIn(CLE, "".join(traceback.format_exception(attrape.exception)))


class TestJeton(unittest.TestCase):
    def test_jeton_valide(self):
        corps = notification()
        self.assertTrue(passerelle().jeton_valide(corps, jeton(corps)))

    def test_champs_absents_comptes_vides(self):
        corps = {"cpm_site_id": SITE, "cpm_trans_id": "T"}
        self.assertTrue(passerelle().jeton_valide(corps, jeton(corps)))

    def test_jetons_refuses(self):
        corps = notification()
        bon = jeton(corps)
        cas = {
            "faux": (corps, "0" * 64),
            "vide": (corps, ""),
            "absent": (corps, None),
            "non ascii": (corps, "é" * 64),
            "montant falsifié": (notification(cpm_amount="5"), bon),
            "autre secret": (corps, jeton(corps, "autre")),
            "autre site": (notification(cpm_site_id="999"), jeton(notification(cpm_site_id="999"))),
        }
        for motif, (c, j) in cas.items():
            with self.subTest(motif=motif):
                self.assertFalse(passerelle().jeton_valide(c, j))

    def test_sans_secret_rien_n_est_valide(self):
        corps = notification()
        self.assertFalse(passerelle(secret="").jeton_valide(corps, jeton(corps, "")))


if __name__ == "__main__":
    unittest.main()
