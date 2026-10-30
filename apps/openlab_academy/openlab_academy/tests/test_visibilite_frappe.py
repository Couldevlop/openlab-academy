"""Fermeture et masquage des parcours sur le banc : pages, API, listes et permissions, pour l'apprenant et le visiteur ;
agents jamais refusés ; jamais rien d'écrit en base par le calcul."""
import dataclasses
import datetime
from unittest import mock
from urllib.parse import quote

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
        self.chapitre_l = frappe.db.get_value("Course Chapter", {"course": self.l})
        self.devoir_l = frappe.db.get_value(
            "LMS Lesson Assessment", {"parent": self.lecon_l, "assessment_type": "LMS Assignment"}, "assessment_name")
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

    def hors_liste(self, doctype, condition, nom):
        """La condition SQL de permission retire l'évaluation des requêtes de liste."""
        return nom not in frappe.db.sql_list(f"select name from `tab{doctype}` where {condition or '1=1'}")

    def lecture_refusee(self, utilisateur):
        """Le hook has_permission refuse la lecture de la leçon, du chapitre et des évaluations du parcours limité
        (lui seul : Course Lesson n'est lisible que des rôles d'écriture, la lecture du LMS ne prouve rien)."""
        for doctype, nom in (("Course Lesson", self.lecon_l), ("Course Chapter", self.chapitre_l),
                             ("LMS Quiz", self.quiz_l), ("LMS Assignment", self.devoir_l)):
            with self.subTest(doctype=doctype, utilisateur=utilisateur):
                doc = frappe.get_doc(doctype, nom)
                self.assertIs(lms.lecture_permise(doc, "read", utilisateur), False)
                self.assertIsNone(lms.lecture_permise(doc, "write", utilisateur))

    def evaluations_retirees(self, utilisateur):
        """Les quatre conditions de liste retirent les évaluations du parcours limité (et celui-là seul)."""
        self.assertTrue(self.hors_liste("LMS Quiz", lms.conditions_quiz(utilisateur), self.quiz_l))
        self.assertTrue(self.hors_liste("LMS Assignment", lms.conditions_devoirs(utilisateur), self.devoir_l))
        self.assertIn(frappe.db.escape(self.l), lms.conditions_exercices(utilisateur))
        self.assertNotIn(frappe.db.escape(self.a), lms.conditions_exercices(utilisateur))

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

    def test_fenetre_de_visibilite_suit_la_cohorte_fenetre_et_non_un_pilote_plus_tardif(self):
        debut = DEBUT + datetime.timedelta(days=60)
        pilote = DepotCohortesFrappe().creer(
            Cohorte.pilote(parcours(title=TITRE_LIMITE), debut, Reglages().rythme("standard"), Reglages()))
        self.assertNotEqual(pilote, self.lot)
        fenetre = SourceVisibiliteFrappe().fenetre(self.l)
        self.assertEqual((fenetre.debut, fenetre.fin), (DEBUT, FIN))
        self.assertEqual(DepotCohortesFrappe().fenetre_de(self.l), self.lot)

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
                self.lecture_refusee(u)
                self.evaluations_retirees(u)
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
                self.assertIs(lms.lecture_permise(frappe.get_doc("Course Lesson", self.lecon_a), "read", u), False)

    def test_evaluations_du_parcours_ferme_refusees_a_l_apprenant(self):
        """LMS Student lit les quiz : le refus vient bien de notre hook, pas des rôles du LMS."""
        self.jour(LENDEMAIN)
        frappe.set_user(ELEVE)
        with self.assertRaises(frappe.PermissionError):
            frappe.client.get("LMS Quiz", self.quiz_l)
        self.assertNotIn(self.quiz_l, frappe.get_list("LMS Quiz", pluck="name"))
        self.assertNotIn(self.devoir_l, frappe.get_list("LMS Assignment", pluck="name"))
        self.jour(DEDANS)
        self.assertEqual(frappe.client.get("LMS Quiz", self.quiz_l)["name"], self.quiz_l)
        self.assertIn(self.quiz_l, frappe.get_list("LMS Quiz", pluck="name"))

    def test_progression_et_certificat_refuses(self):
        self.cacher()
        frappe.set_user(ELEVE)
        for appel, args in ((lms.mark_lesson_progress, (self.a, 1, 1)), (lms.create_certificate, (self.a,)),
                            (lms.save_progress, (self.lecon_a,))):
            with self.subTest(appel=appel.__name__):
                self.refusee(appel, lms.ParcoursCache, *args)

    def test_dernier_jour_ouvert_lendemain_ferme(self):
        frappe.set_user(ELEVE)
        self.jour(DEBUT)
        self.servie(self.l, self.lecon_l)
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
                    self.assertIsNone(lms.lecture_permise(frappe.get_doc("LMS Quiz", self.quiz_l), "read", agent))
                    self.assertIsNone(lms.refus_pour(agent, cours))
                self.assertEqual(lms.conditions_lecons(agent), "")
                self.assertEqual((lms.conditions_quiz(agent), lms.conditions_devoirs(agent),
                                  lms.conditions_exercices(agent)), ("", "", ""))
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


class TestRefusEvaluationPartagee(Base):
    def test_ferme_prime_sur_cache_quel_que_soit_l_ordre(self):
        """Évaluation partagée refusée dans deux parcours : la destination ne dépend pas de l'ordre des noms."""
        cible = "openlab_academy.infrastructure.contenus_parcours_frappe.cours_de_l_evaluation"
        for ferme in (self.l, self.a):
            refus = lambda u, c: lms.Refus.FERME if c == ferme else lms.Refus.CACHE  # noqa: E731
            with self.subTest(ferme=ferme), mock.patch(cible, return_value={self.l, self.a}), \
                    mock.patch.object(lms, "refus_pour", side_effect=refus):
                self.assertEqual(lms._refus_evaluation(ELEVE, "LMS Quiz", "q"), (lms.Refus.FERME, ferme))
                with self.assertRaises(lms.ParcoursFerme) as e:
                    lms._refuser_evaluation_bloquee(ELEVE, "LMS Quiz", "q")
                self.assertEqual(e.exception.redirection, f"/parcours-ferme/{ferme}")


class TestMessages(Base):
    def test_messages_traduits(self):
        self.addCleanup(setattr, frappe.local, "lang", frappe.local.lang)
        for langue, ferme, cache in (("fr", "Parcours fermé", "Parcours indisponible"),
                                     ("en", "Course closed", "Course unavailable")):
            frappe.local.lang = langue
            with self.subTest(langue=langue):
                self.assertEqual(str(lms.ParcoursFerme(self.l)), ferme)
                self.assertEqual(str(lms.ParcoursCache(self.a)), cache)


FICHIER = "openlab_academy.entrypoints.lms.course_lesson.serve_resource"
REFERENCES = "openlab_academy.infrastructure.contenus_parcours_frappe.references_avouees"


class TestRessources(Base):
    """serve_resource du LMS (allow_guest) sert les fichiers privés d'une leçon : il suit le refus de son parcours,
    leçon par leçon (un fichier partagé n'est servi que par une leçon accessible d'un parcours ni refusé ni bloqué)."""

    def setUp(self):
        super().setUp()
        frappe.set_user("Administrator")
        fichier = frappe.get_doc({
            "doctype": "File", "file_name": f"support visibilite {frappe.generate_hash(length=6)}.txt",
            "content": frappe.generate_hash(length=20).encode(), "is_private": 1}).insert()
        self.addCleanup(self.supprimer_fichier, fichier.name)
        self.lien = fichier.file_url
        for lecon in (self.lecon_l, self.lecon_a):
            frappe.db.set_value("Course Lesson", lecon, "content", f'{{"blocks": ["{self.lien}"]}}')
        frappe.db.set_single_value("LMS Settings", "allow_guest_access", 1)
        for cours in (self.l, self.a):
            frappe.db.set_value("LMS Course", cours, "published", 1)
        frappe.db.set_value("Course Lesson", self.lecon_l, "include_in_preview", 1)
        lms.vider_cache()

    @staticmethod
    def supprimer_fichier(nom):
        if frappe.db.exists("File", nom):
            frappe.get_doc("File", nom).delete()

    def servir(self, utilisateur, attendu_servi, adresse=None):
        adresse = adresse or self.lien
        frappe.set_user(utilisateur)
        lms.vider_cache()
        with mock.patch(FICHIER, return_value="octets") as service:
            if attendu_servi:
                self.assertEqual(lms.serve_resource(adresse), "octets")
                service.assert_called_once_with(adresse)
            else:
                with self.assertRaises(frappe.PermissionError):
                    lms.serve_resource(adresse)
                service.assert_not_called()

    def parcours_seul(self, cours):
        """Le fichier n'est cité que par la leçon de ce parcours."""
        autre = self.lecon_a if cours == self.l else self.lecon_l
        frappe.db.set_value("Course Lesson", autre, "content", "{}")

    def desinscrire(self, cours):
        for nom in frappe.get_all("LMS Enrollment", {"course": cours, "member": ELEVE}, pluck="name"):
            frappe.delete_doc("LMS Enrollment", nom, force=True, ignore_permissions=True)

    def test_servi_quand_le_parcours_est_ouvert(self):
        self.jour(DEDANS)
        self.parcours_seul(self.l)
        for u in (ELEVE, "Guest", "Administrator"):
            with self.subTest(u=u):
                self.servir(u, True)

    def test_refuse_hors_fenetre_a_l_apprenant_et_au_visiteur(self):
        self.jour(LENDEMAIN)
        self.parcours_seul(self.l)
        for u in (ELEVE, "Guest"):
            with self.subTest(u=u):
                self.servir(u, False)

    def test_refuse_pendant_le_masquage(self):
        self.cacher()
        self.parcours_seul(self.a)
        for u in (ELEVE, "Guest"):
            with self.subTest(u=u):
                self.servir(u, False)

    def test_refuse_pour_paiement(self):
        self.jour(DEDANS)
        self.parcours_seul(self.l)
        with mock.patch.object(lms, "parcours_bloque", return_value=True):
            self.servir(ELEVE, False)
        self.servir(ELEVE, True)  # payeur à jour

    def test_agents_toujours_servis(self):
        self.cacher()
        self.jour(LENDEMAIN)
        self.parcours_seul(self.l)
        for role in sorted(lms.ROLES_NON_BLOQUES):
            with self.subTest(role=role), mock.patch.object(lms, "parcours_bloque", return_value=True):
                self.servir(utilisateur(f"agent.{role.split()[0].lower()}.res@example.ci", role), True)

    def test_fichier_partage_servi_par_la_lecon_accessible_d_un_parcours_ouvert(self):
        self.jour(LENDEMAIN)  # L fermé, A ouvert (ordinaire), élève inscrit aux deux
        self.servir(ELEVE, True)
        self.cacher()
        self.servir(ELEVE, False)

    def test_fichier_partage_refuse_a_l_eleve_inscrit_au_seul_parcours_ferme(self):
        self.desinscrire(self.a)
        self.jour(DEDANS)
        self.servir(ELEVE, True)  # témoin : L ouvert
        self.jour(LENDEMAIN)
        self.servir(ELEVE, False)  # la leçon de A n'est pas accessible à l'élève, celle de L est fermée
        self.servir("Administrator", True)

    def test_fichier_partage_refuse_au_visiteur_via_la_lecon_d_apercu_du_parcours_ferme(self):
        self.jour(DEDANS)
        self.servir("Guest", True)  # témoin : leçon d'aperçu de L, L ouvert
        self.jour(LENDEMAIN)
        self.servir("Guest", False)  # A ordinaire est ouvert mais sa leçon n'est pas d'aperçu
        frappe.db.set_value("Course Lesson", self.lecon_a, "include_in_preview", 1)
        self.servir("Guest", True)  # une leçon d'aperçu d'un parcours ouvert sert le fichier

    def test_adresse_encodee_decodee_comme_le_lms(self):
        self.jour(DEDANS)
        self.parcours_seul(self.l)
        encodee = quote(self.lien)
        self.assertIn("%20", encodee)
        self.servir(ELEVE, True, adresse=encodee)
        self.jour(LENDEMAIN)
        self.servir(ELEVE, False, adresse=encodee)

    def test_refus_journalise_sans_donnee_sensible(self):
        self.jour(LENDEMAIN)
        self.parcours_seul(self.l)
        frappe.set_user(ELEVE)
        with mock.patch.object(frappe, "logger") as journal:
            with self.assertRaises(frappe.PermissionError):
                lms.serve_resource(self.lien)
        journal.assert_called_with("lms.security")
        format_, utilisateur_, adresse_, motif = journal.return_value.warning.call_args.args
        self.assertEqual((utilisateur_, adresse_), (ELEVE, self.lien))
        self.assertIn("denied", format_)
        self.assertNotIn(ELEVE, motif)

    def test_agent_servi_meme_si_le_calcul_des_references_echoue(self):
        with mock.patch(REFERENCES, side_effect=RuntimeError("changement interne")) as calcul:
            self.servir("Administrator", True)
        calcul.assert_not_called()

    def test_echec_du_calcul_refuse_les_autres_et_le_journalise(self):
        for u in (ELEVE, "Guest"):
            frappe.set_user(u)
            with self.subTest(u=u), mock.patch(REFERENCES, side_effect=RuntimeError("changement interne")),                     mock.patch.object(frappe, "logger") as journal, mock.patch.object(frappe, "log_error") as erreur,                     mock.patch(FICHIER) as service:
                with self.assertRaises(frappe.PermissionError):
                    lms.serve_resource(self.lien)
                service.assert_not_called()
                erreur.assert_called_once()
                self.assertIn("calcul impossible", journal.return_value.warning.call_args.args[-1])

    def test_fichier_inconnu_laisse_au_lms(self):
        frappe.set_user(ELEVE)
        with mock.patch(FICHIER, return_value="refus du LMS") as service:
            self.assertEqual(lms.serve_resource("/private/files/introuvable.pdf"), "refus du LMS")
        service.assert_called_once()

    def test_surcharge_declaree(self):
        self.assertEqual(hooks.override_whitelisted_methods["lms.lms.doctype.course_lesson.course_lesson.serve_resource"],
                         "openlab_academy.entrypoints.lms.serve_resource")
        self.assertIs(lms.serve_resource.__module__, lms.__name__)
        self.assertTrue(lms.serve_resource in frappe.guest_methods)


class TestHooks(FrappeTestCase):
    def test_hooks_inchanges(self):
        self.assertEqual(hooks.has_permission["Course Lesson"], "openlab_academy.entrypoints.lms.lecture_permise")
        self.assertEqual(hooks.permission_query_conditions["Course Lesson"],
                         "openlab_academy.entrypoints.lms.conditions_lecons")
