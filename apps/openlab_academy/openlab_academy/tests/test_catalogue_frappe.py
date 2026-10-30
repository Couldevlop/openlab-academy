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
from openlab_academy.infrastructure.visibilite_frappe import CHAMP_LIMITE
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

    def creer_cache(self, titre):
        """Un parcours de plus, caché (hors des visibles), avec sa cohorte."""
        c = DepotFrappe(commit=False, reglages=Reglages()).creer(
            parcours(title=titre, questions_par_quiz=5, blocs=(Bloc("B1", (module(),)),)))
        self.lots[c] = DepotCohortesFrappe().creer(Cohorte.fenetre(parcours(title=titre), DEBUT, Reglages()))
        return c

    def agent(self, role="Course Creator"):
        return utilisateur(f"agent.{role.split()[0].lower()}.cat2@example.ci", role)

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

    def test_filtre_in_en_chaine_separee_par_des_virgules(self):
        for u in (ELEVE, "Guest"):
            with self.subTest(u=u):
                frappe.set_user(u)
                filtre = {"name": ["in", f"{self.c[0]}, {self.c[3]},{self.c[1]}"]}
                self.assertCountEqual(noms(catalogue.get_courses(dict(filtre))), [self.c[0], self.c[1]])
                self.assertEqual(catalogue.get_course_count(dict(filtre)), 2)

    def test_filet_si_le_lms_cesse_d_appeler_les_filtres(self):
        """Défense en profondeur : même sans l'exclusion avant requête, les listes sont refiltrées (et journalisées)."""
        agent = self.agent()
        with mock.patch.object(lms_utils, "update_course_filters", lms_utils.update_course_filters.original), \
                mock.patch.object(lms_utils, "update_batch_filters", lms_utils.update_batch_filters.original), \
                mock.patch.object(frappe, "log_error") as journal:
            for u in (ELEVE, "Guest"):
                with self.subTest(u=u):
                    frappe.set_user(u)
                    liste = noms(catalogue.get_courses({}, 0, 120))
                    self.assertTrue(set(self.visibles) <= set(liste))
                    self.assertFalse(set(liste) & set(self.caches))
                    lots = noms(catalogue.get_batches({}, 0, "start_date", 120))
                    self.assertIn(self.lots[self.c[0]], lots)
                    self.assertFalse(set(lots) & {self.lots[c] for c in self.caches})
            self.assertTrue(journal.called)
            journal.reset_mock()
            frappe.set_user(agent)
            self.assertTrue(set(self.c) <= set(noms(catalogue.get_courses({}, 0, 120))))
            journal.assert_not_called()

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

    def test_calcul_impossible_ferme_les_parcours_limites_des_non_agents(self):
        """Échec du calcul de visibilité : échec fermé pour le visiteur et l'apprenant (le parcours limité à sa cohorte
        est retiré de la liste et du total, sans fermer tout le catalogue) ; les agents gardent tout."""
        frappe.db.set_value("LMS Course", self.c[0], CHAMP_LIMITE, 1)
        agent = self.agent()
        for u in (ELEVE, "Guest", agent):
            with self.subTest(u=u):
                frappe.set_user(u)
                lms.vider_cache()
                with mock.patch.object(lms, "_visibilite", side_effect=RuntimeError("panne")), \
                        mock.patch.object(frappe, "log_error"):
                    liste = noms(catalogue.get_courses({}, 0, 120))
                    total = catalogue.get_course_count({})
                self.assertEqual(self.c[0] in liste, u == agent)
                self.assertTrue(set(self.c[1:]) <= set(liste))
                self.assertEqual(total, len(liste))


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

    def test_accueil_inscriptions_visibles_au_dela_des_trois_dernieres(self):
        """Les trois dernières inscriptions sont cachées : les inscriptions visibles plus anciennes restent servies, au
        plus trois (comme le LMS une fois filtré), les plus récentes d'abord."""
        extra = self.creer_cache("Catalogue extra 1")
        for i, c in enumerate([self.c[0], self.c[1], self.c[2], self.c[3], self.c[4], extra]):
            suivre(c, ELEVE)
            frappe.db.set_value("LMS Enrollment", {"course": c, "member": ELEVE}, "modified",
                                datetime.datetime(2037, 1, 1, 10, i, 0), update_modified=False)
        frappe.set_user(ELEVE)
        self.assertEqual(noms(catalogue.get_my_courses()), [self.c[2], self.c[1], self.c[0]])

    def test_accueil_sans_rien_a_montrer(self):
        suivre(self.c[3], ELEVE)
        self.cacher(visibles=())
        frappe.set_user(ELEVE)
        self.assertEqual(catalogue.get_my_courses(), [])

    def test_accueil_sans_filtre_appelle_l_original(self):
        """Phase décochée : rien n'est refusé, le LMS répond tel quel."""
        self.decocher()
        frappe.set_user(ELEVE)
        with mock.patch.object(lms_api, "get_my_courses", return_value=["tel quel"]) as original:
            self.assertEqual(catalogue.get_my_courses(), ["tel quel"])
        original.assert_called_once_with()

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

    def lot_mixte(self):
        """La cohorte du parcours caché c4 porte aussi le parcours visible c1."""
        lot = frappe.get_doc("LMS Batch", self.lots[self.c[4]])
        lot.append("courses", {"course": self.c[1]})
        lot.save(ignore_permissions=True)
        return lot.name

    def test_parcours_de_cohorte_sans_parcours_refuses(self):
        lot = self.lot_mixte()
        for u in (ELEVE, "Guest"):
            with self.subTest(u=u):
                frappe.set_user(u)
                self.assertEqual(noms(catalogue.get_batch_courses(self.lots[self.c[0]])), [self.c[0]])
                self.assertEqual(catalogue.get_batch_courses(self.lots[self.c[3]]), [])
                self.assertEqual(noms(catalogue.get_batch_courses(lot)), [self.c[1]])
        frappe.set_user(self.agent("Batch Evaluator"))
        self.assertEqual(noms(catalogue.get_batch_courses(self.lots[self.c[3]])), [self.c[3]])
        self.assertCountEqual(noms(catalogue.get_batch_courses(lot)), [self.c[1], self.c[4]])

    def test_total_des_cohortes_egal_a_la_liste(self):
        self.inscrire_a_la_cohorte(self.c[0])
        self.inscrire_a_la_cohorte(self.c[3])
        for u in (ELEVE, "Guest"):
            for filtre in ({}, {"enrolled": 1}):
                with self.subTest(u=u, filtre=filtre):
                    frappe.set_user(u)
                    liste = catalogue.get_batches(dict(filtre), 0, "start_date", 120)
                    self.assertEqual(catalogue.get_batch_count(dict(filtre)), len(liste))
        frappe.set_user(ELEVE)
        total_apprenant = catalogue.get_batch_count({})
        frappe.set_user(self.agent("Batch Evaluator"))
        self.assertGreaterEqual(catalogue.get_batch_count({}), total_apprenant + 2)  # c3, c4 et le reste du site

    def test_cohorte_mixte_sans_titre_du_parcours_refuse(self):
        lot = self.lot_mixte()
        for u in (ELEVE, "Guest"):
            with self.subTest(u=u):
                frappe.set_user(u)
                self.assertEqual([c["course"] for c in catalogue.get_batch_details(lot)["courses"]], [self.c[1]])
        frappe.set_user(self.agent("Batch Evaluator"))
        self.assertCountEqual([c["course"] for c in catalogue.get_batch_details(lot)["courses"]],
                              [self.c[1], self.c[4]])

    def test_mes_cohortes_inscriptions_visibles_au_dela_des_quatre_dernieres(self):
        extra = [self.creer_cache(f"Catalogue extra {i}") for i in (1, 2)]
        for i, c in enumerate([self.c[0], self.c[3], self.c[4], *extra]):
            self.inscrire_a_la_cohorte(c)
            frappe.db.set_value("LMS Batch Enrollment", {"batch": self.lots[c], "member": ELEVE}, "creation",
                                datetime.datetime(2037, 1, 1, 10, i, 0), update_modified=False)
        frappe.set_user(ELEVE)
        self.assertEqual(noms(catalogue.get_my_batches()), [self.lots[self.c[0]]])

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


class TestAutresSurfaces(Base):
    """Catégories, statistiques, avis, programmes et résumé de commande : rien d'un parcours refusé."""

    def test_categories_des_seuls_parcours_visibles(self):
        frappe.db.set_value("LMS Course", self.c[0], "category", "Categorie visible")
        frappe.db.set_value("LMS Course", self.c[3], "category", "Categorie cachee")
        for u in (ELEVE, "Guest"):
            with self.subTest(u=u):
                frappe.set_user(u)
                valeurs = [o["value"] for o in catalogue.get_course_categories()]
                self.assertIn("Categorie visible", valeurs)
                self.assertNotIn("Categorie cachee", valeurs)
                self.assertIn(None, valeurs)
        frappe.set_user(self.agent())
        valeurs = [o["value"] for o in catalogue.get_course_categories()]
        self.assertTrue({"Categorie visible", "Categorie cachee"} <= set(valeurs))

    def test_statistiques_des_seuls_parcours_visibles(self):
        for c in (self.c[0], self.c[3]):
            suivre(c, ELEVE)
        visibles = {"course": ["in", self.visibles]}
        for u in (ELEVE, "Guest"):
            with self.subTest(u=u):
                frappe.set_user(u)
                stats = catalogue.get_chart_details()
                self.assertEqual(stats["courses"], frappe.db.count(
                    "LMS Course", {"published": 1, "upcoming": 0, "name": ["in", self.visibles]}))
                self.assertEqual(stats["enrollments"], frappe.db.count("LMS Enrollment", visibles))
                self.assertEqual(stats["completions"], frappe.db.count(
                    "LMS Enrollment", {**visibles, "progress": ["like", "%100%"]}))
                self.assertEqual(stats["certifications"], frappe.db.count(
                    "LMS Certificate", {**visibles, "published": 1}))
        frappe.set_user(self.agent())
        agent = catalogue.get_chart_details()
        self.assertGreaterEqual(agent["courses"], 5)
        self.assertGreater(agent["enrollments"], frappe.db.count("LMS Enrollment", visibles))

    def avis(self, cours):
        """Donnée de test : avis écrit sans passer par les contrôles d'inscription du LMS."""
        doc = frappe.get_doc({"doctype": "LMS Course Review", "course": cours, "rating": 0.8, "review": "Très bien"})
        doc.name = frappe.generate_hash(length=10)
        doc.owner = doc.modified_by = "Administrator"
        doc.creation = doc.modified = frappe.utils.now()
        doc.db_insert()

    def test_avis_d_un_parcours_refuse_refuses(self):
        self.avis(self.c[0])
        self.avis(self.c[3])
        for u in (ELEVE, "Guest"):
            with self.subTest(u=u):
                frappe.set_user(u)
                lms.vider_cache()
                self.assertEqual(len(catalogue.get_reviews(self.c[0])), 1)
                with self.assertRaises(lms.ParcoursCache):
                    catalogue.get_reviews(self.c[3])
                frappe.local.response.pop("redirection", None)
        frappe.set_user(self.agent())
        self.assertEqual(len(catalogue.get_reviews(self.c[3])), 1)

    def test_resume_de_commande_d_un_parcours_refuse_refuse(self):
        with mock.patch.object(lms_utils, "get_order_summary", return_value={"title": "x"}) as original:
            frappe.set_user(ELEVE)
            self.assertEqual(catalogue.get_order_summary("LMS Course", self.c[0], "CODE", "CI"), {"title": "x"})
            original.assert_called_once_with("LMS Course", self.c[0], "CODE", "CI")
            original.reset_mock()
            with self.assertRaises(lms.ParcoursCache):
                catalogue.get_order_summary("LMS Course", self.c[3])
            original.assert_not_called()
            frappe.local.response.pop("redirection", None)
            frappe.set_user(self.agent())
            catalogue.get_order_summary("LMS Course", self.c[3])
            original.assert_called_once()

    def test_resume_de_commande_d_une_cohorte_inchange(self):
        with mock.patch.object(lms_utils, "get_order_summary", return_value={"title": "x"}) as original:
            frappe.set_user(ELEVE)
            catalogue.get_order_summary("LMS Batch", self.lots[self.c[0]])
            original.assert_called_once()

    def test_programme_sans_parcours_refuse(self):
        def detail(_):
            return frappe._dict(name="prog", courses=[frappe._dict(name=n) for n in (self.c[0], self.c[3], self.c[1])])

        with mock.patch.object(lms_utils, "get_program_details", side_effect=detail):
            frappe.set_user(ELEVE)
            self.assertEqual(noms(catalogue.get_program_details("prog")["courses"]), [self.c[0], self.c[1]])
            frappe.set_user(self.agent())
            self.assertEqual(noms(catalogue.get_program_details("prog")["courses"]), [self.c[0], self.c[3], self.c[1]])


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
            "lms.lms.utils.get_batch_courses": "get_batch_courses",
            "lms.lms.utils.get_batch_count": "get_batch_count",
            "lms.lms.utils.get_course_categories": "get_course_categories",
            "lms.lms.api.get_chart_details": "get_chart_details",
            "lms.lms.utils.get_reviews": "get_reviews",
            "lms.lms.utils.get_program_details": "get_program_details",
            "lms.lms.utils.get_order_summary": "get_order_summary",
        }
        for chemin, nom in attendu.items():
            self.assertEqual(hooks.override_whitelisted_methods[chemin], f"openlab_academy.entrypoints.catalogue.{nom}")
            self.assertTrue(callable(getattr(catalogue, nom)))
            self.assertIn(getattr(catalogue, nom), frappe.whitelisted)
