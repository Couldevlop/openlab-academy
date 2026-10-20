"""Adaptateur compatible OpenAI (llama.cpp server, Ollama, vLLM) : requête, délai, clé jamais divulguée."""
import traceback
import unittest
from unittest import mock

import requests

from openlab_academy.application.controler import EtapeIndisponible
from openlab_academy.infrastructure.correcteur_ia import CorrecteurCompatibleOpenAI, CorrecteurIndisponible
from openlab_academy.tests.http_simule import Reponse

CLE = "sk-secret-cle-ia-123"
MESSAGES = [{"role": "system", "content": "s"}, {"role": "user", "content": "u"}]
POST = "requests.post"


def reponse(contenu='{"criteres": {}}', statut=200):
    return Reponse(statut, json={"choices": [{"message": {"role": "assistant", "content": contenu}}]})


class TestCorrecteurCompatibleOpenAI(unittest.TestCase):
    def test_requete_deterministe_en_json_strict(self):
        with mock.patch(POST, return_value=reponse('{"ok": 1}')) as post:
            brut = CorrecteurCompatibleOpenAI("https://ia.openlab.ci/", CLE, 600).proposer(MESSAGES, "ministral-8b")
        self.assertEqual(brut, '{"ok": 1}')
        (url,), options = post.call_args
        self.assertEqual(url, "https://ia.openlab.ci/v1/chat/completions")
        self.assertEqual(options["json"], {"model": "ministral-8b", "messages": MESSAGES, "temperature": 0,
                                           "response_format": {"type": "json_object"}})
        self.assertEqual(options["headers"]["Authorization"], f"Bearer {CLE}")
        self.assertEqual(options["timeout"], 600)
        self.assertIs(options["allow_redirects"], False)

    def test_sans_cle_aucun_en_tete_d_autorisation(self):
        with mock.patch(POST, return_value=reponse()) as post:
            CorrecteurCompatibleOpenAI("http://ia:8080", "", 60).proposer(MESSAGES, "m")
        self.assertNotIn("Authorization", post.call_args.kwargs["headers"])

    def test_echecs_indisponibles_sans_la_cle(self):
        cas = {
            "Timeout": requests.Timeout(f"lent Authorization: Bearer {CLE}"),
            "ConnectionError": requests.ConnectionError(f"refus {CLE}"),
            "HTTP 500": Reponse(500, json={"error": CLE}),
            "HTTP 302": Reponse(302),
            "illisible": Reponse(texte=f"<html>{CLE}</html>"),
            "inattendue": Reponse(json={"choices": []}),
            "sans texte": reponse(contenu=None),
        }
        for motif, effet in cas.items():
            with self.subTest(motif=motif), mock.patch(POST, side_effect=[effet]):
                with self.assertRaisesRegex(CorrecteurIndisponible, motif) as attrape:
                    CorrecteurCompatibleOpenAI("https://ia.openlab.ci", CLE, 60).proposer(MESSAGES, "m")
                erreur = attrape.exception
                self.assertIsInstance(erreur, EtapeIndisponible)
                self.assertNotIn(CLE, str(erreur))
                self.assertNotIn(CLE, "".join(traceback.format_exception(erreur)))  # ce que consignerait Frappe

    def test_url_non_http_refusee_sans_requete(self):
        with mock.patch(POST) as post:
            for url in ("file:///etc/passwd", "ftp://ia", "", "https://jeton@ia.local"):
                with self.subTest(url=url), self.assertRaises(CorrecteurIndisponible):
                    CorrecteurCompatibleOpenAI(url, CLE, 60).proposer(MESSAGES, "m")
        post.assert_not_called()

    def test_cle_absente_de_la_representation(self):
        self.assertNotIn(CLE, repr(CorrecteurCompatibleOpenAI("https://ia", CLE, 60)))
