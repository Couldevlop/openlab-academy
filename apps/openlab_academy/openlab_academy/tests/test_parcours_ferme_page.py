"""Page publique /parcours-ferme/<cours> : rendue en visiteur, titre échappé, dates JJ/MM/AAAA, aucune redirection."""
import datetime
from unittest import mock
from urllib.parse import quote

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.website.serve import get_response
from werkzeug.test import EnvironBuilder
from werkzeug.wrappers import Request

from openlab_academy import hooks
from openlab_academy.domain.cohorte import Cohorte
from openlab_academy.domain.reglages import Reglages
from openlab_academy.infrastructure.depot_cohortes_frappe import DepotCohortesFrappe
from openlab_academy.infrastructure.depot_frappe import DepotFrappe
from openlab_academy.tests.fabriques import parcours
from openlab_academy.www import parcours_ferme


class TestPageParcoursFerme(FrappeTestCase):
    def setUp(self):
        frappe.cache.delete_value("website_route_rules")  # les règles de routage sont en cache sur un banc existant

    def tearDown(self):
        frappe.cache.delete_value("website_route_rules")
        frappe.set_user("Administrator")
        frappe.db.rollback()

    def cours(self, titre, debut):
        p = parcours(title=titre)
        nom = DepotFrappe(commit=False, reglages=Reglages()).creer(p)
        DepotCohortesFrappe().creer(Cohorte.fenetre(p, debut, Reglages()))
        return nom

    def rendre(self, nom, langue="fr"):
        frappe.set_user("Guest")
        self.addCleanup(setattr, frappe.local, "lang", frappe.local.lang)
        frappe.local.lang = langue
        chemin = "/parcours-ferme/" + quote(nom, safe="")
        # la règle de routage ne s'évalue que sur une vraie requête (environnement WSGI)
        requete = Request(EnvironBuilder(path=chemin).get_environ())
        with mock.patch.object(frappe.local, "request", requete, create=True):
            reponse = get_response(chemin.strip("/"))
        return reponse.status_code, reponse.get_data(as_text=True)

    def test_route_declaree(self):
        self.assertIn({"from_route": "/parcours-ferme/<cours>", "to_route": "parcours-ferme"},
                      hooks.website_route_rules)
        self.assertEqual(parcours_ferme.no_cache, 1)

    def test_parcours_ferme_affiche_titre_dates_et_catalogue(self):
        nom = self.cours("Parcours fermé test", datetime.date(2020, 1, 10))
        statut, html = self.rendre(nom)
        self.assertEqual(statut, 200)
        self.assertIn("Ce parcours est fermé", html)
        self.assertIn("« Parcours fermé test » était ouvert du 10/01/2020 au 10/02/2020.", html)
        self.assertIn('href="/lms/courses"', html)
        self.assertIn("openlab.css", html)
        self.assertIn('name="viewport"', html)

    def test_page_en_anglais(self):
        nom = self.cours("Closed course test", datetime.date(2020, 1, 10))
        statut, html = self.rendre(nom, "en")
        self.assertEqual(statut, 200)
        self.assertIn("This course is closed", html)
        self.assertIn("View the catalogue", html)
        self.assertIn("“Closed course test” was open from 10/01/2020 to 10/02/2020.", html)

    def test_titre_echappe(self):
        nom = self.cours("Parcours échappé", datetime.date(2020, 1, 10))
        frappe.db.set_value("LMS Course", nom, "title", "<b>x</b>")
        statut, html = self.rendre(nom)
        self.assertEqual(statut, 200)
        self.assertIn("&lt;b&gt;x&lt;/b&gt;", html)
        self.assertNotIn("« <b>x</b>", html)

    def test_parcours_inconnu_page_generique(self):
        statut, html = self.rendre("Parcours qui n'existe pas <i>")
        self.assertEqual(statut, 200)
        self.assertIn("Ce parcours est fermé", html)
        self.assertIn('href="/lms/courses"', html)
        self.assertNotIn("était ouvert", html)
        self.assertNotIn("ouvrira", html)
        self.assertNotIn("n'existe pas", html)

    def test_cohorte_future_ouvrira_le(self):
        nom = self.cours("Parcours à venir test", datetime.date(2099, 3, 5))
        statut, html = self.rendre(nom)
        self.assertEqual(statut, 200)
        self.assertIn("« Parcours à venir test » ouvrira le 05/03/2099.", html)
        self.assertNotIn("était ouvert", html)

    def test_contexte_sans_cohorte(self):
        nom = DepotFrappe(commit=False, reglages=Reglages()).creer(parcours(title="Sans cohorte test"))
        context = frappe._dict()
        with self._form(nom):
            parcours_ferme.get_context(context)
        self.assertEqual((context.titre, context.debut, context.fin, context.a_venir),
                         ("Sans cohorte test", "", "", False))

    def test_cohorte_non_publiee_ignoree(self):
        nom = self.cours("Cohorte non publiée test", datetime.date(2020, 1, 10))
        frappe.db.set_value("LMS Batch", {"title": ["like", "Promo 1 — Cohorte non publiée%"]}, "published", 0)
        context = frappe._dict()
        with self._form(nom):
            parcours_ferme.get_context(context)
        self.assertEqual((context.debut, context.fin), ("", ""))

    def _form(self, nom):
        return mock.patch.object(frappe.local, "form_dict", frappe._dict(cours=nom))
