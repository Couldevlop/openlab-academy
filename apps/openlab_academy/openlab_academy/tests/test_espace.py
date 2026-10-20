import pathlib
from types import SimpleNamespace
from unittest import mock

import frappe
from frappe.tests.utils import FrappeTestCase

from openlab_academy import hooks
from openlab_academy.www import espace

GABARIT = pathlib.Path(espace.__file__).with_suffix(".html")


class TestPageEspace(FrappeTestCase):
    def tearDown(self):
        frappe.set_user("Administrator")

    def contexte(self, chemin="/espace/retour/C1"):
        context = frappe._dict()
        with mock.patch.object(frappe.local, "request", SimpleNamespace(path=chemin), create=True), \
                mock.patch.object(espace.frappe.db, "commit") as commit:
            espace.get_context(context)
        return context, commit

    def test_visiteur_renvoye_vers_la_connexion_puis_vers_la_page(self):
        frappe.set_user("Guest")
        with self.assertRaises(frappe.Redirect):
            self.contexte("/espace/correcteur/C7")
        self.assertEqual(frappe.local.flags.redirect_location, "/login?redirect-to=%2Fespace%2Fcorrecteur%2FC7")

    def test_utilisateur_connecte_recoit_le_jeton_csrf_de_sa_session(self):
        frappe.set_user("Administrator")
        with mock.patch.object(espace, "version", return_value="42"):
            context, commit = self.contexte()
        self.assertEqual(context.csrf_token, frappe.sessions.get_csrf_token())
        self.assertEqual(context.version, "42")
        commit.assert_called_once()

    def test_version_du_paquet_construit_ou_zero(self):
        with mock.patch.object(espace.os.path, "getmtime", return_value=1700000000.7):
            self.assertEqual(espace.version(), "1700000000")
        with mock.patch.object(espace.os.path, "getmtime", side_effect=FileNotFoundError):
            self.assertEqual(espace.version(), "0")

    def test_gabarit_sans_donnee_et_jeton_echappe(self):
        """OWASP A03 : le jeton est sérialisé en JSON échappé ; la page ne porte aucune donnée d'évaluation."""
        html = frappe.render_template(GABARIT.read_text(encoding="utf-8"),
                                      {"csrf_token": '</script><img src=x onerror=alert(1)>', "version": "1"})
        self.assertNotIn("</script><img", html)
        self.assertNotIn("<img", html)
        self.assertIn('/assets/openlab_academy/espace/espace.js?v=1', html)
        self.assertIn('/assets/openlab_academy/css/openlab.css', html)
        self.assertIn('<div id="espace"></div>', html)

    def test_page_sans_cache_et_routee(self):
        self.assertEqual(espace.no_cache, 1)
        self.assertIn({"from_route": "/espace/<path:app_path>", "to_route": "espace"}, hooks.website_route_rules)
