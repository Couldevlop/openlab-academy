import datetime

import frappe
from frappe.tests.utils import FrappeTestCase

from openlab_academy.domain.cohorte import Cohorte
from openlab_academy.domain.reglages import Reglages
from openlab_academy.entrypoints import cohorte as commande
from openlab_academy.entrypoints import seed
from openlab_academy.infrastructure.depot_cohortes_frappe import DepotCohortesFrappe
from openlab_academy.infrastructure.depot_frappe import DepotFrappe
from openlab_academy.tests.fabriques import parcours

LUNDI = datetime.date(2026, 11, 2)
STANDARD = Reglages().rythme("standard")
TITRE_PILOTE = "Promo 1 — Fondamentaux de la Data Science · Standard 12 h"


class TestDepotCohortesFrappe(FrappeTestCase):
    def tearDown(self):
        frappe.db.rollback()

    def test_creation_lms_batch(self):
        p = parcours(title="Parcours cohorte test")
        cours = DepotFrappe(commit=False).creer(p)
        depot = DepotCohortesFrappe()
        nom = depot.creer(Cohorte.pilote(p, LUNDI, STANDARD, Reglages()))
        self.assertEqual(depot.trouver("Promo 1 — Parcours cohorte test · Standard 12 h"), nom)
        b = frappe.get_doc("LMS Batch", nom)
        self.assertEqual([c.course for c in b.courses], [cours])
        self.assertEqual((b.paid_batch, b.published, b.medium, b.timezone), (0, 1, "Online", "Africa/Abidjan"))
        self.assertEqual((str(b.start_date), str(b.end_date)), ("2026-11-02", "2027-02-22"))
        self.assertEqual((str(b.start_time), str(b.end_time)), ("18:30:00", "20:30:00"))
        self.assertEqual((b.allow_self_enrollment, b.certification, b.evaluation), (1, 1, 1))
        self.assertIn("12 h par semaine", b.batch_details)

    def test_cours_absent_refuse(self):
        with self.assertRaisesRegex(ValueError, "cours « Inconnu » introuvable"):
            DepotCohortesFrappe().creer(Cohorte.pilote(parcours(title="Inconnu"), LUNDI, STANDARD, Reglages()))

    def test_inconnue(self):
        self.assertIsNone(DepotCohortesFrappe().trouver("Promo 1 — rien"))


class TestCommandeCohorte(FrappeTestCase):
    def tearDown(self):
        frappe.db.rollback()

    def test_ouvrir_pilote_idempotent(self):
        seed.run(commit=False)
        frappe.db.delete("LMS Batch", {"title": TITRE_PILOTE})
        premiere = commande.ouvrir_pilote(commit=False)
        self.assertTrue(premiere["creee"])
        self.assertEqual(frappe.db.get_value("LMS Batch", premiere["cohorte"], "title"), TITRE_PILOTE)
        self.assertEqual(commande.ouvrir_pilote(commit=False), {"cohorte": premiere["cohorte"], "creee": False})

    def test_ouvrir_pilote_intensif(self):
        seed.run(commit=False)
        resultat = commande.ouvrir_pilote(rythme="intensif", commit=False)
        b = frappe.get_doc("LMS Batch", resultat["cohorte"])
        self.assertTrue(b.title.endswith("· Intensif 16 h"))
        self.assertIn("3 h le samedi et le dimanche", b.batch_details)

    def test_rythme_inconnu_refuse(self):
        with self.assertRaisesRegex(ValueError, "rythme « turbo » inconnu"):
            commande.ouvrir_pilote(rythme="turbo", commit=False)

    def test_ouverture_validee_en_base(self):
        seed.run(commit=False)
        frappe.db.delete("LMS Batch", {"title": TITRE_PILOTE})
        nom = commande.ouvrir_pilote(commit=True)["cohorte"]
        frappe.db.rollback()
        self.assertTrue(frappe.db.exists("LMS Batch", nom))

    def test_non_exposee_a_l_api(self):
        """OWASP A01."""
        with self.assertRaises(frappe.PermissionError):
            frappe.is_whitelisted(commande.ouvrir_pilote)
