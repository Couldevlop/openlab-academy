import datetime
from unittest import mock

import frappe
from frappe.tests.utils import FrappeTestCase

from openlab_academy.domain.fenetre import un_mois_apres
from openlab_academy.domain.reglages import TITRE_LANCEMENT
from openlab_academy.entrypoints import cohorte as commande
from openlab_academy.entrypoints import install
from openlab_academy.infrastructure import reglages_frappe
from openlab_academy.tests.test_cohorte_frappe import supprimer_cohortes

REGLAGES = "Reglages OpenLab Academy"
FONDAMENTAUX = "Fondamentaux de la Data Science"
TITRE_FENETRE = f"Promo 1 — {TITRE_LANCEMENT}"


class TestReglages(FrappeTestCase):
    def tearDown(self):
        frappe.db.rollback()

    def test_plateforme_en_francais_fcfa_abidjan(self):
        reglages_frappe.appliquer()
        s = frappe.get_single("System Settings")
        self.assertEqual((s.language, s.time_zone, s.currency, s.date_format),
                         ("fr", "Africa/Abidjan", "XOF", "dd-mm-yyyy"))
        self.assertEqual(frappe.db.get_single_value("LMS Settings", "default_currency"), "XOF")
        w = frappe.get_single("Website Settings")
        self.assertEqual((w.app_name, w.app_logo), ("OpenLab Academy", "/assets/openlab_academy/images/logo.svg"))

    def test_devise_xof_sans_decimales(self):
        frappe.db.delete("Currency", {"name": "XOF"})
        reglages_frappe.appliquer()
        xof = frappe.get_doc("Currency", "XOF")
        self.assertEqual((xof.enabled, xof.symbol, xof.fraction_units), (1, "FCFA", 0))

    def test_idempotent(self):
        reglages_frappe.appliquer()
        reglages_frappe.appliquer()
        self.assertEqual(frappe.db.count("Currency", {"name": "XOF"}), 1)


def sans_publication():
    """Hook exerce sans republier le catalogue.

    `seed.run` republie les huit parcours, soit plus de mille sections : deux minutes par appel depuis que le
    parcours Python a ete reecrit. Les tests qui verifient l'orchestration du hook — champs personnalises, fin de
    l'assistant, choix de l'administrateur, passage au parcours de lancement — n'ont pas besoin de ce travail :
    le site de test est deja peuple par l'installation. Ils remplacent donc la publication par un mouchard et
    verifient qu'elle est bien demandee. La publication elle-meme reste couverte, sur le vrai catalogue, par
    test_after_install_configure_et_publie et test_after_migrate_republie_les_parcours.
    """
    return mock.patch.object(install.seed, "run", return_value={})


class TestInstallation(FrappeTestCase):
    def setUp(self):
        frappe.db.set_single_value(REGLAGES, "ouverture_lancement", None)  # indépendant de l'état du banc

    def tearDown(self):
        frappe.db.rollback()

    def test_after_install_configure_et_publie(self):
        frappe.db.set_single_value(REGLAGES, "lancement_initialise", 0)
        supprimer_cohortes({"title": TITRE_FENETRE})
        install.after_install(commit=False)
        self.assertEqual(frappe.db.get_single_value("System Settings", "language"), "fr")
        self.assertTrue(frappe.db.exists("LMS Course", {"title": TITRE_LANCEMENT}))
        lot = frappe.get_doc("LMS Batch", {"title": TITRE_FENETRE})
        aujourd_hui = datetime.date.today()
        self.assertEqual((lot.start_date, lot.end_date), (aujourd_hui, un_mois_apres(aujourd_hui)))
        self.assertEqual(frappe.db.get_single_value(REGLAGES, "lancement_initialise"), 1)

    def test_sans_cours_de_lancement_aucune_ligne_de_parcours(self):
        """Jamais de ligne `cours=None` dans les parcours visibles pendant le lancement."""
        frappe.db.set_single_value(REGLAGES, "lancement_initialise", 0)
        frappe.db.set_value("LMS Course", {"title": TITRE_LANCEMENT}, "title", "Titre écarté")
        with mock.patch.object(install.cohorte, "ouvrir_pilote"):
            install.preparer_lancement(commit=False)
        self.assertEqual(frappe.get_single(REGLAGES).get("parcours_lancement"), [])

    def test_migration_site_existant(self):
        """Un site déjà installé, réglé sur l'ancien parcours pilote, passe au parcours de lancement."""
        with sans_publication():
            install.after_migrate(commit=False)
        frappe.db.set_single_value(REGLAGES, "parcours_pilote", FONDAMENTAUX)
        commande.ouvrir_pilote(commit=False)
        supprimer_cohortes({"title": TITRE_FENETRE})
        doc = frappe.get_doc(REGLAGES)
        doc.phase_lancement = 0
        doc.set("parcours_lancement", [])
        doc.lancement_initialise = 0
        doc.save(ignore_permissions=True)
        avant = frappe.get_all("LMS Batch", {"title": ("like", f"Promo 1 — {FONDAMENTAUX}%")},
                               ["name", "start_date", "end_date"])
        self.assertTrue(avant)
        with sans_publication() as publication:
            install.after_migrate(commit=False)
        publication.assert_called_once()
        doc = frappe.get_doc(REGLAGES)
        self.assertEqual(doc.parcours_pilote, TITRE_LANCEMENT)
        self.assertEqual(doc.phase_lancement, 1)
        self.assertEqual([l.cours for l in doc.parcours_lancement],
                         [frappe.db.get_value("LMS Course", {"title": TITRE_LANCEMENT})])
        self.assertEqual(doc.lancement_initialise, 1)
        self.assertTrue(frappe.db.exists("LMS Batch", {"title": TITRE_FENETRE}))
        apres = frappe.get_all("LMS Batch", {"title": ("like", f"Promo 1 — {FONDAMENTAUX}%")},
                               ["name", "start_date", "end_date"])
        self.assertEqual(apres, avant)

    def test_choix_de_l_administrateur_conserve(self):
        """Une fois le lancement initialisé, une migration ne remet rien en cause."""
        with sans_publication():
            install.after_migrate(commit=False)
        doc = frappe.get_doc(REGLAGES)
        doc.phase_lancement = 0
        doc.parcours_pilote = FONDAMENTAUX
        doc.set("parcours_lancement", [])
        doc.lancement_initialise = 1
        doc.save(ignore_permissions=True)
        with sans_publication():
            install.after_migrate(commit=False)
        doc = frappe.get_doc(REGLAGES)
        self.assertEqual((doc.phase_lancement, doc.parcours_pilote, len(doc.parcours_lancement)),
                         (0, FONDAMENTAUX, 0))

    def test_after_migrate_republie_les_parcours(self):
        self.assertIn("openlab_academy.entrypoints.install.after_migrate", frappe.get_hooks("after_migrate"))
        frappe.db.set_value("LMS Course", {"title": "AI Engineer"}, "short_introduction", "périmé")
        install.after_migrate(commit=False)
        self.assertNotEqual(frappe.db.get_value("LMS Course", {"title": "AI Engineer"}, "short_introduction"),
                            "périmé")

    def test_after_migrate_termine_l_assistant_d_installation(self):
        """Un site déjà installé reçoit aussi les réglages : sinon le bureau /app reste sur l'assistant, sans barre."""
        frappe.db.set_value("Installed Application", {"app_name": "lms"}, "is_setup_complete", 0)
        frappe.db.set_default("desktop:home_page", "setup-wizard")
        with sans_publication():
            install.after_migrate(commit=False)
        self.assertEqual(frappe.db.get_value("Installed Application", {"app_name": "lms"}, "is_setup_complete"), 1)
        self.assertEqual(frappe.db.get_default("desktop:home_page"), "workspace")

    def test_installation_non_exposee_a_l_api(self):
        """OWASP A01 : aucune fonction d'installation n'est appelable via /api/method."""
        for fonction in (install.after_install, install.after_migrate, reglages_frappe.appliquer):
            with self.subTest(fonction=fonction.__name__), self.assertRaises(frappe.PermissionError):
                frappe.is_whitelisted(fonction)


class TestChampsLancement(FrappeTestCase):
    def tearDown(self):
        frappe.db.rollback()
        install.preparer_champs_lancement()
        frappe.db.commit()

    def test_champs_de_lancement_crees(self):
        frappe.db.delete("Custom Field", {"fieldname": ["in", ["acces_limite_cohorte", "video_lecon",
                                                               "delai_exercices_minutes"]]})
        install.preparer_champs_lancement()
        install.preparer_champs_lancement()
        (limite,) = frappe.get_all("Custom Field", {"dt": "LMS Course", "fieldname": "acces_limite_cohorte"},
                                   ["fieldtype", "label", "permlevel"])
        self.assertEqual((limite.fieldtype, limite.label, limite.permlevel),
                         ("Check", "Accès limité aux dates de la cohorte", 1))
        (video,) = frappe.get_all("Custom Field", {"dt": "Course Lesson", "fieldname": "video_lecon"},
                                  ["fieldtype", "label", "description", "insert_after"])
        self.assertEqual((video.fieldtype, video.label, video.description, video.insert_after),
                         ("Attach", "Vidéo de la leçon",
                          "Lien YouTube, Vimeo ou fichier vidéo ; affichée en tête de la leçon.", "title"))
        (delai,) = frappe.get_all("Custom Field", {"dt": "LMS Course", "fieldname": "delai_exercices_minutes"},
                                  ["fieldtype", "label", "permlevel"])
        self.assertEqual((delai.fieldtype, delai.label, delai.permlevel),
                         ("Int", "Délai avant les exercices (minutes)", 1))

    def test_champs_remis_a_jour_et_appel_a_l_installation(self):
        nom = frappe.db.get_value("Custom Field", {"dt": "LMS Course", "fieldname": "acces_limite_cohorte"})
        frappe.db.set_value("Custom Field", nom, {"permlevel": 0, "label": "Ancien"})
        install.preparer_champs_lancement()
        self.assertEqual(frappe.db.get_value("Custom Field", nom, ["permlevel", "label"]),
                         (1, "Accès limité aux dates de la cohorte"))
        for fonction in (install.after_install, install.after_migrate):
            frappe.db.delete("Custom Field", {"fieldname": "video_lecon"})
            with sans_publication() as publication:
                fonction(commit=False)
            publication.assert_called_once()
            self.assertTrue(frappe.db.exists("Custom Field", {"dt": "Course Lesson", "fieldname": "video_lecon"}))
