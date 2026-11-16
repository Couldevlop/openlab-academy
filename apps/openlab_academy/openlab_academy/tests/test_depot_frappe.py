import json
import pathlib
import tempfile
from unittest import mock

import frappe
import yaml
from frappe.tests.utils import FrappeTestCase

from openlab_academy.application.publier_parcours import PublierParcours, Statut
from openlab_academy.domain.parcours import Annonce, Bloc, Module, Niveau
from openlab_academy.entrypoints import install, seed
from openlab_academy.infrastructure import contenus_parcours_frappe as contenus
from openlab_academy.infrastructure import ressources_frappe
from openlab_academy.infrastructure.depot_frappe import DepotFrappe
from openlab_academy.tests.fabriques import parcours, parcours_brut, projet

TITRE = "Parcours de test seed"
ARCHIVE = "socle-ia-agentique-v0.3.0.zip"


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

    def test_remplacer_passe_par_les_documents(self):
        """Hooks du LMS joués (notes de leçon supprimées) et aucune ligne enfant orpheline."""
        nom = self.depot.creer(self.p)
        chapitres = frappe.get_all("Course Chapter", {"course": nom}, pluck="name")
        lecons = frappe.get_all("Course Lesson", {"course": nom}, pluck="name")
        quiz = frappe.get_all("LMS Quiz", {"course": nom}, pluck="name")
        frappe.get_doc({"doctype": "LMS Lesson Note", "lesson": lecons[0], "member": "Administrator",
                        "note": "n", "color": "Yellow"}).db_insert()
        self.depot.remplacer(nom, parcours(title=TITRE))
        self.assertEqual(frappe.db.count("LMS Lesson Note", {"lesson": lecons[0]}), 0)
        self.assertEqual(frappe.db.count("Lesson Reference", {"parent": ["in", chapitres]}), 0)
        self.assertEqual(frappe.db.count("LMS Lesson Assessment", {"parent": ["in", lecons]}), 0)
        if quiz:
            self.assertEqual(frappe.db.count("LMS Quiz Question", {"parent": ["in", quiz]}), 0)

    def test_drapeaux_publies(self):
        nom = self.depot.creer(parcours(title=TITRE, gratuit=True, acces_limite_a_la_cohorte=True, mise_en_avant=True))
        self.assertEqual(frappe.db.get_value("LMS Course", nom, ["parcours_gratuit", "acces_limite_cohorte", "featured"]),
                         (1, 1, 1))

    def test_drapeaux_absents_n_ecrasent_pas_l_administrateur(self):
        nom = self.depot.creer(self.p)
        frappe.db.set_value("LMS Course", nom, {"featured": 1, "parcours_gratuit": 1, "acces_limite_cohorte": 1})
        self.depot.remplacer(nom, self.p)
        self.assertEqual(frappe.db.get_value("LMS Course", nom, ["parcours_gratuit", "acces_limite_cohorte", "featured"]),
                         (1, 0, 1))

    def test_annonce_sans_drapeaux(self):
        nom = self.depot.creer(Annonce(TITRE, "s", "d", ("x",), "Blue"))
        self.assertEqual(frappe.db.get_value("LMS Course", nom, ["parcours_gratuit", "acces_limite_cohorte", "featured"]),
                         (0, 0, 0))

    def test_progression_sequentielle_publiee_et_republiee(self):
        """Le parcours quotidien verrouille ses leçons ; celui qui ne le demande pas les laisse libres."""
        nom = self.depot.creer(parcours(title=TITRE, progression_sequentielle=True))
        self.assertEqual(frappe.db.get_value("LMS Course", nom, "enforce_lesson_completion"), 1)
        self.depot.remplacer(nom, parcours(title=TITRE))
        self.assertEqual(frappe.db.get_value("LMS Course", nom, "enforce_lesson_completion"), 0)

    def test_completer_applique_la_progression_sequentielle(self):
        """Parcours à inscrits : le verrou suit aussi, sinon la promo en cours garderait l'ancien régime."""
        nom = self.depot.creer(self.p)
        self.depot.completer(nom, parcours(title=TITRE, progression_sequentielle=True))
        self.assertEqual(frappe.db.get_value("LMS Course", nom, "enforce_lesson_completion"), 1)

    def test_archive_jointe_en_fichier_prive_et_citee_par_la_lecon(self):
        """L'archive est un fichier privé attaché à la leçon : seul le contrôle des médias du LMS la sert, donc
        seul un membre dont le parcours est ouvert et la leçon accessible peut la télécharger."""
        module = Module("01", "Un", "c", "l", travaux_pratiques="Déroulé.", archive=ARCHIVE)
        nom = self.depot.creer(parcours(title=TITRE, blocs=(Bloc("B1", (module,)),)))
        la_lecon = lecon(nom, "01 ")
        fichier = frappe.get_doc("File", {"attached_to_doctype": "Course Lesson",
                                          "attached_to_name": la_lecon.name, "file_name": ARCHIVE})
        self.assertEqual((fichier.is_private, fichier.attached_to_field), (1, "content"))
        liens = [b["data"]["text"] for b in json.loads(la_lecon.content)["blocks"] if b["type"] == "paragraph"]
        self.assertIn(f'À télécharger : <a href="{fichier.file_url}">{ARCHIVE}</a>', liens)
        # cette leçon avoue l'archive, et aucune référence ne la réserve aux instructeurs : l'apprenant du
        # parcours ouvert y a droit. Les mêmes octets servent plusieurs parcours (le socle du parcours livré) :
        # les autres leçons qui la citent sont donc attendues, seule la réserve aux instructeurs est interdite.
        references = contenus.references_avouees(fichier.file_url)
        self.assertIn((la_lecon.name, False, nom), references)
        self.assertFalse([r for r in references if r[1]], references)

    def test_figure_du_guide_de_projet_jointe_a_la_lecon_et_citee(self):
        """Le guide de réalisation du projet final porte ses schémas comme une séance : fichiers privés
        attachés à la leçon, servis par le contrôle d'accès du LMS."""
        from openlab_academy.domain.parcours import Figure, Section
        figure = Figure("boucle-agent.svg", "La boucle d'un agent")
        cap = projet(titre="Cap", apres_module=None, niveau=Niveau.AUTONOME, duree_h=60,
                     cours=(Section("Cadrer", ("Écrire la mission.",), figures=(figure,)),))
        nom = self.depot.creer(parcours(title=TITRE, capstone=cap))
        la_lecon = lecon(nom, "Énoncé — Cap")
        fichier = frappe.get_doc("File", {"attached_to_doctype": "Course Lesson",
                                          "attached_to_name": la_lecon.name, "file_name": figure.nom})
        self.assertEqual((fichier.is_private, fichier.attached_to_field), (1, "content"))
        images = [b for b in json.loads(la_lecon.content)["blocks"] if b["type"] == "image"]
        self.assertEqual([b["data"]["url"] for b in images], [fichier.file_url])

    def test_archive_deja_jointe_reutilisee(self):
        """Une archive jointe deux fois à la même leçon ne crée pas un second fichier."""
        module = Module("01", "Un", "c", "l", travaux_pratiques="Déroulé.", archive=ARCHIVE)
        nom = self.depot.creer(parcours(title=TITRE, blocs=(Bloc("B1", (module,)),)))
        la_lecon = lecon(nom, "01 ")
        url = frappe.db.get_value("File", {"attached_to_name": la_lecon.name, "file_name": ARCHIVE}, "file_url")
        self.assertEqual(ressources_frappe.joindre(la_lecon.name, ARCHIVE), url)
        self.assertEqual(frappe.db.count("File", {"attached_to_name": la_lecon.name, "file_name": ARCHIVE}), 1)

    def test_archive_absente_des_ressources_refusee(self):
        """Échec fermé : aucune leçon ne cite une archive que l'application ne livre pas."""
        module = Module("01", "Un", "c", "l", travaux_pratiques="D", archive="inexistante.zip")
        with self.assertRaises(ressources_frappe.RessourceInconnue):
            self.depot.creer(parcours(title=TITRE, blocs=(Bloc("B1", (module,)),)))

    def test_video_preservee_a_la_republication(self):
        video = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        nom = self.depot.creer(self.p)
        avant = lecon(nom, "01 ·")
        frappe.db.set_value("Course Lesson", avant.name, "video_lecon", video)
        self.depot.remplacer(nom, self.p)
        apres = lecon(nom, "01 ·")
        self.assertNotEqual(apres.name, avant.name)
        self.assertEqual(apres.video_lecon, video)
        enonce = frappe.get_all("Course Lesson", {"course": nom, "title": ["like", "Énoncé%"]}, pluck="video_lecon")
        self.assertTrue(enonce and not any(enonce))

    def test_completer_applique_les_drapeaux(self):
        nom = self.depot.creer(self.p)
        frappe.get_doc({"doctype": "LMS Enrollment", "course": nom, "member": "Administrator",
                        "member_type": "Student"}).insert(ignore_permissions=True)
        lecons = sorted(frappe.get_all("Course Lesson", {"course": nom}, pluck="name"))
        self.depot.completer(nom, parcours(title=TITRE, gratuit=True, acces_limite_a_la_cohorte=True,
                                           mise_en_avant=True))
        self.assertEqual(frappe.db.get_value("LMS Course", nom, ["parcours_gratuit", "acces_limite_cohorte", "featured"]),
                         (1, 1, 1))
        self.assertEqual(sorted(frappe.get_all("Course Lesson", {"course": nom}, pluck="name")), lecons)

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


class TestPublicationConcurrente(FrappeTestCase):
    """Une tâche planifiée du LMS (statistiques horaires) enregistre tous les parcours et valide sa transaction
    pendant une republication. Transaction de la publication : instantané de lecture ancien, `modified` du parcours
    plus récent en base."""

    def setUp(self):
        self.depot = DepotFrappe(commit=True)
        self.p = parcours(title=TITRE)
        self.autre = parcours(title=TITRE + " bis")

    def tearDown(self):
        frappe.db.rollback()
        for titre in (TITRE, TITRE + " bis"):
            nom = frappe.db.get_value("LMS Course", {"title": titre})
            if nom:
                DepotFrappe._purger(nom)
                frappe.delete_doc("LMS Course", nom, force=True, ignore_permissions=True, delete_permanently=True)
        frappe.db.commit()

    @staticmethod
    def _tache_planifiee(*titres):
        """Autre connexion, transaction validée : touche `modified` des parcours, comme update_course_statistics."""
        from frappe.database import get_db

        autre = get_db(socket=frappe.conf.db_socket, host=frappe.conf.db_host, port=frappe.conf.db_port,
                       user=frappe.conf.db_name, password=frappe.conf.db_password, cur_db_name=frappe.conf.db_name)
        try:
            for titre in titres:
                autre.sql("update `tabLMS Course` set modified = %s where title = %s",
                          (frappe.utils.add_to_date(frappe.utils.now_datetime(), seconds=1), titre))
            autre.commit()
        finally:
            autre.close()

    def _publier(self, *lot):
        self.journal = []
        return PublierParcours(self.depot, self.journal.append).executer(lot)

    def test_tache_planifiee_pendant_la_republication(self):
        self.assertEqual(self._publier(self.p, self.autre), {TITRE: Statut.CREE, TITRE + " bis": Statut.CREE})
        purger = DepotFrappe._purger
        appels = []

        def purger_puis_tache(cours_id):
            purger(cours_id)
            if not appels:  # la tâche passe pendant le premier parcours seulement
                appels.append(cours_id)
                self._tache_planifiee(TITRE, TITRE + " bis")

        with mock.patch.object(DepotFrappe, "_purger", staticmethod(purger_puis_tache)):
            statuts = self._publier(self.p, self.autre)
        self.assertEqual(statuts, {TITRE: Statut.MAJ, TITRE + " bis": Statut.MAJ}, self.journal)
