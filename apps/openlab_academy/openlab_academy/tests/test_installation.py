import frappe
from frappe.tests.utils import FrappeTestCase

from openlab_academy.entrypoints import install
from openlab_academy.infrastructure import reglages_frappe


class TestReglages(FrappeTestCase):
    def tearDown(self):
        frappe.db.rollback()

    def test_plateforme_en_francais_fcfa_abidjan(self):
        reglages_frappe.appliquer()
        s = frappe.get_single("System Settings")
        self.assertEqual((s.language, s.time_zone, s.currency, s.date_format),
                         ("fr", "Africa/Abidjan", "XOF", "dd-mm-yyyy"))
        self.assertEqual(frappe.db.get_single_value("LMS Settings", "default_currency"), "XOF")
        w = frappe.get_single("Website Settings")
        self.assertEqual((w.app_name, w.app_logo), ("OpenLab Academy", "/assets/openlab_academy/images/logo.svg"))

    def test_devise_xof_sans_decimales(self):
        frappe.db.delete("Currency", {"name": "XOF"})
        reglages_frappe.appliquer()
        xof = frappe.get_doc("Currency", "XOF")
        self.assertEqual((xof.enabled, xof.symbol, xof.fraction_units), (1, "FCFA", 0))

    def test_idempotent(self):
        reglages_frappe.appliquer()
        reglages_frappe.appliquer()
        self.assertEqual(frappe.db.count("Currency", {"name": "XOF"}), 1)


class TestInstallation(FrappeTestCase):
    def tearDown(self):
        frappe.db.rollback()

    def test_after_install_configure_et_publie(self):
        install.after_install(commit=False)
        self.assertEqual(frappe.db.get_single_value("System Settings", "language"), "fr")
        self.assertTrue(frappe.db.exists("LMS Course", {"title": "Fondamentaux de la Data Science"}))
        self.assertTrue(frappe.db.exists("LMS Batch", {"title": "Promo 1 — Fondamentaux de la Data Science · Standard 12 h"}))

    def test_after_migrate_republie_les_parcours(self):
        self.assertIn("openlab_academy.entrypoints.install.after_migrate", frappe.get_hooks("after_migrate"))
        frappe.db.set_value("LMS Course", {"title": "AI Engineer"}, "short_introduction", "périmé")
        install.after_migrate(commit=False)
        self.assertNotEqual(frappe.db.get_value("LMS Course", {"title": "AI Engineer"}, "short_introduction"),
                            "périmé")

    def test_installation_non_exposee_a_l_api(self):
        """OWASP A01 : aucune fonction d'installation n'est appelable via /api/method."""
        for fonction in (install.after_install, install.after_migrate, reglages_frappe.appliquer):
            with self.subTest(fonction=fonction.__name__), self.assertRaises(frappe.PermissionError):
                frappe.is_whitelisted(fonction)
