"""Inscription à une cohorte : refus (cohorte close, parcours sans tarif), dossier aux prix figés, choix du mode."""
import datetime
import json
from unittest import mock

import frappe
from frappe.tests.utils import FrappeTestCase

from openlab_academy.application.paiements import ChoisirMode
from openlab_academy.domain.cohorte import Cohorte
from openlab_academy.domain.echeancier import Mode, Tarif, dixieme_suivant
from openlab_academy.domain.reglages import Reglages
from openlab_academy.infrastructure.depot_cohortes_frappe import DepotCohortesFrappe
from openlab_academy.infrastructure.depot_dossiers_frappe import DepotDossiersFrappe, ReglagesPaiementFrappe, TarifsFrappe
from openlab_academy.infrastructure.journal_paiement_frappe import journaliser
from openlab_academy.tests.fabriques import parcours
from openlab_academy.tests.sans_lancement import inscription_libre, sans_phase_de_lancement
from openlab_academy.tests.test_paiement_donnees_frappe import ELEVE, cours, tarif, utilisateur

DOSSIER = "Dossier Paiement OpenLab"
AUJOURDHUI = frappe.utils.getdate(frappe.utils.nowdate())


def cohorte(c, debut=None, rythme="standard"):
    debut = debut or AUJOURDHUI + datetime.timedelta(days=14)
    p = parcours(title=frappe.db.get_value("LMS Course", c, "title"))
    return DepotCohortesFrappe().creer(Cohorte.pilote(p, debut, Reglages().rythme(rythme), Reglages()))


def inscrire(lot, membre=ELEVE):
    with inscription_libre():
        return frappe.get_doc({"doctype": "LMS Batch Enrollment", "batch": lot, "member": membre}).insert(
            ignore_permissions=True)


def dossier_de(c, membre=ELEVE):
    return frappe.db.get_value(DOSSIER, {"apprenant": membre, "cours": c})


class Base(FrappeTestCase):
    def setUp(self):
        sans_phase_de_lancement(self)
        self.cours = cours("Parcours inscription paiement")
        utilisateur()

    def tearDown(self):
        frappe.db.rollback()


class TestInscription(Base):
    def test_inscription_ouvre_un_dossier_aux_prix_figes(self):
        tarif(self.cours).insert(ignore_permissions=True)
        lot = cohorte(self.cours)
        inscrire(lot)
        d = frappe.get_doc(DOSSIER, dossier_de(self.cours))
        self.assertEqual((d.cohorte, d.mode, d.dispense, d.cle), (lot, "une_fois", 0, f"{ELEVE}|{self.cours}"))
        self.assertEqual((d.frais_inscription, d.prix_une_fois, d.prix_deux_tranches, d.prix_mensuel),
                         (10000, 100000, 110000, 120000))
        self.assertEqual([(str(e.date_limite), e.montant, e.libelle) for e in d.echeances],
                         [(str(AUJOURDHUI), 10000, "Frais d'inscription"),
                          (str(dixieme_suivant(AUJOURDHUI, ReglagesPaiementFrappe().charger().jour_echeance)), 90000,
                           "Échéance")])
        self.assertEqual(str(d.date_inscription), str(AUJOURDHUI))

    def test_date_d_inscription_au_jour_du_site_et_non_a_l_horloge_du_conteneur(self):
        """Fuseau Abidjan : la date d'inscription (frais, premier 10, inscription tardive) vient du jour du site."""
        from openlab_academy.entrypoints import paiement
        tarif(self.cours).insert(ignore_permissions=True)
        lot = cohorte(self.cours)
        jour_du_site = AUJOURDHUI + datetime.timedelta(days=1)
        with mock.patch.object(paiement, "jour_courant", return_value=jour_du_site):
            inscrire(lot)
        d = frappe.get_doc(DOSSIER, dossier_de(self.cours))
        self.assertEqual(str(d.date_inscription), str(jour_du_site))
        self.assertEqual(str(d.echeances[0].date_limite), str(jour_du_site))

    def test_tarif_modifie_ensuite_sans_effet_sur_le_dossier(self):
        t = tarif(self.cours).insert(ignore_permissions=True)
        inscrire(cohorte(self.cours))
        t.prix_une_fois, t.prix_deux_tranches, t.prix_mensuel = 200000, 210000, 220000
        t.save(ignore_permissions=True)
        self.assertEqual(frappe.db.get_value(DOSSIER, dossier_de(self.cours), "prix_une_fois"), 100000)

    def test_inscription_apres_deux_mois_refusee(self):
        tarif(self.cours).insert(ignore_permissions=True)
        lot = cohorte(self.cours, AUJOURDHUI - datetime.timedelta(days=63))
        with self.assertRaisesRegex(frappe.ValidationError, "Les inscriptions à cette cohorte sont closes"):
            inscrire(lot)
        self.assertIsNone(dossier_de(self.cours))
        self.assertFalse(frappe.db.exists("LMS Batch Enrollment", {"batch": lot, "member": ELEVE}))

    def test_parcours_sans_tarif_inscription_refusee(self):
        with self.assertRaisesRegex(frappe.ValidationError, "pas encore de tarif : inscription impossible"):
            inscrire(cohorte(self.cours))

    def test_roles_non_bloques_sans_dossier_et_jamais_refuses(self):
        lot = cohorte(self.cours, AUJOURDHUI - datetime.timedelta(days=90))  # close ET sans tarif
        for role in ("System Manager", "Moderator", "Course Creator", "Batch Evaluator", "Intendant OpenLab"):
            email = f"{role.split()[0].lower()}.inscription@example.ci"
            frappe.get_doc({"doctype": "User", "email": email, "first_name": "X", "send_welcome_email": 0,
                            "roles": [{"role": role}]}).insert(ignore_permissions=True)
            with self.subTest(role=role):
                inscrire(lot, email)
                self.assertIsNone(dossier_de(self.cours, email))

    def test_cohorte_sans_parcours_ignoree(self):
        lot = cohorte(self.cours)
        frappe.db.delete("Batch Course", {"parent": lot})
        inscrire(lot)
        self.assertEqual(frappe.db.count(DOSSIER, {"apprenant": ELEVE}), 0)

    def test_reinscription_dans_une_autre_cohorte_du_meme_parcours_garde_le_dossier(self):
        tarif(self.cours).insert(ignore_permissions=True)
        premiere = cohorte(self.cours)
        inscrire(premiere)
        nom = dossier_de(self.cours)
        inscrire(cohorte(self.cours, rythme="intensif"))
        self.assertEqual(frappe.get_all(DOSSIER, {"apprenant": ELEVE}, pluck="name"), [nom])
        self.assertEqual(frappe.db.get_value(DOSSIER, nom, "cohorte"), premiere)

    def test_jour_et_delai_d_inscription_lus_dans_les_reglages(self):
        tarif(self.cours).insert(ignore_permissions=True)
        lot = cohorte(self.cours, AUJOURDHUI - datetime.timedelta(days=63))
        frappe.db.set_single_value("Reglages Paiement OpenLab", "inscription_tardive_mois", 3)
        inscrire(lot)
        self.assertTrue(dossier_de(self.cours))


class TestReglages(FrappeTestCase):
    def tearDown(self):
        frappe.db.rollback()

    def test_valeurs_par_defaut_quand_le_single_est_vide(self):
        frappe.db.delete("Singles", {"doctype": "Reglages Paiement OpenLab"})
        r = ReglagesPaiementFrappe().charger()
        self.assertEqual((r.jour_echeance, r.inscription_tardive_mois), (10, 2))

    def test_valeurs_reglees(self):
        frappe.db.set_single_value("Reglages Paiement OpenLab", {"jour_echeance": 5, "inscription_tardive_mois": 1})
        r = ReglagesPaiementFrappe().charger()
        self.assertEqual((r.jour_echeance, r.inscription_tardive_mois), (5, 1))

    def test_tarif_absent_puis_present(self):
        c = cours("Parcours tarifs lecture")
        self.assertIsNone(TarifsFrappe().charger(c))
        tarif(c).insert(ignore_permissions=True)
        self.assertEqual(TarifsFrappe().charger(c), Tarif(10000, 100000, 110000, 120000))


class TestChoixDuMode(Base):
    def setUp(self):
        super().setUp()
        tarif(self.cours).insert(ignore_permissions=True)
        self.lot = cohorte(self.cours)
        inscrire(self.lot)
        self.nom = dossier_de(self.cours)
        self.depot = DepotDossiersFrappe()

    def choisir(self, mode, telephone="+225 07 00 00 00 00"):
        return ChoisirMode(self.depot, journaliser, datetime.date.today).executer(ELEVE, self.cours, mode, telephone)

    def test_choix_mensuel_replanifie_et_journalise(self):
        echeances = self.choisir("mensuel")
        d = frappe.get_doc(DOSSIER, self.nom)
        self.assertEqual((d.mode, d.telephone), ("mensuel", "+2250700000000"))
        self.assertEqual([(e.date_limite, e.montant, e.libelle) for e in d.echeances],
                         [(e.date_limite, e.montant, e.libelle) for e in echeances])
        self.assertEqual(d.echeances[0].libelle, "Frais d'inscription")
        self.assertEqual(sum(e.montant for e in d.echeances), 120000)
        (ligne,) = frappe.get_all("Journal Paiement OpenLab", {"dossier": self.nom},
                                  ["acteur", "action", "avant", "apres"])
        self.assertEqual((ligne.acteur, ligne.action), (ELEVE, "mode"))
        self.assertEqual(json.loads(ligne.avant)["mode"], "une_fois")
        self.assertEqual(json.loads(ligne.apres)["mode"], "mensuel")

    def test_changement_apres_paiement_conserve_le_verse(self):
        frappe.get_doc({"doctype": "Paiement OpenLab", "dossier": self.nom, "montant": 10000, "moyen": "virement",
                        "reference": "V1", "statut": "confirme"}).insert(ignore_permissions=True)
        frappe.get_doc({"doctype": "Paiement OpenLab", "dossier": self.nom, "montant": 5000, "moyen": "virement",
                        "reference": "V2", "statut": "en_attente"}).insert(ignore_permissions=True)
        self.assertEqual(self.depot.paye(self.nom), 10000)
        self.choisir("deux_tranches")
        d = frappe.get_doc(DOSSIER, self.nom)
        self.assertEqual((d.echeances[0].libelle, d.echeances[0].montant), ("Déjà versé", 10000))
        self.assertEqual(sum(e.montant for e in d.echeances), 110000)

    def test_telephone_invalide_refuse(self):
        with self.assertRaisesRegex(ValueError, "Numéro de téléphone invalide"):
            self.choisir("mensuel", "0700000000")
        self.assertEqual(frappe.db.get_value(DOSSIER, self.nom, "mode"), "une_fois")

    def test_dossier_charge_avec_frais_et_paye_confirme(self):
        frappe.get_doc({"doctype": "Paiement OpenLab", "dossier": self.nom, "montant": 10000, "moyen": "virement",
                        "reference": "V1", "statut": "confirme"}).insert(ignore_permissions=True)
        d = self.depot.charger(ELEVE, self.cours)
        self.assertEqual((d.mode, d.telephone, d.dossier.paye, d.dossier.frais_inscription, d.dossier.dispense),
                         (Mode.UNE_FOIS, "", 10000, 10000, False))
        self.assertEqual((d.debut, d.fin), tuple(
            frappe.utils.getdate(v) for v in frappe.db.get_value("LMS Batch", self.lot, ["start_date", "end_date"])))
        self.assertEqual(d.inscription, AUJOURDHUI)
        self.assertIsNone(self.depot.charger("autre@example.ci", self.cours))

    def test_date_d_inscription_absente_repli_sur_la_creation(self):
        frappe.db.set_value(DOSSIER, self.nom, "date_inscription", None)
        self.assertEqual(self.depot.charger(ELEVE, self.cours).inscription, AUJOURDHUI)

    def test_delai_accorde(self):
        self.depot.fixer_delai(self.nom, datetime.date(2030, 1, 1))
        self.assertEqual(self.depot.charger(ELEVE, self.cours).dossier.delai_jusqu_au, datetime.date(2030, 1, 1))

