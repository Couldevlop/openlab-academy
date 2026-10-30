"""Catalogue, accueil, recherche et cohortes limités aux parcours visibles, sur le banc : 5 parcours publiés dont 2
cachés (phase de lancement active), pour l'apprenant et le visiteur ; agents jamais filtrés ; pagination exacte."""
import datetime
from unittest import mock

import frappe
from frappe.tests.utils import FrappeTestCase
from lms import command_palette
from lms.lms import api as lms_api
from lms.lms import utils as lms_utils

from openlab_academy import hooks
from openlab_academy.domain.cohorte import Cohorte
from openlab_academy.domain.lancement import PhaseLancement
from openlab_academy.domain.parcours import Bloc
from openlab_academy.domain.reglages import Reglages
from openlab_academy.entrypoints import catalogue, lms
from openlab_academy.infrastructure import reglages_source_frappe
from openlab_academy.infrastructure.depot_cohortes_frappe import DepotCohortesFrappe
from openlab_academy.infrastructure.depot_frappe import DepotFrappe
from openlab_academy.tests.fabriques import parcours
from openlab_academy.tests.test_blocage_frappe import suivre, utilisateur
from openlab_academy.tests.test_exercices_frappe import module

ELEVE = "eleve.catalogue@example.ci"
TITRES = [f"Catalogue test {i}" for i in range(1, 6)]
DEBUT = datetime.date(2037, 3, 10)  # cohortes à venir
CLE_PHASE = "phase_lancement"


def noms(liste):
    return [c["name"] for c in liste]


class Base(FrappeTestCase):
    """c1, c2, c3 visibles ; c4, c5 cachés (le reste du site l'est aussi : seuls les parcours visibles restent)."""

    def setUp(self):
        lms.vider_cache()
        self.phase = mock.patch.object(reglages_source_frappe, "phase_lancement",
                                       return_value=PhaseLancement(False)).start()
        self.addCleanup(mock.patch.stopall)
        depot = DepotFrappe(commit=False, reglages=Reglages())
        self.c = [depot.creer(parcours(title=t, questions_par_quiz=5, blocs=(Bloc("B1", (module(),)),)))
                  for t in TITRES]
        self.visibles = self.c[:3]
        self.caches = self.c[3:]
        utilisateur(ELEVE)
        self.lots = {c: DepotCohortesFrappe().creer(Cohorte.fenetre(parcours(title=t), DEBUT, Reglages()))
                     for c, t in zip(self.c, TITRES)}
        frappe.db.set_single_value("LMS Settings", "allow_guest_access", 1)
        self.cacher()

    def tearDown(self):
        frappe.set_user("Administrator")
        lms.vider_cache()
        frappe.db.rollback()

    def cacher(self, visibles=None):
        lms.vider_cache()
        self.phase.return_value = PhaseLancement(True, frozenset(self.visibles if visibles is None else visibles))

    def decocher(self):
        lms.vider_cache()
        self.phase.return_value = PhaseLancement(False)

    def mes(self, liste):
        """Les parcours de ce test dans une liste de noms, dans l'ordre servi."""
        return [n for n in liste if n in self.c]

    def inscrire_a_la_cohorte(self, cours, membre=ELEVE):
        """Donnée de test : inscription à la cohorte sans passer par les crochets d'inscription."""
        frappe.get_doc({"doctype": "LMS Batch Enrollment", "batch": self.lots[cours], "member": membre}).db_insert()


class TestCatalogue(Base):
    def test_catalogue_sans_parcours_caches(self):
        for u in (ELEVE, "Guest"):
            with self.subTest(u=u):
                frappe.set_user(u)
                liste = noms(catalogue.get_courses({"live": 1}))
                self.assertCountEqual(self.mes(liste), self.visibles)
                self.assertCountEqual(liste, self.visibles)  # le reste du site est caché aussi

    def test_pagination_exacte(self):
        for u in (ELEVE, "Guest"):
            with self.subTest(u=u):
                frappe.set_user(u)
                pages = [noms(catalogue.get_courses({}, debut, 2)) for debut in (0, 2, 4)]
                self.assertEqual([len(p) for p in pages], [2, 1, 0])
                self.assertCountEqual(sum(pages, []), self.visibles)
                self.assertEqual(catalogue.get_course_count({}), 3)
                self.assertEqual(catalogue.get_course_count({"live": 1}), 3)

    def test_recherche_par_titre_filtree_et_comptee(self):
        frappe.set_user(ELEVE)
        self.assertEqual(noms(catalogue.get_courses({"title": TITRES[0]})), [self.c[0]])
        self.assertEqual(catalogue.get_course_count({"title": TITRES[0]}), 1)
        self.assertEqual(catalogue.get_courses({"title": TITRES[3]}), [])
        self.assertEqual(catalogue.get_course_count({"title": TITRES[3]}), 0)

    def test_onglet_inscrits_filtre(self):
        for c in (self.c[0], self.c[3]):
            suivre(c, ELEVE)
        frappe.set_user(ELEVE)
        self.assertEqual(noms(catalogue.get_courses({"enrolled": 1})), [self.c[0]])
        self.assertEqual(catalogue.get_course_count({"enrolled": 1}), 1)
        self.decocher()
        self.assertCountEqual(noms(catalogue.get_courses({"enrolled": 1})), [self.c[0], self.c[3]])

    def test_onglet_inscrits_garde_la_portee_a_soi(self):
        """Un brouillon auquel on est inscrit reste dans l'onglet (portée « à soi » du LMS), un caché non."""
        suivre(self.c[0], ELEVE)
        suivre(self.c[3], ELEVE)
        frappe.db.set_value("LMS Course", self.c[0], "published", 0)
        frappe.db.set_value("LMS Course", self.c[3], "published", 0)
        frappe.set_user(ELEVE)
        self.assertEqual(noms(catalogue.get_courses({"enrolled": 1})), [self.c[0]])
        self.assertEqual(catalogue.get_course_count({"enrolled": 1}), 1)
        self.assertNotIn(self.c[0], noms(catalogue.get_courses({})))  # hors de la portée à soi : brouillon masqué

    def test_onglet_crees_filtre(self):
        for c in (self.c[0], self.c[3]):
            frappe.get_doc({"doctype": "Course Instructor", "parent": c, "parenttype": "LMS Course",
                            "parentfield": "instructors", "instructor": ELEVE}).db_insert()
        frappe.set_user(ELEVE)
        self.assertEqual(noms(catalogue.get_courses({"created": 1})), [self.c[0]])
        self.assertEqual(catalogue.get_course_count({"created": 1}), 1)

    def test_filtre_de_nom_du_client_conserve_et_filtre(self):
        frappe.set_user(ELEVE)
        for filtre in ({"name": self.c[3]}, {"name": ["in", [self.c[0], self.c[3]]]},
                       {"name": ["like", "%atalogue-test%"]}, {"name": ["not in", [self.c[1]]]}):
            with self.subTest(filtre=filtre):
                liste = noms(catalogue.get_courses(dict(filtre)))
                self.assertFalse(set(liste) & set(self.caches))
                self.assertEqual(len(liste), catalogue.get_course_count(dict(filtre)))
        self.assertEqual(noms(catalogue.get_courses({"name": ["in", [self.c[0], self.c[3]]]})), [self.c[0]])

    def test_parcours_de_lancement_en_tete(self):
        frappe.db.set_value("LMS Course", self.c[2], "featured", 1)
        for u in (ELEVE, "Guest"):
            with self.subTest(u=u):
                frappe.set_user(u)
                self.assertEqual(noms(catalogue.get_courses({"live": 1}))[0], self.c[2])
                self.assertEqual(catalogue.get_course_count({"live": 1}), 3)

    def test_agents_voient_tout(self):
        for role in sorted(lms.ROLES_NON_BLOQUES):
            with self.subTest(role=role):
                frappe.set_user(utilisateur(f"agent.{role.split()[0].lower()}.cat@example.ci", role))
                lms.vider_cache()
                self.assertTrue(set(self.c) <= set(noms(catalogue.get_courses({}, 0, 120))))
                self.assertGreaterEqual(catalogue.get_course_count({}), 5)

    def test_phase_decochee_catalogue_complet(self):
        self.decocher()
        for u in (ELEVE, "Guest"):
            with self.subTest(u=u):
                frappe.set_user(u)
                self.assertTrue(set(self.c) <= set(noms(catalogue.get_courses({}, 0, 120))))
                self.cacher()
                self.assertCountEqual(noms(catalogue.get_courses({})), self.visibles)
                self.decocher()

    def test_acces_visiteur_desactive_inchange(self):
        frappe.db.set_single_value("LMS Settings", "allow_guest_access", 0)
        frappe.clear_cache(doctype="LMS Settings")
        frappe.set_user("Guest")
        self.assertEqual((catalogue.get_courses({}), catalogue.get_course_count({})), ([], 0))

    def test_exclusion_oubliee_apres_l_appel(self):
        frappe.set_user(ELEVE)
        catalogue.get_courses({})
        self.assertIsNone(getattr(frappe.local, catalogue.CLE_EXCLUSION, None))
        with mock.patch.object(lms_utils, "get_courses", side_effect=RuntimeError("panne")):
            with self.assertRaises(RuntimeError):
                catalogue.get_courses({})
        self.assertIsNone(getattr(frappe.local, catalogue.CLE_EXCLUSION, None))

    def test_calcul_impossible_ne_laisse_pas_tout_passer(self):
        """Échec du calcul de visibilité : la liste de repli (parcours limités) s'applique, jamais le catalogue entier."""
        frappe.set_user(ELEVE)
        with mock.patch.object(lms, "_visibilite", side_effect=RuntimeError("panne")), \
                mock.patch.object(frappe, "log_error"):
            self.assertTrue(set(noms(catalogue.get_courses({}, 0, 120))) >= set(self.c))


class TestAccueil(Base):
    def test_accueil_filtre(self):
        suivre(self.c[0], ELEVE)
        suivre(self.c[3], ELEVE)
        frappe.set_user(ELEVE)
        self.assertEqual(noms(catalogue.get_my_courses()), [self.c[0]])

    def test_accueil_repli_sur_les_parcours_visibles(self):
        """Inscrit seulement à un parcours caché : le repli du LMS (à la une, puis populaires) s'applique, sans caché."""
        suivre(self.c[3], ELEVE)
        frappe.db.set_value("LMS Course", self.c[1], "featured", 1)
        frappe.set_user(ELEVE)
        self.assertEqual(noms(catalogue.get_my_courses()), [self.c[1]])
        frappe.db.set_value("LMS Course", self.c[1], "featured", 0)
        lms.vider_cache()
        liste = noms(catalogue.get_my_courses())
        self.assertTrue(liste)
        self.assertFalse(set(liste) & set(self.caches))

    def test_accueil_sans_rien_a_montrer(self):
        suivre(self.c[3], ELEVE)
        self.cacher(visibles=())
        frappe.set_user(ELEVE)
        self.assertEqual(catalogue.get_my_courses(), [])

    def test_accueil_sans_inscription_inchange(self):
        frappe.set_user(ELEVE)
        with mock.patch.object(lms_api, "get_my_courses", return_value=[]):
            self.assertEqual(catalogue.get_my_courses(), [])

    def test_parcours_associes_filtres(self):
        for c in (self.c[1], self.c[3]):
            frappe.get_doc({"doctype": "Related Courses", "parent": self.c[0], "parenttype": "LMS Course",
                            "parentfield": "related_courses", "course": c}).db_insert()
        for u in (ELEVE, "Guest"):
            with self.subTest(u=u):
                frappe.set_user(u)
                self.assertEqual(noms(catalogue.get_related_courses(self.c[0])), [self.c[1]])

    def test_parcours_associes_d_un_parcours_cache_refuses(self):
        frappe.get_doc({"doctype": "Related Courses", "parent": self.c[3], "parenttype": "LMS Course",
                        "parentfield": "related_courses", "course": self.c[0]}).db_insert()
        frappe.set_user(ELEVE)
        self.assertEqual(catalogue.get_related_courses(self.c[3]), [])

    def test_agents_non_filtres(self):
        agent = utilisateur("agent.accueil.cat@example.ci", "Course Creator")
        suivre(self.c[3], agent)
        frappe.get_doc({"doctype": "Related Courses", "parent": self.c[0], "parenttype": "LMS Course",
                        "parentfield": "related_courses", "course": self.c[3]}).db_insert()
        frappe.set_user(agent)
        self.assertEqual(noms(catalogue.get_my_courses()), [self.c[3]])
        self.assertEqual(noms(catalogue.get_related_courses(self.c[0])), [self.c[3]])


class TestCohortes(Base):
    def test_cohortes_filtrees(self):
        for u in (ELEVE, "Guest"):
            with self.subTest(u=u):
                frappe.set_user(u)
                liste = noms(catalogue.get_batches({}, 0, "start_date", 120))
                for c in self.visibles:
                    self.assertIn(self.lots[c], liste)
                for c in self.caches:
                    self.assertNotIn(self.lots[c], liste)
                self.assertEqual(catalogue.get_batch_details(self.lots[self.c[3]]), {})
                self.assertEqual(catalogue.get_batch_details(self.lots[self.c[0]])["name"], self.lots[self.c[0]])

    def test_pagination_des_cohortes_exacte(self):
        frappe.set_user(ELEVE)
        tout = noms(catalogue.get_batches({}, 0, "start_date", 120))
        n = len(tout)
        pages = [noms(catalogue.get_batches({}, debut, "start_date", 2)) for debut in range(0, n + 1, 2)]
        self.assertEqual(sum(pages, []), tout)
        self.assertEqual([len(p) for p in pages], [min(2, n - debut) for debut in range(0, n + 1, 2)])

    def test_mes_cohortes_filtrees(self):
        self.inscrire_a_la_cohorte(self.c[0])
        self.inscrire_a_la_cohorte(self.c[3])
        frappe.set_user(ELEVE)
        self.assertEqual(noms(catalogue.get_my_batches()), [self.lots[self.c[0]]])
        self.assertEqual(noms(catalogue.get_batches({"enrolled": 1})), [self.lots[self.c[0]]])

    def test_mes_cohortes_repli_sur_les_cohortes_visibles(self):
        self.inscrire_a_la_cohorte(self.c[3])
        frappe.set_user(ELEVE)
        liste = noms(catalogue.get_my_batches())
        self.assertIn(self.lots[self.c[0]], liste)
        self.assertNotIn(self.lots[self.c[3]], liste)

    def test_cohorte_mixte_conservee(self):
        """Une cohorte reste visible tant qu'un de ses parcours l'est."""
        lot = frappe.get_doc("LMS Batch", self.lots[self.c[3]])
        lot.append("courses", {"course": self.c[0]})
        lot.save(ignore_permissions=True)
        frappe.set_user(ELEVE)
        self.assertIn(lot.name, noms(catalogue.get_batches({}, 0, "start_date", 120)))
        self.assertEqual(catalogue.get_batch_details(lot.name)["name"], lot.name)

    def test_cohorte_sans_parcours_conservee(self):
        lot = frappe.get_doc("LMS Batch", self.lots[self.c[3]])
        lot.set("courses", [])
        lot.save(ignore_permissions=True)
        frappe.set_user(ELEVE)
        self.assertIn(lot.name, noms(catalogue.get_batches({}, 0, "start_date", 120)))

    def test_agents_voient_toutes_les_cohortes(self):
        agent = utilisateur("agent.cohortes.cat@example.ci", "Batch Evaluator")
        frappe.set_user(agent)
        liste = noms(catalogue.get_batches({}, 0, "start_date", 120))
        for c in self.c:
            self.assertIn(self.lots[c], liste)
            self.assertEqual(catalogue.get_batch_details(self.lots[c])["name"], self.lots[c])

    def test_phase_decochee_toutes_les_cohortes(self):
        self.decocher()
        frappe.set_user(ELEVE)
        liste = noms(catalogue.get_batches({}, 0, "start_date", 120))
        for c in self.c:
            self.assertIn(self.lots[c], liste)


class TestRecherche(Base):
    def resultats(self):
        return [{"title": "Courses", "items": [
                    {"doctype": "LMS Course", "name": n, "title": n, "modified": "2037-01-01"} for n in self.c]},
                {"title": "Batches", "items": [
                    {"doctype": "LMS Batch", "name": self.lots[c], "title": c, "modified": "2037-01-01"}
                    for c in self.c]},
                {"title": "Quizzes", "items": [
                    {"doctype": "LMS Quiz", "name": "quiz-x", "title": "x", "modified": "2037-01-01"}]}]

    def chercher(self, **kw):
        with mock.patch.object(command_palette, "search_sqlite", return_value=self.resultats()) as original:
            resultat = catalogue.search_sqlite("catalogue", kw.get("category"))
        original.assert_called_once_with("catalogue", kw.get("category"))
        return resultat

    def groupe(self, resultat, titre):
        return next((g for g in resultat if g["title"] == titre), None)

    def test_recherche_filtree(self):
        for u in (ELEVE, "Guest"):
            with self.subTest(u=u):
                frappe.set_user(u)
                lms.vider_cache()
                resultat = self.chercher()
                self.assertCountEqual(noms(self.groupe(resultat, "Courses")["items"]), self.visibles)
                self.assertCountEqual(noms(self.groupe(resultat, "Batches")["items"]),
                                      [self.lots[c] for c in self.visibles])
                self.assertEqual(noms(self.groupe(resultat, "Quizzes")["items"]), ["quiz-x"])  # autres types intacts

    def test_groupe_vide_retire_et_categorie(self):
        self.cacher(visibles=())
        frappe.set_user(ELEVE)
        resultat = self.chercher(category="courses")
        self.assertIsNone(self.groupe(resultat, "Courses"))
        self.assertIsNone(self.groupe(resultat, "Batches"))
        self.assertIsNotNone(self.groupe(resultat, "Quizzes"))

    def test_agents_non_filtres(self):
        frappe.set_user(utilisateur("agent.recherche.cat@example.ci", "Moderator"))
        self.assertEqual(self.chercher(), self.resultats())

    def test_phase_decochee_recherche_complete(self):
        self.decocher()
        frappe.set_user(ELEVE)
        self.assertEqual(self.chercher(), self.resultats())


class TestHooks(FrappeTestCase):
    def test_surcharges_declarees(self):
        attendu = {
            "lms.lms.utils.get_courses": "get_courses",
            "lms.lms.utils.get_course_count": "get_course_count",
            "lms.lms.api.get_my_courses": "get_my_courses",
            "lms.lms.utils.get_related_courses": "get_related_courses",
            "lms.lms.utils.get_batches": "get_batches",
            "lms.lms.api.get_my_batches": "get_my_batches",
            "lms.lms.utils.get_batch_details": "get_batch_details",
            "lms.command_palette.search_sqlite": "search_sqlite",
        }
        for chemin, nom in attendu.items():
            self.assertEqual(hooks.override_whitelisted_methods[chemin], f"openlab_academy.entrypoints.catalogue.{nom}")
            self.assertTrue(callable(getattr(catalogue, nom)))
            self.assertIn(getattr(catalogue, nom), frappe.whitelisted)
