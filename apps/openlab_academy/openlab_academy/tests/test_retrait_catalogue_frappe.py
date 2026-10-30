"""Retrait quotidien du catalogue : un parcours limité à ses dates est dépublié le lendemain de sa fin, une seule
écriture (`published`), sans toucher leçons, inscriptions, progressions ni certificats."""
import datetime
from unittest import mock

import frappe
from lms.lms.doctype.lms_certificate.lms_certificate import get_latest_certificate

from openlab_academy import hooks
from openlab_academy.entrypoints import catalogue, install, lancement, lms
from openlab_academy.infrastructure.visibilite_frappe import SourceVisibiliteFrappe
from openlab_academy.tests import test_visibilite_frappe as vis
from openlab_academy.tests.test_blocage_frappe import suivre

COURS = "LMS Course"
ELEVE = vis.ELEVE


def publie(nom):
    return frappe.db.get_value(COURS, nom, "published")


class TestRetrait(vis.Base):
    """L : limité à [DEBUT, FIN] ; A : ordinaire. Les deux publiés, élève inscrit aux deux."""

    def setUp(self):
        super().setUp()
        for cours in (self.l, self.a):
            frappe.db.set_value(COURS, cours, "published", 1)
        for autre in frappe.get_all(COURS, {"acces_limite_cohorte": 1, "name": ["!=", self.l]}, pluck="name"):
            frappe.db.set_value(COURS, autre, "published", 0)  # le parcours de lancement du site, fenêtre propre

    def test_parcours_echu_depublie(self):
        self.jour(vis.LENDEMAIN)
        retires = lancement.retirer_parcours_echus(commit=False)
        self.assertIn(self.l, retires)
        self.assertNotIn(self.a, retires)
        self.assertEqual(publie(self.l), 0)

    def test_modification_conservee(self):
        """`published` seul change : ni date de modification, ni autre champ."""
        avant = frappe.db.get_value(COURS, self.l, ["modified", "title", "enable_certification"])
        self.jour(vis.LENDEMAIN)
        lancement.retirer_parcours_echus(commit=False)
        self.assertEqual(frappe.db.get_value(COURS, self.l, ["modified", "title", "enable_certification"]), avant)

    def test_dernier_jour_reste_publie(self):
        for jour in (vis.DEBUT, vis.DEDANS, vis.FIN):
            with self.subTest(jour=jour):
                self.jour(jour)
                self.assertNotIn(self.l, lancement.retirer_parcours_echus(commit=False))
                self.assertEqual(publie(self.l), 1)

    def test_parcours_non_limite_jamais_depublie(self):
        self.jour(datetime.date(2099, 1, 1))
        self.assertNotIn(self.a, lancement.retirer_parcours_echus(commit=False))
        self.assertEqual(publie(self.a), 1)

    def test_deja_retire_rien_a_refaire(self):
        self.jour(vis.LENDEMAIN)
        lancement.retirer_parcours_echus(commit=False)
        self.assertNotIn(self.l, lancement.retirer_parcours_echus(commit=False))

    def test_depublier_n_ecrit_que_la_publication(self):
        with mock.patch.object(frappe.db, "set_value") as ecrit:
            SourceVisibiliteFrappe().depublier(self.l)
        ecrit.assert_called_once_with(COURS, self.l, "published", 0, update_modified=False)

    def test_validation_seulement_s_il_y_a_des_parcours_retires(self):
        self.jour(vis.DEDANS)
        with mock.patch.object(frappe.db, "commit") as valide:
            lancement.retirer_parcours_echus()
        valide.assert_not_called()
        self.jour(vis.LENDEMAIN)
        with mock.patch.object(frappe.db, "commit") as valide:
            lancement.retirer_parcours_echus()
        valide.assert_called_once_with()
        self.jour(vis.LENDEMAIN)

    def test_retrait_journalise(self):
        self.jour(vis.LENDEMAIN)
        with mock.patch.object(frappe, "logger") as journal:
            lancement.retirer_parcours_echus(commit=False)
        journal.assert_called_with("openlab_academy")
        self.assertEqual(journal.return_value.info.call_args.args[1:], (self.l,))

    def certificats_de_l_apprenant(self):
        """Ce que le LMS retient du certificat de l'apprenant pour ce parcours."""
        derniere = get_latest_certificate(ELEVE, self.l)
        return [derniere["name"]] if derniere else []

    def test_progression_et_certificat_conserves(self):
        lecon = self.lecon_l
        chapitre = frappe.db.get_value("Course Lesson", lecon, "chapter")
        progression = frappe.get_doc({"doctype": "LMS Course Progress", "course": self.l, "member": ELEVE,
                                      "lesson": lecon, "chapter": chapitre, "status": "Complete"}
                                     ).insert(ignore_permissions=True).name
        frappe.db.set_value("LMS Enrollment", {"course": self.l, "member": ELEVE}, "progress", 100)
        certificat = frappe.get_doc({
            "doctype": "LMS Certificate", "member": ELEVE, "course": self.l, "issue_date": frappe.utils.nowdate(),
            "template": lms.lms_certificate.get_default_certificate_template()}).insert(ignore_permissions=True).name
        inscription = frappe.db.get_value("LMS Enrollment", {"course": self.l, "member": ELEVE})
        lecons = frappe.get_all("Course Lesson", {"course": self.l}, pluck="name")
        self.assertEqual(self.certificats_de_l_apprenant(), [certificat])  # témoin avant le retrait
        self.jour(vis.LENDEMAIN)
        self.assertIn(self.l, lancement.retirer_parcours_echus(commit=False))
        self.assertEqual(publie(self.l), 0)
        self.assertTrue(frappe.db.exists("LMS Course Progress", progression))
        self.assertTrue(frappe.db.exists("LMS Certificate", certificat))
        self.assertTrue(frappe.db.exists("LMS Enrollment", inscription))
        self.assertEqual(frappe.get_all("Course Lesson", {"course": self.l}, pluck="name"), lecons)
        self.assertEqual(self.certificats_de_l_apprenant(), [certificat])

    def test_republication_puis_retrait(self):
        """La migration republie le parcours (seed) puis le retrait passe en dernier : il reste dépublié."""
        self.jour(vis.LENDEMAIN)
        frappe.db.set_value(COURS, self.l, "published", 0)

        def republier(*args, **kwargs):
            frappe.db.set_value(COURS, self.l, "published", 1)
            return {}

        with mock.patch.object(install.seed, "run", side_effect=republier) as semer:
            install.after_migrate(commit=False)
        semer.assert_called_once()
        self.assertEqual(publie(self.l), 0)

    def test_parcours_echu_absent_du_catalogue(self):
        self.jour(vis.DEDANS)
        frappe.set_user(ELEVE)
        self.assertIn(self.l, [c["name"] for c in catalogue.get_courses({})])
        frappe.set_user("Administrator")
        self.jour(vis.LENDEMAIN)
        lancement.retirer_parcours_echus(commit=False)
        for utilisateur in (ELEVE, "Guest"):
            frappe.set_user(utilisateur)
            lms.vider_cache()
            with self.subTest(utilisateur=utilisateur):
                self.assertNotIn(self.l, [c["name"] for c in catalogue.get_courses({})])

    def test_tache_planifiee_declaree(self):
        self.assertEqual(hooks.scheduler_events["cron"]["5 0 * * *"],
                         ["openlab_academy.entrypoints.lancement.retirer_parcours_echus"])
        self.assertIn("openlab_academy.entrypoints.lancement.retirer_parcours_echus",
                      frappe.get_hooks("scheduler_events")["cron"]["5 0 * * *"])

    def test_tache_non_exposee_a_l_api(self):
        with self.assertRaises(frappe.PermissionError):
            frappe.is_whitelisted(lancement.retirer_parcours_echus)
