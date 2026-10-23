"""Parcours gratuits (MOOC) sur Frappe : case du parcours, inscription sans tarif ni dossier, tarif refusé, accès,
« Mes paiements », intendance, et passage payant -> gratuit (dossiers dispensés, journalisés) puis gratuit -> payant."""
import datetime
import json

import frappe
from frappe.tests.utils import FrappeTestCase

from openlab_academy.entrypoints import install, lms, paiement
from openlab_academy.infrastructure.depot_dossiers_frappe import ParcoursGratuitsFrappe
from openlab_academy.infrastructure.rappels_frappe import DepotRappelsFrappe
from openlab_academy.application.ports_paiement import FiltresTableau
from openlab_academy.tests.test_paiement_api_frappe import INTENDANT, agent, appeler
from openlab_academy.tests.test_paiement_donnees_frappe import ELEVE, cours, tarif, utilisateur
from openlab_academy.tests.test_paiement_inscription_frappe import cohorte, dossier_de, inscrire

DOSSIER = "Dossier Paiement OpenLab"
JOURNAL = "Journal Paiement OpenLab"
AUJOURDHUI = datetime.date.today()
AUTRE = "autre.mooc@example.ci"


def rendre(c, gratuit=True):
    doc = frappe.get_doc("LMS Course", c)
    doc.parcours_gratuit = int(gratuit)
    doc.save(ignore_permissions=True)


class Base(FrappeTestCase):
    def setUp(self):
        utilisateur()
        lms.vider_cache()

    def tearDown(self):
        frappe.db.rollback()
        frappe.set_user("Administrator")
        lms.vider_cache()


class TestCase(Base):
    def tearDown(self):
        """Les champs personnalisés passent par du DDL, qui valide la transaction : la case et ses droits sont
        remis en place pour les tests suivants."""
        super().tearDown()
        install.preparer_parcours_gratuits()
        frappe.db.commit()

    def test_case_du_formulaire_des_parcours_et_idempotence(self):
        frappe.db.delete("Custom Field", {"dt": "LMS Course", "fieldname": "parcours_gratuit"})
        install.preparer_parcours_gratuits()
        install.preparer_parcours_gratuits()
        (champ,) = frappe.get_all("Custom Field", {"dt": "LMS Course", "fieldname": "parcours_gratuit"},
                                  ["fieldtype", "label", "description", "insert_after", "permlevel"])
        self.assertEqual((champ.fieldtype, champ.label, champ.insert_after, champ.permlevel),
                         ("Check", "Parcours gratuit (MOOC)", "pricing_section", 1))
        self.assertEqual(champ.description, "Aucun paiement : ni tarif, ni échéancier, ni rappel, ni blocage.")
        regles = frappe.get_all("Custom DocPerm", {"parent": "LMS Course", "permlevel": 1}, ["role", "read", "write"])
        self.assertEqual([(r.role, r.read, r.write) for r in regles], [("System Manager", 1, 1)])

    def test_site_existant_case_passee_au_niveau_administrateur(self):
        nom = frappe.db.get_value("Custom Field", {"dt": "LMS Course", "fieldname": "parcours_gratuit"})
        frappe.db.set_value("Custom Field", nom, {"permlevel": 0, "label": "Ancien libellé"})
        frappe.db.delete("Custom DocPerm", {"parent": "LMS Course", "permlevel": 1})
        install.preparer_parcours_gratuits()
        self.assertEqual(frappe.db.get_value("Custom Field", nom, ["permlevel", "label"]),
                         (1, "Parcours gratuit (MOOC)"))
        self.assertTrue(frappe.db.exists("Custom DocPerm", {"parent": "LMS Course", "role": "System Manager",
                                                            "permlevel": 1, "write": 1}))

    def test_createur_et_moderateur_ne_peuvent_pas_cocher_la_case(self):
        c = cours("Parcours du créateur")
        for role in ("Course Creator", "Moderator"):
            email = agent(f"{role.split()[0].lower()}.mooc@example.ci", role)
            proprio = frappe.get_doc("LMS Course", c)  # le créateur n'écrit que ses parcours : il en est formateur
            proprio.append("instructors", {"instructor": email})
            proprio.save(ignore_permissions=True)
            frappe.set_user(email)
            try:
                with self.subTest(role=role):
                    doc = frappe.get_doc("LMS Course", c)
                    doc.parcours_gratuit = 1
                    doc.save()
                    self.assertEqual(frappe.db.get_value("LMS Course", c, "parcours_gratuit"), 0)
            finally:
                frappe.set_user("Administrator")

    def test_lecture_du_statut(self):
        c = cours("MOOC lecture du statut")
        self.assertFalse(ParcoursGratuitsFrappe().gratuit(c))
        rendre(c)
        self.assertTrue(ParcoursGratuitsFrappe().gratuit(c))
        self.assertFalse(ParcoursGratuitsFrappe().gratuit("parcours-inconnu"))


class TestInscription(Base):
    def setUp(self):
        super().setUp()
        self.cours = cours("MOOC inscription libre")
        rendre(self.cours)

    def test_inscription_sans_tarif_ni_dossier_ni_blocage(self):
        lot = cohorte(self.cours)
        inscrire(lot)
        self.assertTrue(frappe.db.exists("LMS Batch Enrollment", {"batch": lot, "member": ELEVE}))
        self.assertIsNone(dossier_de(self.cours))
        self.assertFalse(lms.bloque_pour(ELEVE, self.cours))

    def test_limite_d_inscription_tardive_aussi_pour_un_mooc(self):
        lot = cohorte(self.cours, AUJOURDHUI - datetime.timedelta(days=63))
        with self.assertRaisesRegex(frappe.ValidationError, "Les inscriptions à cette cohorte sont closes"):
            inscrire(lot)

    def test_parcours_payant_sans_tarif_toujours_refuse(self):
        payant = cours("Parcours payant oublié")
        with self.assertRaisesRegex(frappe.ValidationError, "pas encore de tarif : inscription impossible"):
            inscrire(cohorte(payant))

    def test_tarif_refuse_avec_message_clair(self):
        with self.assertRaisesRegex(frappe.ValidationError, "Ce parcours est gratuit \\(MOOC\\)"):
            tarif(self.cours).insert(ignore_permissions=True)
        self.assertFalse(frappe.db.exists("Tarif Parcours OpenLab", self.cours))

    def test_mes_paiements_etat_calme(self):
        inscrire(cohorte(self.cours))
        self.assertEqual(appeler("mon_dossier", ELEVE, cours=self.cours),
                         {"cours": self.cours, "titre": "MOOC inscription libre", "gratuit": True})

    def test_mes_paiements_d_un_mooc_non_suivi_comme_un_parcours_inconnu(self):
        with self.assertRaises(frappe.DoesNotExistError):
            appeler("mon_dossier", ELEVE, cours=self.cours)

    def test_inscription_en_autonomie_vaut_inscription(self):
        frappe.get_doc({"doctype": "LMS Enrollment", "course": self.cours, "member": ELEVE}).insert(
            ignore_permissions=True)
        self.assertTrue(appeler("mon_dossier", ELEVE, cours=self.cours)["gratuit"])

    def test_absent_de_l_intendance(self):
        inscrire(cohorte(self.cours))
        lignes = paiement.intendance(FiltresTableau(), None)["lignes"]
        self.assertNotIn(self.cours, {x["parcours"] for x in lignes})
        self.assertNotIn(self.cours, {x["parcours"] for x in
                                      paiement.intendance(FiltresTableau(parcours=self.cours), None)["lignes"]})


class TestPassage(Base):
    """Parcours payant avec deux inscrits (frais du jour impayés : bloqués), puis rendu gratuit."""

    def setUp(self):
        super().setUp()
        self.cours = cours("Parcours devenu MOOC")
        tarif(self.cours).insert(ignore_permissions=True)
        self.lot = cohorte(self.cours)
        for email in (ELEVE, utilisateur(AUTRE)):
            inscrire(self.lot, email)
        self.noms = [dossier_de(self.cours), dossier_de(self.cours, AUTRE)]
        self.intendant = agent(INTENDANT, "Intendant OpenLab")

    def test_dossiers_dispenses_journalises_ni_bloques_ni_rappeles(self):
        self.assertTrue(lms.bloque_pour(ELEVE, self.cours))
        lms.vider_cache()
        rendre(self.cours)
        self.assertEqual([frappe.db.get_value(DOSSIER, n, "dispense") for n in self.noms], [1, 1])
        lignes = frappe.get_all(JOURNAL, {"dossier": ("in", self.noms)}, ["dossier", "acteur", "action", "motif",
                                                                           "avant", "apres", "horodatage"])
        self.assertEqual(sorted(x.dossier for x in lignes), sorted(self.noms))
        for x in lignes:
            self.assertEqual((x.acteur, x.action, x.motif),
                             ("Administrator", "dispense_parcours_gratuit", "parcours devenu gratuit"))
            self.assertEqual(json.loads(x.avant), {"statut": "en_retard", "paye": 0})
            self.assertEqual(json.loads(x.apres), {"statut": "dispense", "paye": 0})
            self.assertTrue(x.horodatage)
        self.assertFalse(lms.bloque_pour(ELEVE, self.cours))
        self.assertFalse(set(self.noms) & set(DepotRappelsFrappe().noms()))
        # toujours visibles, dispensés, dans l'historique de l'intendance
        lignes = paiement.intendance(FiltresTableau(parcours=self.cours), None)["lignes"]
        self.assertEqual({(x["dossier"], x["statut"], x["bloque"]) for x in lignes},
                         {(n, "dispense", False) for n in self.noms})
        self.assertEqual(appeler("mon_dossier", ELEVE, cours=self.cours)["gratuit"], True)

    def test_rejeu_de_l_enregistrement_sans_nouvelle_ligne(self):
        rendre(self.cours)
        rendre(self.cours)
        self.assertEqual(frappe.db.count(JOURNAL, {"dossier": ("in", self.noms)}), 2)

    def test_auteur_journalise_est_la_session(self):
        admin = agent("admin.mooc@example.ci", "System Manager")
        frappe.db.set_value("LMS Course", self.cours, "parcours_gratuit", 1)
        frappe.set_user(admin)
        try:
            paiement.parcours_enregistre(frappe._dict(name=self.cours))
        finally:
            frappe.set_user("Administrator")
        self.assertEqual(set(frappe.get_all(JOURNAL, {"dossier": ("in", self.noms)}, pluck="acteur")), {admin})

    def test_dispense_refusee_hors_administrateur(self):
        """Défense en profondeur : même si la case arrive cochée (API, éditeur du LMS, code), un enregistrement par
        un autre que l'administrateur ne dispense rien et échoue."""
        frappe.db.set_value("LMS Course", self.cours, "parcours_gratuit", 1)
        for utilisateur_ in (self.intendant, agent("createur.dispense@example.ci", "Course Creator")):
            frappe.set_user(utilisateur_)
            try:
                with self.subTest(utilisateur=utilisateur_), self.assertRaisesRegex(
                        frappe.PermissionError, "Seul l'administrateur"):
                    paiement.parcours_enregistre(frappe._dict(name=self.cours))
            finally:
                frappe.set_user("Administrator")
        self.assertEqual([frappe.db.get_value(DOSSIER, n, "dispense") for n in self.noms], [0, 0])
        self.assertEqual(frappe.db.count(JOURNAL, {"dossier": ("in", self.noms)}), 0)

    def test_dossier_solde_reste_solde(self):
        frappe.get_doc({"doctype": "Paiement OpenLab", "dossier": self.noms[0], "montant": 100000,
                        "moyen": "virement", "reference": "VIR-MOOC-SOLDE", "statut": "confirme"}
                       ).insert(ignore_permissions=True)
        rendre(self.cours)
        self.assertEqual([frappe.db.get_value(DOSSIER, n, "dispense") for n in self.noms], [0, 1])
        self.assertEqual(frappe.get_all(JOURNAL, {"dossier": ("in", self.noms)}, pluck="dossier"), [self.noms[1]])
        lignes = paiement.intendance(FiltresTableau(parcours=self.cours), None)["lignes"]
        self.assertEqual({x["dossier"]: x["statut"] for x in lignes}, {self.noms[0]: "solde", self.noms[1]: "dispense"})

    def test_auteur_prevenu_dispense_et_tarif_ignore(self):
        frappe.local.message_log = []
        rendre(self.cours)
        messages = " ".join(json.loads(m).get("message", "") if isinstance(m, str) else m.get("message", "")
                            for m in frappe.local.message_log)
        self.assertIn("2 dossier(s) de paiement dispensé(s)", messages)
        self.assertIn("Le tarif de ce parcours est conservé mais ne s'applique plus", messages)

    def test_enregistrement_d_un_parcours_payant_sans_effet(self):
        doc = frappe.get_doc("LMS Course", self.cours)
        doc.short_introduction = "Nouvelle accroche"
        doc.save(ignore_permissions=True)
        self.assertEqual([frappe.db.get_value(DOSSIER, n, "dispense") for n in self.noms], [0, 0])
        self.assertEqual(frappe.db.count(JOURNAL, {"dossier": ("in", self.noms)}), 0)

    def test_redevenu_payant_pour_les_nouveaux_inscrits_seulement(self):
        rendre(self.cours)
        rendre(self.cours, gratuit=False)
        nouveau = utilisateur("nouveau.mooc@example.ci")
        inscrire(self.lot, nouveau)
        self.assertEqual([frappe.db.get_value(DOSSIER, n, "dispense") for n in self.noms], [1, 1])
        self.assertEqual(frappe.db.get_value(DOSSIER, dossier_de(self.cours, nouveau), "dispense"), 0)
        self.assertEqual(appeler("mon_dossier", ELEVE, cours=self.cours)["statut"], "dispense")
