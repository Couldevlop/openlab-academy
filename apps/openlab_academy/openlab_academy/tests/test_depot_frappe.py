import json
import pathlib
import tempfile

import frappe
import yaml
from frappe.tests.utils import FrappeTestCase

from openlab_academy.application.publier_parcours import PublierParcours, Statut
from openlab_academy.domain.parcours import Bloc, Module
from openlab_academy.entrypoints import seed
from openlab_academy.infrastructure.depot_frappe import DepotFrappe
from openlab_academy.tests.fabriques import parcours, parcours_brut, projet

TITRE = "Parcours de test seed"


def compter(cours):
    return (frappe.db.count("Course Chapter", {"course": cours}),
            frappe.db.count("Course Lesson", {"course": cours}),
            frappe.db.count("LMS Assignment", {"course": cours}))


def lecon(cours, prefixe):
    return frappe.get_doc("Course Lesson", {"course": cours, "title": ["like", f"{prefixe}%"]})


class TestDepotFrappe(FrappeTestCase):
    def setUp(self):
        self.depot = DepotFrappe(commit=False)
        self.p = parcours(title=TITRE)

    def tearDown(self):
        frappe.db.rollback()

    def test_creation_complete(self):
        nom = self.depot.creer(self.p)
        self.assertEqual(self.depot.trouver(TITRE), nom)
        # 1 bloc + 10 projets + capstone = 12 chapitres ; 1 module + 11 énoncés = 12 leçons et 12 devoirs
        self.assertEqual(compter(nom), (12, 12, 12))
        cours = frappe.get_doc("LMS Course", nom)
        self.assertEqual((cours.published, cours.enable_certification, cours.tags), (1, 1, "x"))
        self.assertEqual([i.instructor for i in cours.instructors], ["Administrator"])
        titres = [frappe.db.get_value("Course Chapter", c.chapter, "title") for c in cours.chapters]
        self.assertEqual(titres, [c.titre for c in self.p.chapitres()])

    def test_devoir_rattache_a_sa_lecon(self):
        nom = self.depot.creer(self.p)
        l = lecon(nom, "01 ·")
        devoir = frappe.get_doc("LMS Assignment", l.assessments[0].assessment_name)
        self.assertEqual((l.assessments[0].assessment_type, devoir.type, devoir.grade_assignment, devoir.course),
                         ("LMS Assignment", "URL", 1, nom))
        self.assertEqual(json.loads(l.content)["blocks"][-1]["data"], {"assignment": devoir.name})
        self.assertEqual(devoir.title, "Livrable 01 — M")

    def test_remplacer_sans_doublon(self):
        nom = self.depot.creer(self.p)
        blocs = (Bloc("B1", (Module("01", "Module renommé", "c", "l"),)),)
        self.depot.remplacer(nom, parcours(title=TITRE, short_introduction="Nouvelle", blocs=blocs))
        self.assertEqual(compter(nom), (12, 12, 12))
        self.assertEqual(frappe.db.get_value("LMS Course", nom, "short_introduction"), "Nouvelle")
        self.assertTrue(frappe.db.exists("Course Lesson", {"course": nom, "title": "01 · Module renommé"}))

    def test_inscrits_detectes(self):
        nom = self.depot.creer(self.p)
        self.assertFalse(self.depot.a_des_inscrits(nom))
        frappe.get_doc({"doctype": "LMS Enrollment", "course": nom, "member": "Administrator",
                        "member_type": "Student"}).insert(ignore_permissions=True)
        self.assertTrue(self.depot.a_des_inscrits(nom))

    def test_titres_au_maximum_acceptes_par_lms(self):
        p = parcours(title=TITRE, portfolio=tuple(projet(titre="T" * 120) for _ in range(10)))
        nom = self.depot.creer(p)
        self.assertEqual(compter(nom), (12, 12, 12))

    def test_unite_de_travail_valide_si_commit(self):
        with DepotFrappe(commit=True).unite_de_travail():
            frappe.db.set_default("openlab_academy_test", "1")
        frappe.db.rollback()
        try:
            self.assertEqual(frappe.db.get_default("openlab_academy_test"), "1")
        finally:
            frappe.db.set_default("openlab_academy_test", None)
            frappe.db.commit()

    def test_unite_de_travail_annule_en_cas_d_echec(self):
        with self.assertRaises(RuntimeError), self.depot.unite_de_travail():
            self.depot.creer(self.p)
            raise RuntimeError("boom")
        self.assertIsNone(self.depot.trouver(TITRE))

    def test_publication_bout_en_bout_et_isolation(self):
        refuse_par_lms = parcours(title="Parcours en échec", card_gradient="Arc-en-ciel")
        journal = []
        statuts = PublierParcours(self.depot, journal.append).executer([refuse_par_lms, self.p, self.p])
        self.assertEqual(statuts, {"Parcours en échec": Statut.ECHEC, TITRE: Statut.MAJ})
        self.assertIsNone(self.depot.trouver("Parcours en échec"))
        self.assertEqual(compter(self.depot.trouver(TITRE)), (12, 12, 12))


class TestCommandeSeed(FrappeTestCase):
    def tearDown(self):
        frappe.db.rollback()

    def test_run_depuis_un_dossier(self):
        brut = parcours_brut()
        brut["title"] = TITRE
        with tempfile.TemporaryDirectory() as d:
            pathlib.Path(d, "a.yaml").write_text(yaml.safe_dump(brut, allow_unicode=True), encoding="utf-8")
            self.assertEqual(seed.run(d, commit=False), {TITRE: "cree"})

    def test_echec_journalise(self):
        brut = parcours_brut()
        brut.update(title="Parcours en échec", card_gradient="Arc-en-ciel")
        with tempfile.TemporaryDirectory() as d:
            pathlib.Path(d, "a.yaml").write_text(yaml.safe_dump(brut, allow_unicode=True), encoding="utf-8")
            self.assertEqual(seed.run(d, commit=False), {"Parcours en échec": "echec"})
        self.assertTrue(frappe.db.exists("Error Log", {"method": "openlab_academy : publication des parcours"}))

    def test_run_parcours_livres(self):
        statuts = seed.run(commit=False)
        self.assertTrue(statuts)
        self.assertNotIn("echec", statuts.values())

    def test_commande_non_exposee_a_l_api(self):
        """OWASP A01 : le seed n'est pas appelable via /api/method."""
        with self.assertRaises(frappe.PermissionError):
            frappe.is_whitelisted(seed.run)
