import frappe
from frappe.tests.utils import FrappeTestCase

from openlab_academy.domain.reglages import Reglages
from openlab_academy.infrastructure import reglages_source_frappe as source
from openlab_academy.patches import initialiser_reglages

DOCTYPE = "Reglages OpenLab Academy"
ELEVE = "eleve.reglages@example.ci"


def vider():
    doc = frappe.get_single(DOCTYPE)
    for table in ("bareme", "exigences", "rythmes"):
        doc.set(table, [])
    doc.flags.ignore_validate = True
    doc.save(ignore_permissions=True)


class TestSourceReglagesFrappe(FrappeTestCase):
    def tearDown(self):
        frappe.set_user("Administrator")
        frappe.db.rollback()

    def test_reglages_par_defaut_si_jamais_initialises(self):
        vider()
        self.assertEqual(source.charger(), Reglages())

    def test_initialisation_reproduit_les_valeurs_par_defaut(self):
        vider()
        source.initialiser()
        doc = frappe.get_single(DOCTYPE)
        self.assertEqual((len(doc.bareme), len(doc.rythmes)), (5, 2))
        self.assertEqual(source.charger(), Reglages())

    def test_initialisation_ne_ecrase_pas_les_reglages_existants(self):
        source.initialiser()
        doc = frappe.get_single(DOCTYPE)
        doc.heures_par_module = 6
        doc.save(ignore_permissions=True)
        source.initialiser()
        self.assertEqual(source.charger().heures_par_module, 6)

    def test_modification_dans_l_ecran_prise_en_compte(self):
        source.initialiser()
        doc = frappe.get_single(DOCTYPE)
        doc.update({"heures_par_module": 6, "jour_ouverture": "Samedi", "heure_debut": "19:00:00",
                    "heure_fin": "21:00:00", "parcours_pilote": "Développeur Python"})
        doc.append("rythmes", {"code": "week-end", "libelle": "Week-end", "samedi": 5, "dimanche": 5})
        doc.save(ignore_permissions=True)
        r = source.charger()
        self.assertEqual((r.heures_par_module, r.jour_ouverture, r.heure_debut, r.heure_fin, r.parcours_pilote),
                         (6, 5, "19:00", "21:00", "Développeur Python"))
        self.assertEqual(r.rythme("week-end").heures, 10)

    def test_reglage_incoherent_refuse_a_l_enregistrement(self):
        source.initialiser()
        doc = frappe.get_single(DOCTYPE)
        doc.bareme[0].poids = 10  # total 70 %
        with self.assertRaisesRegex(frappe.ValidationError, "barème : total 70 % au lieu de 100 %"):
            doc.save(ignore_permissions=True)

    def test_rythme_vide_refuse(self):
        source.initialiser()
        doc = frappe.get_single(DOCTYPE)
        doc.append("rythmes", {"code": "vide", "libelle": "Vide"})
        with self.assertRaisesRegex(frappe.ValidationError, "aucune heure"):
            doc.save(ignore_permissions=True)

    def test_patch_d_initialisation(self):
        vider()
        initialiser_reglages.execute()
        self.assertEqual(len(frappe.get_single(DOCTYPE).rythmes), 2)


class TestDroitsReglages(FrappeTestCase):
    """OWASP A01 : seuls les administrateurs système lisent et modifient les réglages."""

    def setUp(self):
        if not frappe.db.exists("User", ELEVE):
            frappe.get_doc({"doctype": "User", "email": ELEVE, "first_name": "Élève",
                            "send_welcome_email": 0, "roles": [{"role": "LMS Student"}]}).insert(ignore_permissions=True)

    def tearDown(self):
        frappe.set_user("Administrator")
        frappe.db.rollback()

    def test_apprenant_ne_lit_pas(self):
        frappe.set_user(ELEVE)
        self.assertFalse(frappe.has_permission(DOCTYPE, "read"))
        with self.assertRaises(frappe.PermissionError):
            frappe.get_doc(DOCTYPE).check_permission("read")

    def test_apprenant_ne_modifie_pas(self):
        frappe.set_user(ELEVE)
        self.assertFalse(frappe.has_permission(DOCTYPE, "write"))
        doc = frappe.get_doc(DOCTYPE)
        doc.heures_par_module = 1
        with self.assertRaises(frappe.PermissionError):
            doc.save()

    def test_administrateur_systeme_autorise(self):
        self.assertTrue(frappe.has_permission(DOCTYPE, "write"))
