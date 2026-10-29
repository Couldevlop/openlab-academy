"""Les points d'entrée appliquent ce qui est réglé dans l'écran « Reglages OpenLab Academy »."""
import json
import pathlib
import tempfile

import frappe
import yaml
from frappe.tests.utils import FrappeTestCase

from openlab_academy.domain.reglages import TITRE_LANCEMENT
from openlab_academy.entrypoints import cohorte, seed
from openlab_academy.infrastructure import reglages_frappe, reglages_source_frappe
from openlab_academy.tests.fabriques import parcours_brut
from openlab_academy.tests.test_cohorte_frappe import supprimer_cohortes

TITRE = "Parcours réglages test"


def regler(**valeurs):
    """Repart des réglages par défaut (la base de dev peut contenir des réglages modifiés) puis applique."""
    doc = frappe.get_single("Reglages OpenLab Academy")
    doc.set("rythmes", [])
    doc.flags.ignore_validate = True
    doc.save(ignore_permissions=True)
    reglages_source_frappe.initialiser()
    doc = frappe.get_single("Reglages OpenLab Academy")
    rythmes = valeurs.pop("rythmes", [])
    doc.update(valeurs)
    for r in rythmes:
        doc.append("rythmes", r)
    doc.save(ignore_permissions=True)


class TestBranchementReglages(FrappeTestCase):
    def tearDown(self):
        frappe.db.rollback()

    def _publier(self, brut):
        with tempfile.TemporaryDirectory() as d:
            pathlib.Path(d, "a.yaml").write_text(yaml.safe_dump(brut, allow_unicode=True), encoding="utf-8")
            return seed.run(d, commit=False)

    def test_publication_utilise_les_reglages(self):
        regler(heures_par_module=6, formateur="Administrator")
        doc = frappe.get_single("Reglages OpenLab Academy")
        doc.bareme[0].nom, doc.bareme[0].poids, doc.bareme[1].poids = "Démo", 50, 15
        doc.set("exigences", [{"texte": "Exigence maison"}])
        doc.save(ignore_permissions=True)
        brut = parcours_brut()
        brut["title"] = TITRE
        self.assertEqual(self._publier(brut), {TITRE: "cree"})
        cours = frappe.db.get_value("LMS Course", {"title": TITRE})
        module = frappe.get_doc("Course Lesson", {"course": cours, "title": ["like", "01 ·%"]})
        projet = frappe.get_doc("Course Lesson", {"course": cours, "title": ["like", "Énoncé —%"]})
        self.assertIn("~6 h", module.content)
        contenu = json.dumps(json.loads(projet.content), ensure_ascii=False)
        self.assertIn("Exigence maison", contenu)
        self.assertIn("Démo : 50 %", contenu)

    def test_nombre_de_projets_regle(self):
        regler(projets_par_portfolio=3)
        brut = parcours_brut()
        brut["title"] = TITRE
        brut["portfolio"] = brut["portfolio"][:3]
        self.assertEqual(self._publier(brut), {TITRE: "cree"})

    def test_cohorte_avec_un_rythme_ajoute_dans_l_ecran(self):
        regler(rythmes=[{"code": "week-end", "libelle": "Week-end", "samedi": 5, "dimanche": 5}])
        seed.run(commit=False)
        resultat = cohorte.ouvrir_pilote(rythme="week-end", commit=False)
        b = frappe.get_doc("LMS Batch", resultat["cohorte"])
        self.assertTrue(b.title.endswith("· Week-end 10 h"))
        self.assertIn("5 h les samedi et dimanche", b.batch_details)

    def test_horaires_de_seance_regles(self):
        regler(heure_debut="19:00:00", heure_fin="21:00:00")
        seed.run(commit=False)
        supprimer_cohortes({"title": ["like", f"Promo 1 — {TITRE_LANCEMENT}%"]})
        b = frappe.get_doc("LMS Batch", cohorte.ouvrir_pilote(commit=False)["cohorte"])
        self.assertEqual((str(b.start_time), str(b.end_time)), ("19:00:00", "21:00:00"))

    def test_parcours_pilote_absent_message_explicite(self):
        regler(parcours_pilote="Parcours inexistant")
        with self.assertRaisesRegex(ValueError, "parcours pilote « Parcours inexistant » introuvable"):
            cohorte.ouvrir_pilote(commit=False)

    def test_autre_devise(self):
        regler(devise="EUR")
        reglages_frappe.appliquer()
        self.assertEqual(frappe.db.get_single_value("System Settings", "currency"), "EUR")
        self.assertEqual(frappe.db.get_value("Currency", "EUR", "enabled"), 1)

    def test_assistant_d_installation_marque_termine(self):
        """Langue, fuseau et devise sont réglés ici : l'assistant Frappe ne doit plus bloquer le bureau (/app)."""
        for app in frappe.get_all("Installed Application", pluck="name"):
            frappe.db.set_value("Installed Application", app, "is_setup_complete", 0)
        frappe.db.set_single_value("System Settings", "setup_complete", 0)
        reglages_frappe.appliquer()
        self.assertEqual(set(frappe.get_all("Installed Application", pluck="is_setup_complete")), {1})
        self.assertEqual(frappe.db.get_single_value("System Settings", "setup_complete"), 1)

    def test_logo_de_la_barre_laterale_du_lms(self):
        """Le LMS affiche Website Settings.banner_image, résolu par une fiche File ; sans elle, son logo par défaut."""
        from lms.lms.api import get_branding

        frappe.db.set_single_value("Website Settings", "banner_image", "")
        reglages_frappe.appliquer()
        reglages_frappe.appliquer()  # idempotent : une seule fiche File
        url = frappe.db.get_single_value("Website Settings", "banner_image")
        self.assertEqual(frappe.db.count("File", {"file_url": url}), 1)
        self.assertEqual(get_branding().banner_image["file_url"], url)

    def test_marque_de_la_plateforme_reglee(self):
        regler(nom_plateforme="Académie Test", devise="XOF", langue="fr")
        reglages_frappe.appliquer()
        self.assertEqual(frappe.db.get_single_value("Website Settings", "app_name"), "Académie Test")
