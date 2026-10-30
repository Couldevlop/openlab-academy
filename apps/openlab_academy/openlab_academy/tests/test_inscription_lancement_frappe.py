"""Inscriptions et phase de lancement sur le banc : refus hors fenêtre (parcours fermé) ou pendant le lancement
(parcours caché), rattachement automatique à la cohorte-fenêtre, agents jamais refusés."""
import datetime
from unittest import mock

import frappe
from frappe.tests.utils import FrappeTestCase

from openlab_academy import hooks
from openlab_academy.domain.cohorte import Cohorte
from openlab_academy.domain.fenetre import un_mois_apres
from openlab_academy.domain.lancement import PhaseLancement
from openlab_academy.domain.parcours import Bloc
from openlab_academy.domain.reglages import Reglages
from openlab_academy.entrypoints import lancement, lms
from openlab_academy.infrastructure import reglages_source_frappe
from openlab_academy.infrastructure.depot_cohortes_frappe import DepotCohortesFrappe
from openlab_academy.infrastructure.depot_frappe import DepotFrappe
from openlab_academy.tests.fabriques import parcours
from openlab_academy.tests.test_blocage_frappe import utilisateur
from openlab_academy.tests.test_exercices_frappe import module
from openlab_academy.tests.test_paiement_api_frappe import agent

ELEVE = "eleve.lancement@example.ci"
TITRE = "Parcours fenêtre inscription"
DEBUT = datetime.date(2027, 3, 10)
FIN = un_mois_apres(DEBUT)
DEDANS = datetime.date(2027, 3, 20)
AVANT = DEBUT - datetime.timedelta(days=1)
APRES = FIN + datetime.timedelta(days=1)
FERMEES = "Les inscriptions à ce parcours sont fermées."
CACHE = "Ce parcours n'est pas disponible pour le moment."
INSCRIPTION = "LMS Enrollment"
LOT_INSCRIPTION = "LMS Batch Enrollment"
DOSSIER = "Dossier Paiement OpenLab"
AGENTS = ("System Manager", "Moderator", "Course Creator", "Batch Evaluator", "Intendant OpenLab")


def creer(titre, limite=False):
    return DepotFrappe(commit=False, reglages=Reglages()).creer(
        parcours(title=titre, questions_par_quiz=5, blocs=(Bloc("B1", (module(),)),), gratuit=True,
                 acces_limite_a_la_cohorte=limite))


class Base(FrappeTestCase):
    """F : parcours gratuit limité à sa cohorte-fenêtre [DEBUT, FIN] ; O : parcours ordinaire. Phase décochée."""

    def setUp(self):
        lms.vider_cache()
        self.phase = mock.patch.object(reglages_source_frappe, "phase_lancement",
                                       return_value=PhaseLancement(False)).start()
        self.addCleanup(mock.patch.stopall)
        self.langue = getattr(frappe.local, "lang", None)
        frappe.local.lang = "fr"
        self.f = creer(TITRE, limite=True)
        self.o = creer("Parcours ordinaire inscription")
        self.lot = DepotCohortesFrappe().creer(Cohorte.fenetre(parcours(title=TITRE), DEBUT, Reglages()))
        utilisateur(ELEVE)
        self.jour(DEDANS)

    def tearDown(self):
        frappe.set_user("Administrator")
        frappe.local.lang = self.langue
        lms.vider_cache()
        frappe.db.rollback()

    def jour(self, jour):
        lms.vider_cache()
        mock.patch.object(lms, "aujourd_hui", return_value=jour).start()

    def lancement(self, *visibles):
        """Phase de lancement active : seuls `visibles` restent affichés."""
        lms.vider_cache()
        self.phase.return_value = PhaseLancement(True, frozenset(visibles))

    def s_inscrire(self, cours, membre=ELEVE):
        """Comme « Enroll Now » (frappe.client.insert) : en session du membre, droits vérifiés."""
        frappe.set_user(membre)
        try:
            return frappe.get_doc({"doctype": INSCRIPTION, "course": cours, "member": membre}).insert()
        finally:
            frappe.set_user("Administrator")

    def s_inscrire_cohorte(self, membre=ELEVE):
        frappe.set_user(membre)
        try:
            return frappe.get_doc({"doctype": LOT_INSCRIPTION, "batch": self.lot, "member": membre}).insert()
        finally:
            frappe.set_user("Administrator")

    def inscriptions(self, cours, membre=ELEVE):
        return frappe.db.count(INSCRIPTION, {"course": cours, "member": membre})

    def rattachements(self, membre=ELEVE):
        return frappe.db.count(LOT_INSCRIPTION, {"batch": self.lot, "member": membre})

    def oublier(self, membre=ELEVE):
        frappe.db.delete(LOT_INSCRIPTION, {"member": membre})
        frappe.db.delete(INSCRIPTION, {"member": membre})


class TestRefus(Base):
    def test_refus_hors_fenetre(self):
        for jour in (AVANT, APRES):
            self.jour(jour)
            with self.assertRaisesRegex(frappe.ValidationError, FERMEES):
                self.s_inscrire(self.f)
            with self.assertRaisesRegex(frappe.ValidationError, FERMEES):
                self.s_inscrire_cohorte()
        self.assertEqual(self.inscriptions(self.f), 0)
        self.assertEqual(self.rattachements(), 0)

    def test_inscription_ouverte_acceptee(self):
        for jour in (DEBUT, DEDANS, FIN):
            self.jour(jour)
            self.s_inscrire(self.f)
            self.assertEqual(self.inscriptions(self.f), 1)
            self.oublier()
        self.s_inscrire(self.f)
        self.assertFalse(frappe.db.exists(DOSSIER, {"apprenant": ELEVE}))
        self.assertEqual(frappe.db.get_value("LMS Course", self.f, "disable_self_learning"), 0)

    def test_inscription_cohorte_ouverte_acceptee(self):
        self.s_inscrire_cohorte()
        self.assertEqual(self.inscriptions(self.f), 1)
        self.assertEqual(self.rattachements(), 1)

    def test_inscription_parcours_cache_refusee(self):
        self.lancement()
        for cours in (self.o, self.f):
            with self.assertRaisesRegex(frappe.ValidationError, CACHE):
                self.s_inscrire(cours)
            self.assertEqual(self.inscriptions(cours), 0)
        with self.assertRaisesRegex(frappe.ValidationError, CACHE):
            self.s_inscrire_cohorte()
        self.assertEqual(self.rattachements(), 0)

    def test_parcours_visible_pendant_le_lancement_inscrit(self):
        self.lancement(self.f)
        self.s_inscrire(self.f)
        with self.assertRaisesRegex(frappe.ValidationError, CACHE):
            self.s_inscrire(self.o)

    def test_cohorte_refusee_seulement_si_tous_ses_parcours_le_sont(self):
        lot = frappe.get_doc("LMS Batch", self.lot)
        lot.append("courses", {"course": self.o})
        lot.save(ignore_permissions=True)
        self.lancement(self.f)
        frappe.clear_messages()
        self.s_inscrire_cohorte()  # F reste visible : acceptée, sans message de refus laissé
        self.assertEqual(frappe.local.message_log, [])
        self.oublier()
        self.jour(APRES)
        self.lancement(self.f)
        frappe.clear_messages()
        with self.assertRaises(frappe.ValidationError):  # F fermé, O caché : tous refusés, un seul message
            self.s_inscrire_cohorte()
        self.assertEqual(len(frappe.local.message_log), 1)

    def test_drapeau_de_cohorte_pose_par_le_client_ne_contourne_pas_le_refus(self):
        self.jour(APRES)
        for flags in ({"via_batch_enrollment": True}, {"via_batch_enrollment": True, "ignore_permissions": True}):
            frappe.set_user(ELEVE)
            try:
                with self.assertRaises((frappe.ValidationError, frappe.PermissionError)):
                    frappe.client.insert({"doctype": INSCRIPTION, "course": self.f, "member": ELEVE,
                                          "enrollment_from_batch": self.lot, "flags": flags})
            finally:
                frappe.set_user("Administrator")
        self.assertEqual(self.inscriptions(self.f), 0)

    def test_drapeau_pose_cote_serveur_sans_inscription_de_cohorte_ne_contourne_pas_le_refus(self):
        self.jour(APRES)
        doc = frappe.get_doc({"doctype": INSCRIPTION, "course": self.f, "member": ELEVE,
                              "enrollment_from_batch": self.lot})
        doc.flags.via_batch_enrollment = True
        frappe.set_user(ELEVE)
        try:
            with self.assertRaisesRegex(frappe.ValidationError, FERMEES):
                doc.insert()
        finally:
            frappe.set_user("Administrator")
        self.assertEqual(self.inscriptions(self.f), 0)

    def test_visiteur_refuse(self):
        self.jour(APRES)
        frappe.set_user("Guest")
        try:
            with self.assertRaises((frappe.ValidationError, frappe.PermissionError)):
                frappe.client.insert({"doctype": INSCRIPTION, "course": self.f, "member": "Guest"})
            with self.assertRaises((frappe.ValidationError, frappe.PermissionError)):
                frappe.client.insert({"doctype": LOT_INSCRIPTION, "batch": self.lot, "member": "Guest"})
        finally:
            frappe.set_user("Administrator")
        self.assertEqual(frappe.db.count(INSCRIPTION, {"member": "Guest"}), 0)

    def test_agent_inscrit_hors_fenetre(self):
        for i, role in enumerate(AGENTS):
            membre = agent(f"agent{i}.lancement@example.ci", role)
            for jour in (AVANT, APRES):
                self.jour(jour)
                self.lancement()
                lms.refuser_inscription(membre, self.f)  # ne lève pas
                frappe.get_doc({"doctype": INSCRIPTION, "course": self.f, "member": membre}).insert(
                    ignore_permissions=True)
                self.assertEqual(self.inscriptions(self.f, membre), 1)
                self.assertEqual(self.rattachements(membre), 0)
                self.oublier(membre)

    def test_phase_decochee_inscription_permise(self):
        self.lancement()
        with self.assertRaises(frappe.ValidationError):
            self.s_inscrire(self.o)
        lms.vider_cache()
        self.phase.return_value = PhaseLancement(False)
        self.s_inscrire(self.o)
        self.assertEqual(self.inscriptions(self.o), 1)

    def test_message_en_anglais(self):
        frappe.local.lang = "en"
        self.jour(APRES)
        with self.assertRaisesRegex(frappe.ValidationError, "Enrollment for this course is closed."):
            self.s_inscrire(self.f)
        self.jour(DEDANS)
        self.lancement()
        with self.assertRaisesRegex(frappe.ValidationError, "This course is not available at the moment."):
            self.s_inscrire(self.o)

    def test_refuser_inscription_sans_effet_pour_un_parcours_ouvert(self):
        self.assertIsNone(lms.refuser_inscription(ELEVE, self.o))
        self.assertIsNone(lms.refuser_inscription(ELEVE, self.f))


class TestRattachement(Base):
    def test_inscription_directe_rattache_a_la_cohorte(self):
        self.s_inscrire(self.f)
        self.assertEqual(self.rattachements(), 1)
        self.assertEqual(self.inscriptions(self.f), 1)

    def test_rejouable_sans_doublon_ni_boucle(self):
        inscription = self.s_inscrire(self.f)
        lancement.rejoindre_cohorte(inscription)
        lancement.rejoindre_cohorte(inscription)
        self.assertEqual(self.rattachements(), 1)
        self.assertEqual(self.inscriptions(self.f), 1)

    def test_inscription_issue_de_la_cohorte_sans_effet(self):
        self.s_inscrire_cohorte()
        self.assertEqual(self.rattachements(), 1)
        self.assertEqual(self.inscriptions(self.f), 1)

    def test_rattache_a_la_cohorte_fenetre_et_non_a_une_cohorte_plus_tardive(self):
        debut = DEBUT + datetime.timedelta(days=60)
        pilote = DepotCohortesFrappe().creer(
            Cohorte.pilote(parcours(title=TITRE), debut, Reglages().rythme("standard"), Reglages()))
        self.assertEqual(DepotCohortesFrappe().fenetre_de(self.f), self.lot)
        self.jour(DEDANS)  # la visibilité suit la cohorte-fenêtre, pas le pilote plus tardif
        lancement.rejoindre_cohorte(frappe.get_doc({"doctype": INSCRIPTION, "course": self.f, "member": ELEVE}))
        self.assertEqual(self.rattachements(), 1)
        self.assertFalse(frappe.db.exists(LOT_INSCRIPTION, {"batch": pilote, "member": ELEVE}))

    def test_parcours_ordinaire_non_rattache(self):
        self.s_inscrire(self.o)
        self.assertEqual(frappe.db.count(LOT_INSCRIPTION, {"member": ELEVE}), 0)

    def test_agent_non_rattache(self):
        membre = agent("agent.rattachement@example.ci", "Course Creator")
        frappe.get_doc({"doctype": INSCRIPTION, "course": self.f, "member": membre}).insert(ignore_permissions=True)
        self.assertEqual(self.rattachements(membre), 0)

    def test_parcours_limite_sans_cohorte_sans_effet(self):
        seul = creer("Parcours limité sans cohorte", limite=True)
        doc = frappe.get_doc({"doctype": INSCRIPTION, "course": seul, "member": ELEVE})
        lancement.rejoindre_cohorte(doc)  # fenêtre introuvable : ne lève pas
        self.assertEqual(frappe.db.count(LOT_INSCRIPTION, {"member": ELEVE}), 0)

    def test_inscription_par_un_administrateur_rattache_aussi(self):
        frappe.get_doc({"doctype": INSCRIPTION, "course": self.f, "member": ELEVE}).insert(ignore_permissions=True)
        self.assertEqual(self.rattachements(), 1)

    def test_hooks_declares(self):
        self.assertEqual(hooks.doc_events[INSCRIPTION], {
            "before_insert": "openlab_academy.entrypoints.paiement.avant_inscription_parcours",
            "after_insert": "openlab_academy.entrypoints.lancement.rejoindre_cohorte"})
