"""Fermeture et masquage des parcours sur le banc : pages, API, listes et permissions, pour l'apprenant et le visiteur ;
agents jamais refusés ; jamais rien d'écrit en base par le calcul."""
import dataclasses
import datetime
from unittest import mock

import frappe
import frappe.client
from frappe.tests.utils import FrappeTestCase
from lms.lms import utils as lms_utils
from werkzeug.exceptions import HTTPException

from openlab_academy import hooks
from openlab_academy.application.visibilite import Visibilite
from openlab_academy.domain.cohorte import Cohorte
from openlab_academy.domain.fenetre import un_mois_apres
from openlab_academy.domain.lancement import PhaseLancement
from openlab_academy.domain.parcours import Bloc
from openlab_academy.domain.reglages import Reglages
from openlab_academy.entrypoints import http, lms
from openlab_academy.infrastructure import reglages_source_frappe
from openlab_academy.infrastructure.depot_cohortes_frappe import DepotCohortesFrappe
from openlab_academy.infrastructure.depot_frappe import DepotFrappe
from openlab_academy.infrastructure.visibilite_frappe import SourceVisibiliteFrappe
from openlab_academy.tests.fabriques import parcours
from openlab_academy.tests.test_blocage_frappe import requete, suivre, utilisateur
from openlab_academy.tests.test_exercices_frappe import module

ELEVE = "eleve.visibilite@example.ci"
TITRE_LIMITE = "Parcours limité visibilité"
DEBUT = datetime.date(2027, 3, 10)
FIN = un_mois_apres(DEBUT)
DEDANS = datetime.date(2027, 3, 20)
LENDEMAIN = FIN + datetime.timedelta(days=1)
REGLAGES = "Reglages OpenLab Academy"


def creer_parcours(titre, limite=False):
    return DepotFrappe(commit=False, reglages=Reglages()).creer(
        parcours(title=titre, questions_par_quiz=5, blocs=(Bloc("B1", (module(),)),), acces_limite_a_la_cohorte=limite))


class Base(FrappeTestCase):
    """L : parcours limité à sa cohorte [DEBUT, FIN] ; A : parcours ordinaire. Phase de lancement décochée."""

    def setUp(self):
        self.requete_initiale = getattr(frappe.local, "request", None)
        lms.vider_cache()
        self.phase = mock.patch.object(reglages_source_frappe, "phase_lancement",
                                       return_value=PhaseLancement(False)).start()
        self.addCleanup(mock.patch.stopall)
        self.l = creer_parcours(TITRE_LIMITE, limite=True)
        self.a = creer_parcours("Parcours ordinaire visibilité")
        DepotCohortesFrappe().creer(Cohorte.fenetre(parcours(title=TITRE_LIMITE), DEBUT, Reglages()))
        utilisateur(ELEVE)
        for c in (self.l, self.a):
            suivre(c, ELEVE)
        self.lecon_l = frappe.db.get_value("Course Lesson", {"course": self.l, "title": ["like", "01 ·%"]})
        self.lecon_a = frappe.db.get_value("Course Lesson", {"course": self.a, "title": ["like", "01 ·%"]})
        self.quiz_l = frappe.db.get_value("LMS Quiz", {"course": self.l})
        self.lot = frappe.db.get_value("Batch Course", {"course": self.l, "parenttype": "LMS Batch"}, "parent")

    def tearDown(self):
        frappe.set_user("Administrator")
        frappe.local.response.pop("redirection", None)
        frappe.local.request = self.requete_initiale
        lms.vider_cache()
        frappe.db.rollback()

    def jour(self, jour):
        lms.vider_cache()
        mock.patch.object(lms, "aujourd_hui", return_value=jour).start()

    def cacher(self, *visibles):
        """Phase de lancement active : seuls `visibles` restent affichés."""
        lms.vider_cache()
        self.phase.return_value = PhaseLancement(True, frozenset(visibles))

    def entrer(self, chemin, utilisateur=ELEVE):
        frappe.set_user(utilisateur)
        frappe.local.request = requete(chemin)
        try:
            http.before_request()
        except HTTPException as e:
            return e.get_response()
        return None

    def refusee(self, appel, classe, *args):
        with self.assertRaises(classe) as e:
            appel(*args)
        self.assertEqual(frappe.local.response["redirection"], e.exception.redirection)
        frappe.local.response.pop("redirection", None)
        return e.exception

    def lecons_listees(self, cours):
        """Leçons que la liste de Frappe renvoie à l'utilisateur courant : les rôles sans lecture sur les leçons
        reçoivent déjà une erreur de permission (rien n'est listé), les autres une liste filtrée par la condition."""
        try:
            return frappe.get_list("Course Lesson", {"course": cours}, pluck="name")
        except frappe.PermissionError:
            return []

    def hors_condition(self, utilisateur, lecon):
        """La condition SQL de permission retire la leçon des requêtes de liste."""
        condition = lms.conditions_lecons(utilisateur)
        return lecon not in frappe.db.sql_list(f"select name from `tabCourse Lesson` where {condition or '1=1'}")

    def servie(self, cours, lecon):
        with mock.patch.object(lms_utils, "get_lesson", return_value={"name": lecon}):
            self.assertEqual(lms.get_lesson(cours, 1, 1)["name"], lecon)


class TestSource(Base):
    def test_fenetre_de_la_cohorte_publiee_la_plus_recente(self):
        source = SourceVisibiliteFrappe()
        self.assertEqual((source.fenetre(self.l).debut, source.fenetre(self.l).fin), (DEBUT, FIN))
        self.assertIsNone(source.fenetre(self.a))
        base = Cohorte.fenetre(parcours(title=TITRE_LIMITE), DEBUT, Reglages())
        debut = DEBUT + datetime.timedelta(days=60)
        DepotCohortesFrappe().creer(dataclasses.replace(
            base, titre=f"Promo 2 — {TITRE_LIMITE}", debut=debut, fin=un_mois_apres(debut)))
        self.assertEqual(SourceVisibiliteFrappe().fenetre(self.l).debut, debut)

    def test_limites_et_cours(self):
        source = SourceVisibiliteFrappe()
        self.assertTrue(source.limite(self.l))
        self.assertFalse(source.limite(self.a))
        self.assertIn(self.l, source.cours_limites_publies())
        self.assertNotIn(self.a, source.cours_limites_publies())
        self.assertTrue({self.l, self.a} <= set(source.tous_les_cours()))

    def test_lecture_unique_par_requete(self):
        self.jour(DEDANS)
        lms._visibilite().refuses(False)
        with mock.patch.object(frappe, "get_all") as lecture:
            lms._visibilite().refuses(False)
            lms.refus_pour(ELEVE, self.l)
        lecture.assert_not_called()
        self.assertEqual(self.phase.call_count, 1)


class TestPages(Base):
    def test_page_parcours_ferme_redirigee(self):
        self.jour(LENDEMAIN)
        for u in (ELEVE, "Guest"):
            for suite in ("", "/learn/1-1"):
                with self.subTest(u=u, suite=suite):
                    r = self.entrer(f"/lms/courses/{self.l}{suite}", u)
                    self.assertEqual((r.status_code, r.headers["Location"]), (302, f"/parcours-ferme/{self.l}"))

    def test_page_parcours_cache_redirigee(self):
        self.cacher()
        for u in (ELEVE, "Guest"):
            with self.subTest(u=u):
                r = self.entrer(f"/lms/courses/{self.a}", u)
                self.assertEqual((r.status_code, r.headers["Location"]), (302, "/lms/courses"))

    def test_page_ouverte_servie(self):
        self.jour(DEDANS)
        for u in (ELEVE, "Guest"):
            self.assertIsNone(self.entrer(f"/lms/courses/{self.l}", u))
            self.assertIsNone(self.entrer(f"/lms/courses/{self.a}", u))
        self.assertIsNone(self.entrer("/lms/courses"))

    def test_cohorte_dont_tous_les_parcours_sont_caches_redirigee(self):
        self.jour(DEDANS)
        self.assertIsNone(self.entrer(f"/lms/batches/{self.lot}"))
        self.cacher(self.a)
        for u in (ELEVE, "Guest"):
            r = self.entrer(f"/lms/batches/{self.lot}/suite", u)
            self.assertEqual((r.status_code, r.headers["Location"]), (302, "/lms/courses"))
        self.assertIsNone(self.entrer(f"/lms/batches/{self.lot}", "Administrator"))
        self.cacher(self.l)
        self.assertIsNone(self.entrer(f"/lms/batches/{self.lot}"))
        self.cacher()
        self.assertIsNone(self.entrer("/lms/batches/new"))

    def test_destinations_jamais_redirigees_en_boucle(self):
        self.cacher()
        for chemin in (f"/parcours-ferme/{self.l}", "/lms/courses", "/lms", "/lms/courses/new"):
            self.assertIsNone(self.entrer(chemin))

    def test_cohorte_en_erreur_pas_de_redirection(self):
        with mock.patch.object(frappe, "get_all", side_effect=RuntimeError("panne")), \
                mock.patch.object(frappe, "log_error") as journal:
            self.assertFalse(lms.lot_cache_pour(ELEVE, self.lot))
        self.assertEqual(journal.call_args.kwargs["title"], "Visibilité des parcours : calcul impossible")


class TestApi(Base):
    def test_api_lecon_refusee_hors_fenetre(self):
        self.jour(LENDEMAIN)
        for u in (ELEVE, "Guest"):
            with self.subTest(u=u):
                frappe.set_user(u)
                lms.vider_cache()
                with mock.patch.object(lms_utils, "get_lesson") as lecture:
                    e = self.refusee(lms.get_lesson, lms.ParcoursFerme, self.l, 1, 1)
                lecture.assert_not_called()
                self.assertEqual(e.redirection, f"/parcours-ferme/{self.l}")
                self.assertTrue(issubclass(lms.ParcoursFerme, frappe.ValidationError))
                with self.assertRaises(frappe.PermissionError):
                    frappe.client.get("Course Lesson", self.lecon_l)
                self.assertEqual(self.lecons_listees(self.l), [])
                self.assertTrue(self.hors_condition(u, self.lecon_l))
                self.refusee(lms.get_quiz_with_questions, lms.ParcoursFerme, self.quiz_l)
                self.refusee(lms.check_answer, lms.ParcoursFerme, self.quiz_l, "q", "Choices", "[]")
                self.refusee(lms.get_course_details, lms.ParcoursFerme, self.l)

    def test_api_lecon_cachee_refusee(self):
        self.cacher()
        for u in (ELEVE, "Guest"):
            with self.subTest(u=u):
                frappe.set_user(u)
                lms.vider_cache()
                e = self.refusee(lms.get_lesson, lms.ParcoursCache, self.a, 1, 1)
                self.assertEqual(e.redirection, "/lms/courses")
                self.assertTrue(issubclass(lms.ParcoursCache, frappe.ValidationError))
                with self.assertRaises(frappe.PermissionError):
                    frappe.client.get("Course Lesson", self.lecon_a)
                self.assertEqual(self.lecons_listees(self.a), [])
                self.assertTrue(self.hors_condition(u, self.lecon_a))

    def test_progression_et_certificat_refuses(self):
        self.cacher()
        frappe.set_user(ELEVE)
        for appel, args in ((lms.mark_lesson_progress, (self.a, 1, 1)), (lms.create_certificate, (self.a,)),
                            (lms.save_progress, (self.lecon_a,))):
            with self.subTest(appel=appel.__name__):
                self.refusee(appel, lms.ParcoursCache, *args)

    def test_dernier_jour_ouvert_lendemain_ferme(self):
        frappe.set_user(ELEVE)
        self.jour(FIN)
        self.servie(self.l, self.lecon_l)
        self.jour(LENDEMAIN)
        self.refusee(lms.get_lesson, lms.ParcoursFerme, self.l, 1, 1)
        self.jour(DEBUT - datetime.timedelta(days=1))
        self.refusee(lms.get_lesson, lms.ParcoursFerme, self.l, 1, 1)

    def test_dates_de_cohorte_changees_a_chaud(self):
        frappe.set_user(ELEVE)
        self.jour(LENDEMAIN)
        self.refusee(lms.get_lesson, lms.ParcoursFerme, self.l, 1, 1)
        frappe.db.set_value("LMS Batch", self.lot, "end_date", FIN + datetime.timedelta(days=7))
        lms.vider_cache()  # requête suivante
        self.servie(self.l, self.lecon_l)

    def test_agents_jamais_refuses(self):
        self.cacher()
        self.jour(LENDEMAIN)
        for role in sorted(lms.ROLES_NON_BLOQUES):
            with self.subTest(role=role):
                agent = utilisateur(f"agent.{role.split()[0].lower()}.vis@example.ci", role)
                lms.vider_cache()
                for cours, lecon in ((self.l, self.lecon_l), (self.a, self.lecon_a)):
                    self.assertIsNone(self.entrer(f"/lms/courses/{cours}", agent))
                    self.servie(cours, lecon)
                    self.assertIsNone(lms.lecture_permise(frappe.get_doc("Course Lesson", lecon), "read", agent))
                    self.assertIsNone(lms.refus_pour(agent, cours))
                self.assertEqual(lms.conditions_lecons(agent), "")
                self.assertEqual(lms.conditions_quiz(agent), "")
                self.assertIsNone(self.entrer(f"/lms/batches/{self.lot}", agent))

    def test_phase_decochee_tout_revient(self):
        modifie = frappe.db.get_value("LMS Course", self.a, "modified")
        frappe.set_user(ELEVE)
        self.cacher()
        self.refusee(lms.get_lesson, lms.ParcoursCache, self.a, 1, 1)
        self.phase.return_value = PhaseLancement(False, frozenset())
        lms.vider_cache()
        self.servie(self.a, self.lecon_a)
        self.cacher()
        self.refusee(lms.get_lesson, lms.ParcoursCache, self.a, 1, 1)
        self.assertEqual(frappe.db.get_value("LMS Course", self.a, "modified"), modifie)

    def test_phase_reelle_cochee_decochee_sans_ecriture_de_parcours(self):
        """Avec le vrai écran de réglages (document en cache) : la case suffit, le parcours n'est pas touché."""
        mock.patch.stopall()
        modifie = frappe.db.get_value("LMS Course", self.a, "modified")
        doc = frappe.get_doc(REGLAGES)
        self.addCleanup(frappe.clear_document_cache, REGLAGES, REGLAGES)
        for active, attendu in ((1, True), (0, False), (1, True)):
            doc.phase_lancement = active
            doc.set("parcours_lancement", [])
            doc.save(ignore_permissions=True)
            lms.vider_cache()
            self.assertEqual(lms.refus_pour(ELEVE, self.a) is not None, attendu)
        self.assertEqual(frappe.db.get_value("LMS Course", self.a, "modified"), modifie)

    def test_inscrit_d_un_parcours_cache_le_voit_cache(self):
        self.assertTrue(frappe.db.exists("LMS Enrollment", {"course": self.a, "member": ELEVE}))
        self.cacher(self.l)
        self.jour(DEDANS)
        frappe.set_user(ELEVE)
        self.refusee(lms.get_lesson, lms.ParcoursCache, self.a, 1, 1)
        self.assertEqual(self.lecons_listees(self.a), [])
        self.assertTrue(self.hors_condition(ELEVE, self.lecon_a))
        self.assertFalse(self.hors_condition(ELEVE, self.lecon_l))
        self.assertIsNone(self.entrer(f"/lms/courses/{self.l}"))

    def test_parcours_non_limite_hors_lancement_inchange(self):
        frappe.set_user(ELEVE)
        self.jour(datetime.date(2030, 1, 1))
        self.servie(self.a, self.lecon_a)
        self.assertIsNone(lms.refus_pour(ELEVE, self.a))
        self.assertIsNone(lms.refus_pour("Guest", self.a))
        lecons = frappe.db.sql_list(f"select name from `tabCourse Lesson` where {lms.conditions_lecons(ELEVE)}")
        self.assertIn(self.lecon_a, lecons)  # le parcours limité, fermé en 2030, est seul retiré
        self.assertNotIn(self.lecon_l, lecons)

    def test_blocage_paiement_inchange(self):
        """Parcours ouvert par la visibilité mais bloqué pour paiement : toujours renvoyé au paiement."""
        self.jour(DEDANS)
        frappe.set_user(ELEVE)
        with mock.patch.object(lms, "bloque_pour", return_value=True), self.assertRaises(lms.ParcoursBloque):
            lms.get_lesson(self.l, 1, 1)
        self.assertEqual(frappe.local.response["redirection"], f"/espace/paiement/{self.l}")

    def test_visibilite_avant_paiement(self):
        self.jour(LENDEMAIN)
        frappe.set_user(ELEVE)
        with mock.patch.object(lms, "bloque_pour", return_value=True), self.assertRaises(lms.ParcoursFerme):
            lms.get_lesson(self.l, 1, 1)

    def test_erreur_de_calcul_ferme_un_parcours_limite_sinon_aucun_masquage(self):
        self.jour(DEDANS)
        frappe.set_user(ELEVE)
        with mock.patch.object(Visibilite, "refus", side_effect=RuntimeError("panne")), \
                mock.patch.object(frappe, "log_error") as journal:
            self.assertEqual(lms.refus_pour(ELEVE, self.l), lms.Refus.FERME)
            self.assertIsNone(lms.refus_pour(ELEVE, self.a))
        self.assertEqual(journal.call_args.kwargs["title"], "Visibilité des parcours : calcul impossible")
        lms.vider_cache()
        with mock.patch.object(Visibilite, "refuses", side_effect=RuntimeError("panne")), \
                mock.patch.object(frappe, "log_error"):
            self.assertIn(self.l, lms._cours_refuses(ELEVE))
            self.assertNotIn(self.a, lms._cours_refuses(ELEVE))
            self.assertEqual(lms._cours_refuses("Administrator"), ())

    def test_evaluation_partagee_ouverte_tant_qu_un_parcours_l_est(self):
        self.cacher(self.a)
        self.assertIsNotNone(lms._refus_evaluation(ELEVE, "LMS Quiz", self.quiz_l))
        cible = "openlab_academy.infrastructure.contenus_parcours_frappe.cours_de_l_evaluation"
        with mock.patch(cible, return_value={self.l, self.a}):
            self.assertIsNone(lms._refus_evaluation(ELEVE, "LMS Quiz", self.quiz_l))
        with mock.patch(cible, side_effect=RuntimeError("panne")), mock.patch.object(frappe, "log_error"):
            self.assertIsNone(lms._refus_evaluation(ELEVE, "LMS Quiz", self.quiz_l))


class TestHooks(FrappeTestCase):
    def test_hooks_inchanges(self):
        self.assertEqual(hooks.has_permission["Course Lesson"], "openlab_academy.entrypoints.lms.lecture_permise")
        self.assertEqual(hooks.permission_query_conditions["Course Lesson"],
                         "openlab_academy.entrypoints.lms.conditions_lecons")
