"""Choix de la langue sur le banc : compte, cookie du visiteur, requête, traductions du LMS, nouveau compte."""
from unittest import mock

import frappe
from frappe.auth import CookieManager
from frappe.tests.utils import FrappeTestCase
from frappe.translate import get_language
from werkzeug.test import EnvironBuilder
from werkzeug.wrappers import Request

from openlab_academy import hooks
from openlab_academy.entrypoints import http, langue

EMAIL = "langue.test@example.ci"


def requete(cookie=None, accept=None, requete_http=""):
    entetes = {}
    if cookie is not None:
        entetes["Cookie"] = f"preferred_language={cookie}"
    if accept:
        entetes["Accept-Language"] = accept
    return Request(EnvironBuilder(path="/", query_string=requete_http, headers=entetes).get_environ())


def cookie_pose():
    return frappe.local.cookie_manager.cookies.get("preferred_language")


class Base(FrappeTestCase):
    def setUp(self):
        self.avant = {k: getattr(frappe.local, k, None) for k in ("request", "lang", "cookie_manager")}
        self.form_dict = frappe.local.form_dict
        frappe.local.cookie_manager = CookieManager()
        frappe.set_user("Administrator")
        self.langue_admin = frappe.db.get_value("User", "Administrator", "language")

    def tearDown(self):
        frappe.set_user("Administrator")
        frappe.db.set_value("User", "Administrator", "language", self.langue_admin)
        frappe.local.form_dict = self.form_dict
        for k, v in self.avant.items():
            setattr(frappe.local, k, v)
        frappe.db.rollback()

    def arriver(self, utilisateur="Guest", **kw):
        """Requête entrante : Frappe résout sa langue (HTTPRequest.set_lang), puis nos hooks before_request."""
        frappe.set_user(utilisateur)
        frappe.local.request = requete(**kw)
        frappe.local.form_dict = frappe._dict(kw.get("requete_http") and dict(
            p.split("=") for p in kw["requete_http"].split("&")) or {})
        frappe.local.lang = get_language()
        http.before_request()
        return frappe.local.lang


class TestChoisir(Base):
    def test_choisir_ecrit_la_langue_du_compte(self):
        self.assertEqual(langue.choisir("en"), "en")
        frappe.clear_document_cache("User", "Administrator")
        self.assertEqual(frappe.db.get_value("User", "Administrator", "language"), "en")

    def test_choisir_refuse_une_langue_hors_liste(self):
        frappe.db.set_value("User", "Administrator", "language", "fr")
        for valeur in ("de", "", "../en", "en<script>"):
            with self.assertRaises(frappe.ValidationError, msg=repr(valeur)):
                langue.choisir(valeur)
        self.assertEqual(frappe.db.get_value("User", "Administrator", "language"), "fr")
        self.assertIsNone(cookie_pose())

    def test_visiteur_cookie_pose(self):
        frappe.set_user("Guest")
        frappe.local.request = requete()
        self.assertEqual(langue.choisir("en"), "en")
        cookie = cookie_pose()
        self.assertEqual(cookie["value"], "en")
        self.assertTrue(cookie["httponly"])
        self.assertEqual(cookie["samesite"], "Lax")
        self.assertEqual(cookie["max_age"], 365 * 24 * 3600)

    def test_actuelle(self):
        frappe.local.lang = "en"
        self.assertEqual(langue.actuelle(), "en")
        frappe.local.lang = "de"
        self.assertEqual(langue.actuelle(), "fr")
        self.assertEqual(self.arriver(cookie="en"), "en")
        self.assertEqual(langue.actuelle(), "en")
        frappe.db.set_value("User", "Administrator", "language", "en")
        self.assertEqual(self.arriver("Administrator"), "en")
        self.assertEqual(langue.actuelle(), "en")

    def test_methode_publique_post_seulement(self):
        self.assertIn(langue.choisir, frappe.whitelisted)
        self.assertIn(langue.choisir, frappe.guest_methods)
        self.assertEqual(frappe.allowed_http_methods_for_whitelisted_func[langue.choisir], ["POST"])
        self.assertIn(langue.actuelle, frappe.guest_methods)

    def test_surcharge_declaree(self):
        self.assertEqual(hooks.override_whitelisted_methods["lms.lms.api.get_translations"],
                         "openlab_academy.entrypoints.langue.get_translations")
        self.assertEqual(hooks.doc_events["User"]["after_insert"], "openlab_academy.entrypoints.langue.initialiser_langue")
        self.assertIn("openlab_academy.entrypoints.http.before_request", hooks.before_request)


class TestRequete(Base):
    def test_visiteur_accept_language_ignore(self):
        self.assertEqual(self.arriver(accept="en-US,en;q=0.9"), "fr")

    def test_visiteur_cookie_suivi(self):
        self.assertEqual(self.arriver(cookie="en"), "en")

    def test_visiteur_cookie_invalide_ignore(self):
        self.assertEqual(self.arriver(cookie="de", accept="en"), "fr")

    def test_parametre_lang_restreint(self):
        self.assertEqual(self.arriver(cookie="en", requete_http="_lang=fr"), "fr")
        self.assertEqual(self.arriver(cookie="en", requete_http="_lang=de"), "en")
        self.assertEqual(self.arriver(requete_http="_lang=de", accept="en"), "fr")

    def test_compte_connecte_garde_sa_langue(self):
        frappe.db.set_value("User", "Administrator", "language", "en")
        self.assertEqual(self.arriver("Administrator", cookie="fr"), "en")
        self.assertEqual(self.arriver("Administrator", requete_http="_lang=de"), "en")

    def test_traductions_lms_suivent_le_visiteur(self):
        from frappe.translate import get_all_translations
        self.arriver(cookie="en")
        self.assertEqual(langue.get_translations(), get_all_translations("en"))
        self.arriver(cookie=None)
        self.assertEqual(langue.get_translations(), get_all_translations("fr"))


class TestNouveauCompte(Base):
    def creer(self, email=EMAIL):
        return frappe.get_doc({"doctype": "User", "email": email, "first_name": "Aya",
                               "send_welcome_email": 0}).insert(ignore_permissions=True)

    def test_nouveau_compte_reprend_le_cookie(self):
        frappe.local.request = requete(cookie="en")
        self.assertEqual(frappe.db.get_value("User", self.creer().name, "language"), "en")

    def test_cookie_francais_ou_invalide_laisse_le_compte(self):
        for cookie in ("fr", "de", None):
            frappe.local.request = requete(cookie=cookie)
            nom = self.creer(f"langue.{cookie}@example.ci").name
            self.assertNotEqual(frappe.db.get_value("User", nom, "language"), "en")

    def test_hors_requete(self):
        frappe.local.request = None
        self.assertNotEqual(frappe.db.get_value("User", self.creer().name, "language"), "en")

    def test_compte_existant_inchange(self):
        doc = self.creer()
        frappe.local.request = requete(cookie="en")
        frappe.db.set_value("User", doc.name, "language", "fr")
        frappe.get_doc("User", doc.name).save(ignore_permissions=True)
        self.assertEqual(frappe.db.get_value("User", doc.name, "language"), "fr")
