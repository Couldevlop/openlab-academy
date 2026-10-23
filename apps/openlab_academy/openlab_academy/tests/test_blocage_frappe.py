"""Blocage par parcours sur le banc : leçon, exercices, listes et pages d'un parcours en retard refusés ; les autres
parcours de l'apprenant restent ouverts ; rôles exemptés jamais bloqués."""
import datetime
import json
from unittest import mock

import frappe
import frappe.client
import frappe.utils.response
from frappe.tests.utils import FrappeTestCase
from lms.lms import utils as lms_utils
from werkzeug.exceptions import HTTPException
from werkzeug.test import EnvironBuilder
from werkzeug.wrappers import Request

from openlab_academy import hooks
from openlab_academy.application.ports_paiement import NouveauDossier
from openlab_academy.domain.echeancier import Echeance, Mode, Tarif
from openlab_academy.domain.parcours import Bloc
from openlab_academy.domain.reglages import Reglages
from openlab_academy.entrypoints import http, lms
from openlab_academy.infrastructure.depot_dossiers_frappe import DepotDossiersFrappe
from openlab_academy.infrastructure.depot_frappe import DepotFrappe
from openlab_academy.tests.fabriques import parcours
from openlab_academy.tests.test_exercices_frappe import module
from openlab_academy.tests.test_paiement_donnees_frappe import tarif
from openlab_academy.tests.test_paiement_inscription_frappe import cohorte, inscrire

ELEVE = "eleve.blocage@example.ci"
AUTRE = "autre.blocage@example.ci"
CORRECTEUR = "correcteur.blocage@example.ci"
DOSSIER = "Dossier Paiement OpenLab"
HTML = {"Accept": "text/html,application/xhtml+xml"}


def utilisateur(email, *roles):
    if not frappe.db.exists("User", email):
        frappe.get_doc({"doctype": "User", "email": email, "first_name": "Aya", "send_welcome_email": 0,
                        "roles": [{"role": r} for r in ("LMS Student", *roles)]}).insert(ignore_permissions=True)
    return email


def suivre(cours, membre):
    if not frappe.db.exists("LMS Enrollment", {"course": cours, "member": membre}):
        frappe.get_doc({"doctype": "LMS Enrollment", "course": cours, "member": membre,
                        "member_type": "Student"}).insert(ignore_permissions=True)


def requete(chemin, methode="GET", entetes=None):
    return Request(EnvironBuilder(path=chemin, method=methode, headers=HTML if entetes is None else entetes).get_environ())


class Base(FrappeTestCase):
    """A : inscrit, frais impayés (bloqué) ; B : inscrit, dispensé (ouvert)."""

    def setUp(self):
        self.requete_initiale = getattr(frappe.local, "request", None)
        lms.vider_cache()
        depot = DepotFrappe(commit=False, reglages=Reglages())
        self.a = depot.creer(parcours(title="Parcours bloqué test", questions_par_quiz=5,
                                      blocs=(Bloc("B1", (module(),)),)))
        self.b = depot.creer(parcours(title="Parcours ouvert test", questions_par_quiz=5,
                                      blocs=(Bloc("B1", (module(),)),)))
        utilisateur(ELEVE)
        self.lots = {}
        for c in (self.a, self.b):
            tarif(c).insert(ignore_permissions=True)
            self.lots[c] = cohorte(c)
            inscrire(self.lots[c], ELEVE)
            suivre(c, ELEVE)
        frappe.db.set_value(DOSSIER, {"apprenant": ELEVE, "cours": self.b}, "dispense", 1)
        self.lecon_a = frappe.db.get_value("Course Lesson", {"course": self.a, "title": ["like", "01 ·%"]})
        self.lecon_b = frappe.db.get_value("Course Lesson", {"course": self.b, "title": ["like", "01 ·%"]})
        self.quiz_a = frappe.db.get_value("LMS Quiz", {"course": self.a})
        self.quiz_b = frappe.db.get_value("LMS Quiz", {"course": self.b})
        self.devoir_a = frappe.db.get_value("LMS Assignment", {"course": self.a})
        self.devoir_b = frappe.db.get_value("LMS Assignment", {"course": self.b})

    def tearDown(self):
        frappe.set_user("Administrator")
        frappe.local.response.pop("redirection", None)
        frappe.local.request = self.requete_initiale
        lms.vider_cache()
        frappe.db.rollback()

    def placer(self, doctype, nom, lecon):
        frappe.get_doc({"doctype": "LMS Lesson Assessment", "parent": lecon, "parenttype": "Course Lesson",
                        "parentfield": "assessments", "assessment_type": doctype, "assessment_name": nom}).db_insert()


class TestLecon(Base):
    def test_lecon_d_un_parcours_bloque_refusee_par_l_api(self):
        """Point de vigilance 5 : un apprenant bloqué qui appelle get_lesson sans passer par une page."""
        frappe.set_user(ELEVE)
        with self.assertRaises(lms.ParcoursBloque) as e:
            lms.get_lesson(self.a, 1, 1)
        self.assertEqual(str(e.exception), "Paiement requis")
        self.assertEqual(e.exception.redirection, f"/espace/paiement/{self.a}")
        self.assertEqual(frappe.local.response["redirection"], f"/espace/paiement/{self.a}")
        self.assertTrue(issubclass(lms.ParcoursBloque, frappe.ValidationError))
        frappe.set_user("Administrator")
        self.assertFalse(frappe.db.exists("Ouverture Lecon OpenLab", {"apprenant": ELEVE, "lecon": self.lecon_a}))

    def test_refus_avant_toute_lecture(self):
        frappe.set_user(ELEVE)
        with mock.patch.object(lms_utils, "get_lesson") as lecture, self.assertRaises(lms.ParcoursBloque):
            lms.get_lesson(self.a, 1, 1)
        lecture.assert_not_called()

    def test_parcours_a_jour_ouvert_pendant_qu_un_autre_est_bloque(self):
        frappe.set_user(ELEVE)
        self.assertEqual(lms.get_lesson(self.b, 1, 1)["name"], self.lecon_b)

    def test_frais_payes_debloquent(self):
        nom = frappe.db.get_value(DOSSIER, {"apprenant": ELEVE, "cours": self.a})
        DepotDossiersFrappe().creer_paiement(nom, 10000, "virement", "VIR-BLOC-1", "confirme")
        frappe.set_user(ELEVE)
        self.assertEqual(lms.get_lesson(self.a, 1, 1)["name"], self.lecon_a)

    def test_delai_accorde_debloque(self):
        nom = frappe.db.get_value(DOSSIER, {"apprenant": ELEVE, "cours": self.a})
        DepotDossiersFrappe().fixer_delai(nom, lms.aujourd_hui() + datetime.timedelta(days=3))
        frappe.set_user(ELEVE)
        self.assertEqual(lms.get_lesson(self.a, 1, 1)["name"], self.lecon_a)

    def test_sans_dossier_jamais_bloque(self):
        utilisateur(AUTRE)
        suivre(self.a, AUTRE)
        frappe.set_user(AUTRE)
        self.assertEqual(lms.get_lesson(self.a, 1, 1)["name"], self.lecon_a)

    def test_correcteur_inscrit_en_retard_non_bloque(self):
        utilisateur(CORRECTEUR, "Batch Evaluator")
        suivre(self.a, CORRECTEUR)
        hier = frappe.utils.getdate(frappe.utils.nowdate()) - datetime.timedelta(days=1)
        DepotDossiersFrappe().creer(NouveauDossier(
            CORRECTEUR, self.a, self.lots[self.a], Mode.UNE_FOIS, Tarif(10000, 100000, 110000, 120000), hier,
            (Echeance(hier, 10000, "Frais"), Echeance(hier, 100000, "Solde"))))
        self.assertIn("Batch Evaluator", lms.ROLES_NON_BLOQUES)
        frappe.set_user(CORRECTEUR)
        self.assertEqual(lms.get_lesson(self.a, 1, 1)["name"], self.lecon_a)

    def test_depot_en_erreur_jamais_bloquant(self):
        """Fail-safe : une erreur de calcul est journalisée (dossier et parcours seulement) et ne bloque pas."""
        frappe.set_user(ELEVE)
        with mock.patch.object(lms, "parcours_bloque", side_effect=RuntimeError("panne")), \
                mock.patch.object(frappe, "log_error") as journal:
            self.assertFalse(lms.bloque_pour(ELEVE, self.a))
            self.assertEqual(lms.get_lesson(self.a, 1, 1)["name"], self.lecon_a)
        nom = frappe.db.get_value(DOSSIER, {"apprenant": ELEVE, "cours": self.a})
        message = journal.call_args.kwargs["message"]
        self.assertIn(nom, message)
        self.assertIn(self.a, message)
        self.assertNotIn(ELEVE, message + journal.call_args.kwargs["title"])

    def test_liste_en_erreur_sans_filtre(self):
        with mock.patch.object(lms, "cours_bloques", side_effect=RuntimeError("panne")), \
                mock.patch.object(frappe, "log_error") as journal:
            self.assertEqual(lms.conditions_lecons(ELEVE), "")
        self.assertNotIn(ELEVE, journal.call_args.kwargs["message"])

    def test_cohorte_supprimee_toleree(self):
        frappe.db.set_value(DOSSIER, {"apprenant": ELEVE, "cours": self.a}, "cohorte", "cohorte-disparue")
        self.assertTrue(lms.bloque_pour(ELEVE, self.a))

    def test_resultat_mis_en_cache_pour_la_requete(self):
        with mock.patch.object(lms, "parcours_bloque", return_value=True) as calcul:
            self.assertTrue(lms.bloque_pour(ELEVE, self.a))
            self.assertTrue(lms.bloque_pour(ELEVE, self.a))
        calcul.assert_called_once()
        self.assertEqual(lms._cache(), {(ELEVE, self.a, lms.aujourd_hui()): True})

    def test_cache_cree_a_la_premiere_requete(self):
        delattr(frappe.local, lms.CACHE)
        self.assertEqual(lms._cache(), {})
        self.assertIs(lms._cache(), lms._cache())

    def test_journal_sans_dossier_lisible(self):
        with mock.patch.object(frappe.db, "get_value", side_effect=RuntimeError("panne")), \
                mock.patch.object(frappe, "log_error") as journal:
            lms._journaliser(ELEVE, self.a)
        self.assertEqual(journal.call_args.kwargs["message"], f"dossier inconnu, parcours {self.a}")

    def test_invite_jamais_bloque(self):
        frappe.set_user("Guest")
        lms.get_lesson(self.a, 1, 1)  # aucune exception : l'aperçu public reste régi par le LMS


class TestReponseJson(Base):
    def test_exception_serialisee_avec_son_type_et_la_redirection(self):
        """Le navigateur reçoit exc_type == "ParcoursBloque" et l'URL de paiement (frappe.utils.response)."""
        frappe.set_user(ELEVE)
        frappe.local.request = requete("/api/method/lms.lms.utils.get_lesson", entetes={"Accept": "application/json"})
        with self.assertRaises(lms.ParcoursBloque):
            try:
                lms.get_lesson(self.a, 1, 1)
            except lms.ParcoursBloque:  # report_error lit l'exception en cours (sys.exc_info)
                reponse = frappe.utils.response.report_error(lms.ParcoursBloque.http_status_code)
                raise
        corps = json.loads(reponse.get_data(as_text=True))
        self.assertEqual(corps["exc_type"], "ParcoursBloque")
        self.assertEqual(corps["redirection"], f"/espace/paiement/{self.a}")
        self.assertEqual(reponse.status_code, 417)


class TestEvaluations(Base):
    def test_quiz_et_reponses_refuses(self):
        frappe.set_user(ELEVE)
        with self.assertRaises(lms.ParcoursBloque):
            lms.get_quiz_with_questions(self.quiz_a)
        question = frappe.db.get_value("LMS Quiz Question", {"parent": self.quiz_a}, "question")
        with self.assertRaises(lms.ParcoursBloque):
            lms.check_answer(self.quiz_a, question, "Choices", "[]")

    def test_quiz_d_un_parcours_ouvert_servi(self):
        frappe.set_user(ELEVE)
        self.assertEqual(lms.get_quiz_with_questions(self.quiz_b)["quiz"]["name"], self.quiz_b)
        question = frappe.db.get_value("LMS Quiz Question", {"parent": self.quiz_b}, "question")
        with mock.patch("lms.lms.doctype.lms_quiz.lms_quiz.check_answer", return_value=[1]) as verifier:
            self.assertEqual(lms.check_answer(self.quiz_b, question, "Choices", "[]"), [1])
        verifier.assert_called_once_with(self.quiz_b, question, "Choices", "[]")

    def test_documents_refuses_par_les_permissions(self):
        """frappe.client.get, /api/resource et get_assignment passent par has_permission : notre hook est consulté
        avant celui du LMS (qui accorderait l'accès à un inscrit)."""
        frappe.set_user(ELEVE)
        for doctype, nom in (("LMS Quiz", self.quiz_a), ("LMS Assignment", self.devoir_a)):
            with self.subTest(doctype=doctype):
                self.assertFalse(frappe.has_permission(doctype, "read", doc=nom))
        for doctype, nom in (("LMS Quiz", self.quiz_b), ("LMS Assignment", self.devoir_b)):
            with self.subTest(doctype=doctype):
                self.assertTrue(frappe.has_permission(doctype, "read", doc=nom))
        with self.assertRaises(frappe.PermissionError):
            lms_utils.get_assignment(self.devoir_a)
        self.assertEqual(lms_utils.get_assignment(self.devoir_b)["name"], self.devoir_b)
        with self.assertRaises(frappe.PermissionError):
            frappe.client.get("LMS Assignment", self.devoir_a)

    def test_lecon_refusee_par_le_hook(self):
        """Les apprenants n'ont pas de DocPerm de lecture sur Course Lesson ; le hook refuse quand même."""
        self.assertFalse(lms.lecture_permise(frappe.get_doc("Course Lesson", self.lecon_a), "read", ELEVE))

    def test_chapitre_scorm_refuse(self):
        chapitre = frappe.db.get_value("Course Chapter", {"course": self.a})
        frappe.set_user(ELEVE)
        self.assertFalse(frappe.has_permission("Course Chapter", "read", doc=chapitre))
        self.assertTrue(frappe.has_permission("Course Chapter", "read",
                                              doc=frappe.db.get_value("Course Chapter", {"course": self.b})))

    def test_evaluation_placee_dans_une_lecon_du_parcours_bloque(self):
        exercice = frappe.get_doc({"doctype": "LMS Programming Exercise", "title": "Exo blocage",
                                   "language": "Python", "problem_statement": "Secret",
                                   "test_cases": [{"expected_output": "1"}]}).insert(
            ignore_permissions=True)
        self.placer("LMS Programming Exercise", exercice.name, self.lecon_a)
        self.assertEqual(lms.contenus.cours_de_l_evaluation("LMS Programming Exercise", exercice.name), {self.a})
        frappe.set_user(ELEVE)
        self.assertFalse(lms.lecture_permise(exercice, "read", ELEVE))
        self.assertNotIn(exercice.name, frappe.get_list("LMS Programming Exercise", pluck="name"))

    def test_quiz_partage_avec_un_parcours_ouvert_servi(self):
        self.placer("LMS Quiz", self.quiz_a, self.lecon_b)
        frappe.set_user(ELEVE)
        self.assertEqual(lms.get_quiz_with_questions(self.quiz_a)["quiz"]["name"], self.quiz_a)
        self.assertIsNone(lms.lecture_permise(frappe.get_doc("LMS Quiz", self.quiz_a), "read", ELEVE))

    def test_calcul_des_evaluations_en_erreur_jamais_bloquant(self):
        with mock.patch.object(lms.contenus, "cours_de_l_evaluation", side_effect=RuntimeError("panne")), \
                mock.patch.object(frappe, "log_error"):
            self.assertIsNone(lms.lecture_permise(frappe.get_doc("LMS Quiz", self.quiz_a), "read", ELEVE))

    def test_evaluation_hors_parcours_jamais_bloquee(self):
        exercice = frappe.get_doc({"doctype": "LMS Programming Exercise", "title": "Exo libre", "language": "Python",
                                   "problem_statement": "Libre", "test_cases": [{"expected_output": "1"}]}).insert(
            ignore_permissions=True)
        self.assertEqual(lms.contenus.cours_de_l_evaluation("LMS Programming Exercise", exercice.name), set())
        self.assertIsNone(lms.lecture_permise(exercice, "read", ELEVE))

    def test_exemptes_servis_sans_calcul(self):
        with mock.patch.object(lms.contenus, "cours_de_l_evaluation") as calcul:
            self.assertEqual(lms.get_quiz_with_questions(self.quiz_a)["quiz"]["name"], self.quiz_a)
        calcul.assert_not_called()

    def test_ecriture_et_rôles_exemptes_sans_avis(self):
        doc = frappe.get_doc("Course Lesson", self.lecon_a)
        self.assertIsNone(lms.lecture_permise(doc, "write", ELEVE))
        self.assertIsNone(lms.lecture_permise(doc, "read", "Administrator"))
        self.assertIsNone(lms.lecture_permise(doc, "read", "Guest"))
        self.assertIsNone(lms.lecture_permise(frappe.get_doc("Course Lesson", self.lecon_b), "read", ELEVE))


class TestEnvois(Base):
    """Ce qu'un apprenant bloqué envoie pour le parcours bloqué est refusé aussi."""

    def soumettre_quiz(self, quiz, cours):
        return frappe.get_doc({"doctype": "LMS Quiz Submission", "quiz": quiz, "member": ELEVE, "course": cours,
                               "score": 5, "score_out_of": 5, "percentage": 100,
                               "passing_percentage": 100}).insert(ignore_permissions=True)

    def test_soumission_de_quiz_refusee(self):
        frappe.set_user(ELEVE)
        with self.assertRaises(lms.ParcoursBloque):
            self.soumettre_quiz(self.quiz_a, self.a)

    def test_soumission_de_devoir_refusee(self):
        frappe.set_user(ELEVE)
        for devoir in frappe.get_all("LMS Assignment", {"course": self.a}, pluck="name"):
            with self.subTest(devoir=devoir), self.assertRaises(lms.ParcoursBloque):
                frappe.get_doc({"doctype": "LMS Assignment Submission", "assignment": devoir, "member": ELEVE,
                                "answer": "https://github.com/aya/livrable"}).insert(ignore_permissions=True)

    def test_soumission_du_parcours_ouvert_suit_le_verrou_habituel(self):
        frappe.set_user(ELEVE)
        with self.assertRaisesRegex(frappe.ValidationError, "ouvrez d'abord la leçon"):
            self.soumettre_quiz(self.quiz_b, self.b)

    def test_progression_refusee(self):
        frappe.set_user(ELEVE)
        with mock.patch.object(lms.lms_api, "mark_lesson_progress") as marque, self.assertRaises(lms.ParcoursBloque):
            lms.mark_lesson_progress(self.a, 1, 1)
        marque.assert_not_called()
        with mock.patch.object(lms.course_lesson, "save_progress") as sauve, self.assertRaises(lms.ParcoursBloque):
            lms.save_progress(self.lecon_a, self.b)  # le parcours retenu est celui de la leçon
        sauve.assert_not_called()

    def test_progression_du_parcours_ouvert_transmise(self):
        frappe.set_user(ELEVE)
        with mock.patch.object(lms.lms_api, "mark_lesson_progress", return_value=None) as marque:
            lms.mark_lesson_progress(self.b, 1, 1)
        marque.assert_called_once_with(self.b, 1, 1)
        with mock.patch.object(lms.course_lesson, "save_progress", return_value=7) as sauve:
            self.assertEqual(lms.save_progress(self.lecon_b, None, {"is_complete": 1}), 7)
        sauve.assert_called_once_with(self.lecon_b, None, {"is_complete": 1})

    def achever(self, cours):
        frappe.db.set_value("LMS Enrollment", {"course": cours, "member": ELEVE}, "progress", 100)

    def certificat(self, cours):
        return frappe.get_doc({"doctype": "LMS Certificate", "member": ELEVE, "course": cours,
                               "issue_date": frappe.utils.nowdate(),
                               "template": lms.lms_certificate.get_default_certificate_template()})

    def test_certificat_refuse_meme_contenu_acheve(self):
        """Contenu fini tôt, puis paiements arrêtés : aucun certificat par l'API."""
        self.achever(self.a)
        frappe.set_user(ELEVE)
        with mock.patch.object(lms.lms_certificate, "create_certificate") as cree,                 self.assertRaises(lms.ParcoursBloque):
            lms.create_certificate(self.a)
        cree.assert_not_called()
        self.assertEqual(frappe.local.response["redirection"], f"/espace/paiement/{self.a}")
        with self.assertRaises(lms.ParcoursBloque):
            self.certificat(self.a).insert(ignore_permissions=True)
        frappe.set_user("Administrator")
        self.assertFalse(frappe.db.exists("LMS Certificate", {"member": ELEVE, "course": self.a}))

    def test_certificat_du_parcours_ouvert_transmis(self):
        self.achever(self.b)
        frappe.set_user(ELEVE)
        with mock.patch.object(lms.lms_certificate, "create_certificate", return_value="CERT") as cree:
            self.assertEqual(lms.create_certificate(self.b), "CERT")
        cree.assert_called_once_with(self.b)
        self.certificat(self.b).insert(ignore_permissions=True)

    def test_certificat_delivre_par_l_equipe_a_un_apprenant_bloque(self):
        """Décision d'un membre de l'équipe (évaluateur, administrateur) : jamais refusée par le paiement."""
        self.achever(self.a)
        self.certificat(self.a).insert(ignore_permissions=True)
        self.assertTrue(frappe.db.exists("LMS Certificate", {"member": ELEVE, "course": self.a}))

    def test_soumission_en_erreur_jamais_bloquante(self):
        with mock.patch.object(lms, "parcours_bloque", side_effect=RuntimeError("panne")), \
                mock.patch.object(frappe, "log_error"):
            lms._refuser_evaluation_bloquee(ELEVE, "LMS Assignment", self.devoir_a)


class TestListes(Base):
    def test_lecons_et_evaluations_du_parcours_bloque_absentes_des_listes(self):
        condition = lms.conditions_lecons(ELEVE)
        lecons = frappe.db.sql_list(f"select name from `tabCourse Lesson` where {condition}")
        self.assertNotIn(self.lecon_a, lecons)
        self.assertIn(self.lecon_b, lecons)
        frappe.set_user(ELEVE)
        for doctype, a, b in (("LMS Quiz", self.quiz_a, self.quiz_b),
                              ("LMS Assignment", self.devoir_a, self.devoir_b)):
            with self.subTest(doctype=doctype):
                noms = frappe.get_list(doctype, pluck="name")
                self.assertNotIn(a, noms)
                self.assertIn(b, noms)

    def test_sans_parcours_bloque_aucune_condition(self):
        self.assertEqual(lms.conditions_lecons("Administrator"), "")
        self.assertEqual(lms.conditions_quiz("Guest"), "")
        utilisateur(AUTRE)
        self.assertEqual(lms.conditions_devoirs(AUTRE), "")
        self.assertEqual(lms.conditions_exercices(None), "")

    def test_conditions_echappees(self):
        """OWASP A03 : les noms de parcours passent par frappe.db.escape."""
        with mock.patch.object(lms, "_cours_bloques", return_value=("x') or ('1'='1",)):
            self.assertIn("'x\\') or (\\'1\\'=\\'1'", lms.conditions_lecons(ELEVE))


class TestRedirectionDesPages(Base):
    def entrer(self, chemin, utilisateur=ELEVE, **options):
        frappe.set_user(utilisateur)
        frappe.local.request = requete(chemin, **options)
        try:
            http.before_request()
        except HTTPException as e:
            return e.get_response()
        return None

    def test_pages_d_un_parcours_bloque_redirigees(self):
        for suite in ("", "/", "/learn/1-1", "/learn/1.1", "/chapter/x", "/certification", "/enrollment/new"):
            with self.subTest(suite=suite):
                r = self.entrer(f"/lms/courses/{self.a}{suite}")
                self.assertEqual((r.status_code, r.headers["Location"]), (302, f"/espace/paiement/{self.a}"))

    def test_parcours_ouvert_et_autres_pages_jamais_redirigees(self):
        for chemin in (f"/lms/courses/{self.b}", f"/lms/courses/{self.b}/learn/1-1", "/lms", "/lms/courses",
                       "/lms/courses/new", "/lms/courses/import", f"/espace/paiement/{self.a}", "/logout",
                       "/login", f"/api/method/lms.lms.utils.get_lesson?course={self.a}", "/assets/x.js",
                       f"/app/lms-course/{self.a}", f"/lms/batches/{self.a}"):
            with self.subTest(chemin=chemin):
                self.assertIsNone(self.entrer(chemin))

    def test_seulement_les_pages_html_en_get(self):
        chemin = f"/lms/courses/{self.a}"
        self.assertIsNone(self.entrer(chemin, methode="POST"))
        self.assertIsNone(self.entrer(chemin, entetes={"Accept": "application/json"}))
        self.assertIsNone(self.entrer(chemin, entetes={}))

    def test_invite_et_exemptes_jamais_rediriges(self):
        self.assertIsNone(self.entrer(f"/lms/courses/{self.a}", utilisateur="Guest"))
        self.assertIsNone(self.entrer(f"/lms/courses/{self.a}", utilisateur="Administrator"))

    def test_aucune_requete_hors_des_pages_de_parcours(self):
        with mock.patch.object(lms, "parcours_bloque") as calcul:
            for chemin in ("/lms", "/espace/paiement/x", "/api/method/x", "/assets/x.css", "/app"):
                self.entrer(chemin)
            self.entrer(f"/lms/courses/{self.a}", utilisateur="Guest")
        calcul.assert_not_called()


class TestHooks(FrappeTestCase):
    def test_declares(self):
        self.assertEqual(hooks.before_request, ["openlab_academy.entrypoints.http.before_request"])
        self.assertEqual(hooks.override_whitelisted_methods, {
            "lms.lms.utils.get_lesson": "openlab_academy.entrypoints.lms.get_lesson",
            "lms.lms.utils.get_quiz_with_questions": "openlab_academy.entrypoints.lms.get_quiz_with_questions",
            "lms.lms.doctype.lms_quiz.lms_quiz.check_answer": "openlab_academy.entrypoints.lms.check_answer",
            "lms.lms.api.mark_lesson_progress": "openlab_academy.entrypoints.lms.mark_lesson_progress",
            "lms.lms.doctype.course_lesson.course_lesson.save_progress": "openlab_academy.entrypoints.lms.save_progress",
            "lms.lms.doctype.lms_certificate.lms_certificate.create_certificate":
                "openlab_academy.entrypoints.lms.create_certificate",
        })
        self.assertEqual(hooks.doc_events["LMS Certificate"],
                         {"before_insert": "openlab_academy.entrypoints.lms.avant_certificat"})
        for doctype in ("Course Lesson", "Course Chapter", "LMS Quiz", "LMS Assignment", "LMS Programming Exercise"):
            self.assertEqual(hooks.has_permission[doctype], "openlab_academy.entrypoints.lms.lecture_permise")
        self.assertEqual(hooks.permission_query_conditions, {
            "Course Lesson": "openlab_academy.entrypoints.lms.conditions_lecons",
            "LMS Quiz": "openlab_academy.entrypoints.lms.conditions_quiz",
            "LMS Assignment": "openlab_academy.entrypoints.lms.conditions_devoirs",
            "LMS Programming Exercise": "openlab_academy.entrypoints.lms.conditions_exercices",
        })
