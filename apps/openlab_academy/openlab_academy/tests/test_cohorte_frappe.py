import datetime

import frappe
from frappe.tests.utils import FrappeTestCase

from openlab_academy.domain.cohorte import Cohorte
from openlab_academy.domain.reglages import TITRE_LANCEMENT, Reglages
from openlab_academy.entrypoints import cohorte as commande
from openlab_academy.entrypoints import seed
from openlab_academy.infrastructure.depot_cohortes_frappe import DepotCohortesFrappe
from openlab_academy.infrastructure.depot_frappe import DepotFrappe
from openlab_academy.tests.fabriques import parcours

LUNDI = datetime.date(2026, 11, 2)
STANDARD = Reglages().rythme("standard")
TITRE_PILOTE = f"Promo 1 — {TITRE_LANCEMENT}"
FONDAMENTAUX = "Fondamentaux de la Data Science"


def supprimer_cohortes(filtre: dict) -> None:
    """Supprime les cohortes et leurs lignes (parcours, formateurs) : une suppression brute de LMS Batch laissait des
    lignes orphelines qu'une cohorte recréée sous le même nom reprenait, en doublon, après un commit."""
    lots = frappe.get_all("LMS Batch", filtre, pluck="name")
    if lots:
        frappe.db.delete("Batch Course", {"parent": ["in", lots]})
        frappe.db.delete("Course Instructor", {"parent": ["in", lots], "parenttype": "LMS Batch"})
        frappe.db.delete("LMS Batch", {"name": ["in", lots]})


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
        self.assertIn("Séances de 18 h 30 à 20 h 30 (heure d'Abidjan).", b.batch_details)
        # sans places, le LMS masque « Enroll Now » : aucune inscription autonome possible
        self.assertEqual(b.seat_count, 30)

    def test_places_et_seances_des_reglages(self):
        p = parcours(title="Parcours cohorte réglée")
        DepotFrappe(commit=False).creer(p)
        reglages = Reglages(heure_debut="19:00", heure_fin="21:00", places_par_cohorte=12)
        b = frappe.get_doc("LMS Batch", DepotCohortesFrappe().creer(Cohorte.pilote(p, LUNDI, STANDARD, reglages)))
        self.assertEqual(b.seat_count, 12)
        self.assertIn("Séances de 19 h à 21 h", b.batch_details)
        self.assertNotIn("18 h 30", b.batch_details)

    def test_lot_fenetre_cree(self):
        p = parcours(title="Parcours fenêtre test", acces_limite_a_la_cohorte=True)
        cours = DepotFrappe(commit=False).creer(p)
        depot = DepotCohortesFrappe()
        nom = depot.creer(Cohorte.fenetre(p, LUNDI, Reglages()))
        self.assertEqual(depot.trouver("Promo 1 — Parcours fenêtre test"), nom)
        b = frappe.get_doc("LMS Batch", nom)
        self.assertEqual([c.course for c in b.courses], [cours])
        self.assertEqual((str(b.start_date), str(b.end_date)), ("2026-11-02", "2026-12-02"))
        self.assertEqual((str(b.start_time).zfill(8), str(b.end_time)), ("00:00:00", "23:59:00"))
        self.assertEqual((b.allow_self_enrollment, b.seat_count, b.published), (1, 10_000, 1))
        self.assertEqual(b.description, "Parcours en vidéo, à votre rythme : quiz, exercices et projet final "
                                        "corrigé sur la plateforme.")
        self.assertEqual(b.batch_details, "<p>Ouvert du 02/11/2026 au 02/12/2026 inclus, à toute heure.</p>")

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
        frappe.db.set_single_value("Reglages OpenLab Academy", "parcours_pilote", TITRE_LANCEMENT)
        supprimer_cohortes({"title": TITRE_PILOTE})
        premiere = commande.ouvrir_pilote(commit=False)
        self.assertTrue(premiere["creee"])
        self.assertEqual(frappe.db.get_value("LMS Batch", premiere["cohorte"], "title"), TITRE_PILOTE)
        self.assertEqual(commande.ouvrir_pilote(commit=False), {"cohorte": premiere["cohorte"], "creee": False})

    def test_ouvrir_pilote_intensif(self):
        seed.run(commit=False)
        supprimer_cohortes({"title": ("like", "%· Intensif 16 h")})
        frappe.db.set_single_value("Reglages OpenLab Academy", "parcours_pilote", FONDAMENTAUX)
        resultat = commande.ouvrir_pilote(rythme="intensif", commit=False)
        b = frappe.get_doc("LMS Batch", resultat["cohorte"])
        self.assertTrue(b.title.endswith("· Intensif 16 h"))
        self.assertIn("3 h les samedi et dimanche", b.batch_details)

    def test_rythme_inconnu_refuse(self):
        with self.assertRaisesRegex(ValueError, "rythme « turbo » inconnu"):
            commande.ouvrir_pilote(rythme="turbo", commit=False)

    def test_ouverture_validee_en_base(self):
        seed.run(commit=False)
        frappe.db.set_single_value("Reglages OpenLab Academy", "parcours_pilote", TITRE_LANCEMENT)
        supprimer_cohortes({"title": TITRE_PILOTE})
        nom = commande.ouvrir_pilote(commit=True)["cohorte"]
        frappe.db.rollback()
        self.assertTrue(frappe.db.exists("LMS Batch", nom))
        # rouverte après un commit, la cohorte ne reprend aucune ligne de la précédente
        self.assertEqual(frappe.db.count("Batch Course", {"parent": nom}), 1)

    def test_non_exposee_a_l_api(self):
        """OWASP A01."""
        with self.assertRaises(frappe.PermissionError):
            frappe.is_whitelisted(commande.ouvrir_pilote)
