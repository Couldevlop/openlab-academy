import datetime
import json
import os

import frappe
from frappe.tests.utils import FrappeTestCase

from openlab_academy.domain.lancement import PhaseLancement
from openlab_academy.domain.reglages import Reglages
from openlab_academy.infrastructure import reglages_source_frappe as source
from openlab_academy.infrastructure.depot_dossiers_frappe import ReglagesPaiementFrappe
from openlab_academy.infrastructure.inscriptions_frappe import ReglagesInscriptionFrappe
from openlab_academy.patches import completer_places_cohortes, completer_reglages_exercices, initialiser_reglages

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
        vider()
        source.initialiser()
        doc = frappe.get_single(DOCTYPE)
        doc.update({"heures_par_module": 6, "jour_ouverture": "Samedi", "heure_debut": "19:00:00",
                    "questions_par_quiz": 4, "tentatives_max": 2, "score_min": 80, "delai_exercices_minutes": 30,
                    "heure_fin": "21:00:00", "parcours_pilote": "Développeur Python", "places_par_cohorte": 12})
        doc.append("rythmes", {"code": "week-end", "libelle": "Week-end", "samedi": 5, "dimanche": 5})
        doc.save(ignore_permissions=True)
        r = source.charger()
        self.assertEqual((r.heures_par_module, r.jour_ouverture, r.heure_debut, r.heure_fin, r.parcours_pilote),
                         (6, 5, "19:00", "21:00", "Développeur Python"))
        self.assertEqual(r.rythme("week-end").heures, 10)
        self.assertEqual(r.places_par_cohorte, 12)
        self.assertEqual((r.questions_par_quiz, r.tentatives_max, r.score_min, r.delai_exercices_minutes),
                         (4, 2, 80, 30))

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


class TestLancementFrappe(FrappeTestCase):
    def tearDown(self):
        frappe.set_user("Administrator")
        frappe.db.rollback()

    def cours(self, titre):
        return frappe.get_doc({"doctype": "LMS Course", "title": titre, "short_introduction": "i",
                               "description": "d", "instructors": [{"instructor": "Administrator"}]}
                              ).insert(ignore_permissions=True).name

    def test_phase_lancement_lue(self):
        nom = self.cours("Lancement réglages")
        doc = frappe.get_single(DOCTYPE)
        doc.phase_lancement = 1
        doc.set("parcours_lancement", [{"cours": nom}])
        doc.save(ignore_permissions=True)
        self.assertEqual(source.phase_lancement(), PhaseLancement(True, frozenset({nom})))

    def test_phase_decochee(self):
        nom = self.cours("Lancement décoché")
        doc = frappe.get_single(DOCTYPE)
        doc.phase_lancement = 0
        doc.set("parcours_lancement", [{"cours": nom}])
        doc.save(ignore_permissions=True)
        self.assertEqual(source.phase_lancement(), PhaseLancement(False, frozenset({nom})))

    def test_case_changee_vue_par_la_requete_suivante(self):
        """Le single est lu en cache : l'enregistrement doit l'invalider."""
        frappe.db.set_single_value(DOCTYPE, "phase_lancement", 1)
        frappe.clear_document_cache(DOCTYPE, DOCTYPE)
        self.assertTrue(source.phase_lancement().active)
        doc = frappe.get_single(DOCTYPE)
        doc.phase_lancement = 0
        doc.save(ignore_permissions=True)
        self.assertFalse(source.phase_lancement().active)
        doc.phase_lancement = 1
        doc.save(ignore_permissions=True)
        self.assertTrue(source.phase_lancement().active)

    def test_initialiser_coche_la_phase(self):
        vider()
        frappe.db.set_single_value(DOCTYPE, "phase_lancement", 0)
        source.initialiser()
        self.assertEqual(frappe.db.get_single_value(DOCTYPE, "phase_lancement"), 1)
        self.assertTrue(source.phase_lancement().active)

    def test_ouverture_lancement_vers_domaine(self):
        vider()
        source.initialiser()
        self.assertIsNone(source.charger().ouverture_lancement)
        doc = frappe.get_single(DOCTYPE)
        doc.ouverture_lancement = "2026-11-16"
        doc.save(ignore_permissions=True)
        self.assertEqual(source.charger().ouverture_lancement, datetime.date(2026, 11, 16))

    def test_ecran_reserve_a_l_administrateur(self):
        mail = "moderateur.reglages@example.ci"
        if not frappe.db.exists("User", mail):
            frappe.get_doc({"doctype": "User", "email": mail, "first_name": "Modo", "send_welcome_email": 0,
                            "roles": [{"role": "Moderator"}]}).insert(ignore_permissions=True)
        frappe.set_user(mail)
        doc = frappe.get_doc(DOCTYPE)
        doc.phase_lancement = 0
        with self.assertRaises(frappe.PermissionError):
            doc.save()

    def test_ecran_sans_acces_pour_apprenant_et_formateur(self):
        for mail, role in ((ELEVE, "LMS Student"), ("formateur.reglages@example.ci", "Course Creator")):
            if not frappe.db.exists("User", mail):
                frappe.get_doc({"doctype": "User", "email": mail, "first_name": "Test", "send_welcome_email": 0,
                                "roles": [{"role": role}]}).insert(ignore_permissions=True)
            with self.subTest(role=role):
                for droit in ("read", "write"):
                    self.assertFalse(frappe.has_permission(DOCTYPE, droit, user=mail))
        chemin = os.path.join(os.path.dirname(__file__), "..", "openlab_academy", "doctype",
                              "reglages_openlab_academy", "reglages_openlab_academy.json")
        with open(chemin, encoding="utf-8") as f:
            self.assertEqual({p["role"] for p in json.load(f)["permissions"]}, {"System Manager"})


class TestSuspensionDesInscriptions(FrappeTestCase):
    """Le réglage qui ferme la façade publique, et ce qu'il vaut quand personne ne l'a touché."""

    def tearDown(self):
        frappe.set_user("Administrator")
        frappe.db.rollback()

    def test_absent_le_reglage_vaut_suspendu(self):
        """Un réglage jamais renseigné ne doit pas ouvrir les inscriptions : l'oubli ferme, il
        n'ouvre pas. C'est le réglage nommé par l'ouverture qui le garantit."""
        frappe.db.delete("Singles", {"doctype": DOCTYPE, "field": "inscriptions_ouvertes"})
        frappe.clear_document_cache(DOCTYPE, DOCTYPE)
        self.assertTrue(source.inscriptions_suspendues())

    def test_coche_il_rouvre_les_inscriptions(self):
        doc = frappe.get_single(DOCTYPE)
        doc.inscriptions_ouvertes = 1
        doc.save(ignore_permissions=True)
        self.assertFalse(source.inscriptions_suspendues())

    def test_decoche_il_les_suspend(self):
        doc = frappe.get_single(DOCTYPE)
        doc.inscriptions_ouvertes = 0
        doc.save(ignore_permissions=True)
        self.assertTrue(source.inscriptions_suspendues())

    def test_case_changee_vue_par_la_requete_suivante(self):
        """Rouvrir les inscriptions ne doit pas attendre un redémarrage : le single est lu en cache,
        et l'enregistrement doit l'invalider."""
        doc = frappe.get_single(DOCTYPE)
        doc.inscriptions_ouvertes = 0
        doc.save(ignore_permissions=True)
        self.assertTrue(source.inscriptions_suspendues())
        doc.inscriptions_ouvertes = 1
        doc.save(ignore_permissions=True)
        self.assertFalse(source.inscriptions_suspendues())

    def test_l_adaptateur_du_cas_d_usage_lit_le_meme_reglage(self):
        """`ReglagesInscriptionFrappe` sert le cas d'usage public : s'il lisait ailleurs, la page et
        le serveur divergeraient."""
        doc = frappe.get_single(DOCTYPE)
        doc.inscriptions_ouvertes = 0
        doc.save(ignore_permissions=True)
        self.assertTrue(ReglagesInscriptionFrappe(ReglagesPaiementFrappe()).inscriptions_suspendues())


class TestPatchExercices(FrappeTestCase):
    def tearDown(self):
        frappe.db.rollback()

    def test_site_existant_recoit_les_valeurs_par_defaut(self):
        source.initialiser()
        for champ in ("questions_par_quiz", "tentatives_max", "score_min", "delai_exercices_minutes"):
            frappe.db.set_single_value(DOCTYPE, champ, None)
        completer_reglages_exercices.execute()
        r = source.charger()
        self.assertEqual((r.questions_par_quiz, r.tentatives_max, r.score_min, r.delai_exercices_minutes),
                         (5, 3, 100, 60))

    def test_valeurs_existantes_conservees(self):
        source.initialiser()
        frappe.db.set_single_value(DOCTYPE, "score_min", 90)
        completer_reglages_exercices.execute()
        self.assertEqual(source.charger().score_min, 90)


class TestPatchPlaces(FrappeTestCase):
    """Sites existants : réglage des places renseigné, cohortes en inscription autonome sans places complétées."""

    def tearDown(self):
        frappe.db.rollback()

    def lot(self, titre, **champs):
        cours = frappe.get_all("LMS Course", pluck="name", limit=1)[0]
        return frappe.get_doc({"doctype": "LMS Batch", "title": titre, "start_date": "2026-11-02",
                               "end_date": "2027-02-22", "start_time": "18:30:00", "end_time": "20:30:00",
                               "timezone": "Africa/Abidjan", "instructors": [{"instructor": "Administrator"}],
                               "description": "d", "batch_details": "d", "courses": [{"course": cours}],
                               **champs}).insert(ignore_permissions=True).name

    def test_reglage_et_cohortes_completes(self):
        source.initialiser()
        frappe.db.set_single_value(DOCTYPE, "places_par_cohorte", None)
        sans_places = self.lot("Patch places : sans places", allow_self_enrollment=1, seat_count=0)
        fermee = self.lot("Patch places : fermée", allow_self_enrollment=0, seat_count=0)
        reglee = self.lot("Patch places : réglée", allow_self_enrollment=1, seat_count=8)
        completer_places_cohortes.execute()
        completer_places_cohortes.execute()
        self.assertEqual(source.charger().places_par_cohorte, 30)
        places = {n: frappe.db.get_value("LMS Batch", n, "seat_count") for n in (sans_places, fermee, reglee)}
        self.assertEqual(places, {sans_places: 30, fermee: 0, reglee: 8})

    def test_reglage_existant_conserve_et_applique(self):
        source.initialiser()
        frappe.db.set_single_value(DOCTYPE, "places_par_cohorte", 20)
        lot = self.lot("Patch places : réglage conservé", allow_self_enrollment=1, seat_count=0)
        completer_places_cohortes.execute()
        self.assertEqual((source.charger().places_par_cohorte, frappe.db.get_value("LMS Batch", lot, "seat_count")),
                         (20, 20))


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
