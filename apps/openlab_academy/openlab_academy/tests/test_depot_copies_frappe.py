"""Copies figées sur de vraies soumissions LMS : persistance, grilles d'exercice, cohorte, accès."""
import datetime
import json
from unittest import mock

import frappe
from frappe.tests.utils import FrappeTestCase

from openlab_academy import hooks
from openlab_academy.domain.cohorte import Cohorte
from openlab_academy.domain.copie import Proposition, Source, Statut
from openlab_academy.domain.grille import Grille
from openlab_academy.domain.parcours import Bloc
from openlab_academy.domain.reglages import Reglages
from openlab_academy.domain.reglages_evaluation import TypeExercice
from openlab_academy.entrypoints import evaluation
from openlab_academy.infrastructure import depot_copies_frappe
from openlab_academy.infrastructure.depot_cohortes_frappe import DepotCohortesFrappe
from openlab_academy.infrastructure.depot_copies_frappe import DepotCopiesFrappe
from openlab_academy.infrastructure.depot_frappe import DepotFrappe
from openlab_academy.infrastructure.instantane_provisoire import InstantaneProvisoire
from openlab_academy.tests.fabriques import parcours
from openlab_academy.tests.test_exercices_frappe import module

A = "eleve.a.copie@example.ci"
B = "eleve.b.copie@example.ci"
URL = "https://github.com/aya/livrable"


def utilisateur(email: str) -> None:
    if not frappe.db.exists("User", email):
        frappe.get_doc({"doctype": "User", "email": email, "first_name": "Eleve", "send_welcome_email": 0,
                        "roles": [{"role": "LMS Student"}]}).insert(ignore_permissions=True)


class Base(FrappeTestCase):
    def setUp(self):
        for email in (A, B):
            utilisateur(email)
        self.p = parcours(title="Parcours copies test", questions_par_quiz=5, blocs=(Bloc("B1", (module(),)),))
        self.cours = DepotFrappe(commit=False, reglages=Reglages()).creer(self.p)
        devoirs = frappe.get_all("LMS Assignment", {"course": self.cours}, ["name", "title"])
        self.cas = next(d.name for d in devoirs if d.title.startswith("Mise en situation"))
        self.livrable = next(d.name for d in devoirs if d.title.startswith("Livrable"))
        self.projet = next(d.name for d in devoirs if d.title.startswith("Projet 1 "))
        self.capstone = next(d.name for d in devoirs if d.title.startswith("Capstone"))
        self.depot = DepotCopiesFrappe()

    def tearDown(self):
        frappe.set_user("Administrator")
        frappe.db.rollback()

    def soumettre(self, devoir, membre=A, reponse=URL, **autres):
        return frappe.get_doc({"doctype": "LMS Assignment Submission", "assignment": devoir, "member": membre,
                               "answer": reponse, **autres}).insert(ignore_permissions=True)

    def copies(self, **filtres):
        return frappe.get_all("Copie OpenLab", filters=filtres, fields=["name", "version", "statut"], order_by="version")


class TestGrillesExercice(Base):
    def grille(self, devoir):
        return frappe.get_doc("Grille Exercice OpenLab", {"exercice": devoir})

    def test_type_decide_a_la_publication(self):
        self.assertEqual({d: self.grille(d).type_exercice for d in (self.cas, self.livrable, self.projet, self.capstone)},
                         {self.cas: "mise_en_situation", self.livrable: "livrable", self.projet: "projet",
                          self.capstone: "capstone"})

    def test_grilles_derivees_des_reglages(self):
        generique = Grille.depuis_dict(json.loads(self.grille(self.livrable).grille_json))
        self.assertEqual([c.libelle for c in generique.criteres][:2], ["Pertinence", "Rigueur"])
        projet_ = Grille.depuis_dict(json.loads(self.grille(self.projet).grille_json))
        self.assertEqual([c.libelle for c in projet_.criteres][0], "Fonctionnel")
        self.assertEqual(projet_.criteres[0].controles, ("a",))
        self.assertIn("Tests automatisés, couverture ≥ 70 %", projet_.criteres[1].controles)
        self.assertEqual(self.grille(self.livrable).chaine_yaml_json or "", "")

    def test_grille_et_chaine_du_yaml_figees(self):
        from openlab_academy.infrastructure.yaml_source import depuis_dict
        from openlab_academy.tests.fabriques import parcours_brut
        brut = parcours_brut()
        brut["title"] = "Parcours grille yaml"
        module_brut = brut["blocs"][0]["modules"][0]
        module_brut["grille_livrable"] = [{"code": "clarte", "libelle": "Clarté", "poids": 100,
                                           "niveaux": [{"libelle": "Faible"}, {"libelle": "Bon"}]}]
        module_brut["correction_livrable"] = {"etapes": [{"etape": "formateur", "active": True, "delai_heures": 9,
                                                          "expiration": "escalader"}]}
        cours = DepotFrappe(commit=False).creer(depuis_dict(brut, "t.yaml"))
        devoir = frappe.db.get_value("LMS Assignment", {"course": cours, "title": ["like", "Livrable%"]})
        ligne = self.grille(devoir)
        self.assertEqual([c["code"] for c in json.loads(ligne.grille_json)["criteres"]], ["clarte"])
        exercice = self.depot.exercice(devoir)
        self.assertEqual(exercice.chaine.config(exercice.chaine.etapes[-1].etape).delai_heures, 9)
        self.assertEqual(exercice.type_, TypeExercice.LIVRABLE)

    def test_exercice_inconnu(self):
        self.assertIsNone(self.depot.exercice("inexistant"))

    def test_republication_sans_copie_remplace_les_grilles(self):
        avant = frappe.db.count("Grille Exercice OpenLab")
        DepotFrappe(commit=False).remplacer(self.cours, self.p)
        self.assertEqual(frappe.db.count("Grille Exercice OpenLab"), avant)
        self.assertFalse(frappe.db.exists("Grille Exercice OpenLab", {"exercice": self.livrable}))

    def test_republication_ne_touche_pas_une_grille_ayant_des_copies(self):
        self.soumettre(self.livrable)
        avant = self.grille(self.livrable).grille_json
        depot_copies_frappe.enregistrer_grille_exercice(
            self.livrable, TypeExercice.PROJET, Grille.depuis_dict(json.loads(self.grille(self.projet).grille_json)), None)
        depot_copies_frappe.supprimer_grilles_sans_copie([self.livrable])
        ligne = self.grille(self.livrable)
        self.assertEqual((ligne.grille_json, ligne.type_exercice), (avant, "livrable"))

    def test_grille_sans_copie_mise_a_jour(self):
        grille = Grille.depuis_dict(json.loads(self.grille(self.projet).grille_json))
        depot_copies_frappe.enregistrer_grille_exercice(self.livrable, TypeExercice.PROJET, grille, None)
        self.assertEqual(self.grille(self.livrable).type_exercice, "projet")


class TestCopies(Base):
    def test_hooks(self):
        for evenement in ("after_insert", "on_update"):
            self.assertEqual(hooks.doc_events["LMS Assignment Submission"][evenement],
                             "openlab_academy.entrypoints.evaluation.rendu")

    def test_soumission_cree_une_copie_figee(self):
        s = self.soumettre(self.livrable)
        (ligne,) = self.copies()
        copie = frappe.get_doc("Copie OpenLab", ligne.name)
        self.assertEqual((copie.soumission, copie.apprenant, copie.exercice, copie.type_exercice, copie.version,
                          copie.statut), (s.name, A, self.livrable, "livrable", 1, "rendue"))
        grille = Grille.depuis_dict(json.loads(copie.grille_json))
        self.assertEqual(copie.empreinte, grille.empreinte())
        self.assertEqual((copie.contenu, copie.source_url, copie.commit), (URL, URL, ""))  # instantané provisoire
        self.assertEqual(copie.etape_courante, "auto_evaluation")
        self.assertIsNotNone(copie.echeance)

    def test_correction_du_formateur_ne_cree_pas_de_version(self):
        s = self.soumettre(self.livrable)
        s.status = "Pass"
        s.save(ignore_permissions=True)
        self.assertEqual(len(self.copies()), 1)

    def test_resoumission_cree_la_version_2(self):
        s = self.soumettre(self.livrable)
        (v1,) = self.copies()
        frappe.get_doc({"doctype": "Relecture Pair OpenLab", "copie": v1.name, "relecteur": B}).insert(
            ignore_permissions=True)
        self.depot.ajouter_proposition(v1.name, Proposition(Source.IA, "ia", {"clarte": 1}, confiance=0.9))
        s.answer = "https://github.com/aya/livrable-v2"
        s.save(ignore_permissions=True)
        v1_apres, v2 = self.copies()
        self.assertEqual((v1_apres.statut, v2.version, v2.statut), ("renvoyee", 2, "rendue"))
        self.assertEqual(frappe.db.get_value("Relecture Pair OpenLab", {"copie": v1.name}, "statut"), "annulée")
        self.assertEqual(self.depot.propositions(v2.name), [])
        (p,) = self.depot.propositions(v1.name)
        self.assertEqual((p.source, p.niveaux, p.confiance), (Source.IA, {"clarte": 1}, 0.9))
        self.assertEqual(self.depot.version_courante(s.name).id, v2.name)
        self.assertEqual(self.depot.copie(v2.name).statut, Statut.RENDUE)

    def test_exercice_hors_openlab_ignore(self):
        devoir = frappe.get_doc({"doctype": "LMS Assignment", "title": "Devoir libre", "question": "q",
                                 "type": "URL", "course": self.cours}).insert(ignore_permissions=True).name
        self.soumettre(devoir)
        self.assertEqual(self.copies(), [])

    def test_auto_evaluation_prealable_rattachee(self):
        frappe.get_doc({"doctype": "Auto Evaluation OpenLab", "apprenant": A, "exercice": self.livrable,
                        "niveaux_json": json.dumps({"pertinence": 2, "rigueur": 1})}).insert(ignore_permissions=True)
        self.soumettre(self.livrable)
        (ligne,) = self.copies()
        (p,) = self.depot.propositions(ligne.name)
        self.assertEqual((p.source, p.auteur, p.niveaux), (Source.AUTO_EVALUATION, A, {"pertinence": 2, "rigueur": 1}))

    def test_sans_auto_evaluation(self):
        self.assertIsNone(self.depot.auto_evaluation(A, self.livrable))

    def test_cohorte_du_lot_contenant_le_cours(self):
        self.assertIsNone(self.depot.cohorte(A, self.livrable))
        lot = DepotCohortesFrappe().creer(Cohorte.pilote(self.p, datetime.date(2026, 11, 2),
                                                         Reglages().rythme("standard"), Reglages()))
        self.assertIsNone(self.depot.cohorte(A, self.livrable))  # pas encore inscrit
        frappe.get_doc({"doctype": "LMS Batch Enrollment", "batch": lot, "member": A}).insert(ignore_permissions=True)
        self.assertEqual(self.depot.cohorte(A, self.livrable), lot)
        self.assertIsNone(self.depot.cohorte(B, self.livrable))
        self.soumettre(self.livrable)
        self.assertEqual(frappe.db.get_value("Copie OpenLab", {"apprenant": A}, "cohorte"), lot)

    def test_lot_sans_le_cours_ignore(self):
        DepotFrappe(commit=False).creer(parcours(title="Autre cours copies"))
        lot = DepotCohortesFrappe().creer(Cohorte.pilote(parcours(title="Autre cours copies"), datetime.date(2026, 11, 2),
                                                         Reglages().rythme("standard"), Reglages()))
        frappe.get_doc({"doctype": "LMS Batch Enrollment", "batch": lot, "member": A}).insert(ignore_permissions=True)
        self.assertIsNone(self.depot.cohorte(A, self.livrable))

    def test_apprenant_b_ne_lit_pas_la_copie_de_a(self):
        self.soumettre(self.livrable)
        nom = self.copies()[0].name
        frappe.set_user(B)
        with self.assertRaises(frappe.PermissionError):
            frappe.get_doc("Copie OpenLab", nom).check_permission("read")  # get_doc seul ne vérifie rien
        for doctype in ("Proposition OpenLab", "Relecture Pair OpenLab", "Grille Exercice OpenLab",
                        "Auto Evaluation OpenLab"):
            self.assertFalse(frappe.has_permission(doctype, "read"), doctype)
        frappe.set_user(A)
        self.assertFalse(frappe.has_permission("Copie OpenLab", "read", nom))

    def test_responsable_pedagogique_lit_sans_ecrire(self):
        self.soumettre(self.livrable)
        nom = self.copies()[0].name
        permissions = frappe.get_meta("Copie OpenLab").permissions
        responsable = [p for p in permissions if p.role == "Responsable pédagogique OpenLab"]
        self.assertEqual([(p.read, p.write, p.create) for p in responsable], [(1, 0, 0)])
        self.assertTrue(nom)


class TestRendu(Base):
    def test_erreur_interne_consignee_sans_bloquer_le_depot(self):
        with mock.patch.object(evaluation, "soumettre", side_effect=RuntimeError("panne")), \
                mock.patch.object(evaluation.frappe, "log_error") as journal:
            s = self.soumettre(self.livrable)
        self.assertTrue(s.name)
        journal.assert_called()
        self.assertEqual(self.copies(), [])

    def test_instantane_provisoire_garde_le_lien(self):
        self.assertEqual(InstantaneProvisoire().prendre(URL), (URL, ""))

    def test_soumettre_assemble_les_adaptateurs(self):
        s = self.soumettre(self.livrable)
        (ligne,) = self.copies()
        self.assertEqual(evaluation.soumettre({"name": s.name, "assignment": self.livrable, "member": A,
                                               "type": "URL", "answer": URL, "assignment_attachment": None}),
                         ligne.name)


class TestStatut(Base):
    def test_changer_statut(self):
        self.soumettre(self.livrable)
        nom = self.copies()[0].name
        echeance = datetime.datetime(2026, 12, 1, 10, 0)
        self.depot.changer_statut(nom, Statut.CONTROLEE, "ia", echeance)
        ligne = frappe.get_doc("Copie OpenLab", nom)
        self.assertEqual((ligne.statut, ligne.etape_courante, ligne.echeance), ("controlee", "ia", echeance))
