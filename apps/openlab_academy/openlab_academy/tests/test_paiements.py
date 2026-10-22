"""Cas d'usage du paiement : ouverture du dossier à l'inscription, choix et changement de mode (faux ports)."""
import unittest
from dataclasses import replace
from datetime import date

from openlab_academy.application.paiements import (
    ChoisirMode, DossierAbsent, InscriptionTardive, OuvrirDossier, TarifAbsent, TelephoneInvalide, valider_telephone)
from openlab_academy.application.ports_paiement import DossierEnregistre, ReglagesPaiement
from openlab_academy.domain.dossier_paiement import Dossier
from openlab_academy.domain.echeancier import Echeance, Mode, Tarif, TarifInvalide

TARIF = Tarif(10000, 100000, 110000, 120000)
DEBUT, FIN = date(2026, 11, 2), date(2027, 2, 22)
AUJOURDHUI = date(2026, 10, 22)


class Depot:
    def __init__(self):
        self.dossiers, self.payes, self.noms = {}, {}, 0
        self.remplacements, self.telephones = [], []

    def charger(self, apprenant, cours):
        return self.dossiers.get((apprenant, cours))

    def creer(self, d):
        self.noms += 1
        nom = f"D{self.noms}"
        self.payes.setdefault(nom, 0)
        self.dossiers[(d.apprenant, d.cours)] = DossierEnregistre(
            nom, d.apprenant, d.cours, d.mode, "", d.tarif, DEBUT, FIN,
            Dossier(d.echeances, 0, frais_inscription=d.tarif.frais_inscription), d.inscription)
        self.dernier = d
        return nom

    def remplacer_echeances(self, nom, mode, echeances):
        self.remplacements.append((nom, mode, echeances))

    def fixer_telephone(self, nom, telephone):
        self.telephones.append((nom, telephone))

    def paye(self, nom):
        return self.payes[nom]

    def fixer_delai(self, nom, d):
        pass


class Tarifs:
    def __init__(self, tarif=TARIF):
        self.tarif = tarif

    def charger(self, cours):
        return self.tarif


class Reglages:
    def __init__(self, r=ReglagesPaiement()):
        self.r = r

    def charger(self):
        return self.r


def ouvrir(depot, tarif=TARIF, aujourd_hui=AUJOURDHUI, reglages=ReglagesPaiement()):
    return OuvrirDossier(depot, Tarifs(tarif), Reglages(reglages), lambda: aujourd_hui)


class TestOuvrirDossier(unittest.TestCase):
    def test_cree_un_dossier_aux_prix_figes_avec_la_seule_echeance_des_frais(self):
        depot = Depot()
        nom = ouvrir(depot).executer("a@x.ci", "C", "B1", DEBUT, FIN)
        d = depot.dernier
        self.assertEqual((nom, d.mode, d.tarif, d.inscription, d.cohorte), ("D1", Mode.UNE_FOIS, TARIF, AUJOURDHUI, "B1"))
        self.assertEqual(d.echeances, (Echeance(AUJOURDHUI, 10000, "Frais d'inscription"),))

    def test_dossier_existant_renvoye_sans_changement(self):
        depot = Depot()
        cas = ouvrir(depot)
        premier = cas.executer("a@x.ci", "C", "B1", DEBUT, FIN)
        self.assertEqual(cas.executer("a@x.ci", "C", "B2", DEBUT, FIN), premier)
        self.assertEqual(depot.noms, 1)

    def test_tarif_modifie_ensuite_sans_effet_sur_le_dossier(self):
        depot = Depot()
        ouvrir(depot).executer("a@x.ci", "C", "B1", DEBUT, FIN)
        ouvrir(depot, Tarif(20000, 200000, 210000, 220000)).executer("b@x.ci", "C", "B1", DEBUT, FIN)
        self.assertEqual(depot.dossiers[("a@x.ci", "C")].tarif, TARIF)

    def test_inscription_trop_tardive_refusee(self):
        with self.assertRaisesRegex(InscriptionTardive, "Les inscriptions à cette cohorte sont closes"):
            ouvrir(Depot(), aujourd_hui=date(2027, 1, 3)).executer("a@x.ci", "C", "B1", DEBUT, FIN)

    def test_derniere_journee_permise(self):
        ouvrir(Depot(), aujourd_hui=date(2027, 1, 2)).executer("a@x.ci", "C", "B1", DEBUT, FIN)

    def test_delai_de_grace_lu_dans_les_reglages(self):
        cas = ouvrir(Depot(), aujourd_hui=date(2027, 1, 3), reglages=ReglagesPaiement(10, 3))
        cas.executer("a@x.ci", "C", "B1", DEBUT, FIN)

    def test_parcours_sans_tarif_refuse(self):
        with self.assertRaisesRegex(TarifAbsent, "pas encore de tarif"):
            ouvrir(Depot(), tarif=None).executer("a@x.ci", "C", "B1", DEBUT, FIN)

    def test_tarif_invalide_refuse_avant_figement(self):
        depot = Depot()
        with self.assertRaises(TarifInvalide):
            ouvrir(depot, Tarif(10003, 100000, 110000, 120000)).executer("a@x.ci", "C", "B1", DEBUT, FIN)
        self.assertEqual(depot.noms, 0)


class Journal:
    def __init__(self):
        self.appels = []

    def __call__(self, dossier, acteur, action, avant, apres, motif=""):
        self.appels.append((dossier, acteur, action, avant, apres, motif))


def depot_ouvert(paye=0, mode=Mode.UNE_FOIS):
    depot = Depot()
    ouvrir(depot).executer("a@x.ci", "C", "B1", DEBUT, FIN)
    d = depot.dossiers[("a@x.ci", "C")]
    depot.dossiers[("a@x.ci", "C")] = replace(d, mode=mode, dossier=replace(d.dossier, paye=paye))
    return depot


class TestChoisirMode(unittest.TestCase):
    def cas(self, depot, jour=10):
        self.journal = Journal()
        return ChoisirMode(depot, self.journal, lambda: date(2026, 11, 20), jour)

    def test_rien_de_paye_conserve_la_ligne_des_frais_datee_a_l_inscription(self):
        depot = depot_ouvert()
        echeances = self.cas(depot).executer("a@x.ci", "C", "mensuel", "+225 07 00 00 00 00")
        self.assertEqual(echeances[0], Echeance(AUJOURDHUI, 10000, "Frais d'inscription"))
        self.assertEqual(sum(e.montant for e in echeances), 120000)
        self.assertEqual(depot.remplacements, [("D1", Mode.MENSUEL, echeances)])
        self.assertEqual(depot.telephones, [("D1", "+2250700000000")])

    def test_apres_un_paiement_le_calendrier_est_replanifie(self):
        depot = depot_ouvert(paye=10000)
        echeances = self.cas(depot).executer("a@x.ci", "C", "deux_tranches", "+2250700000000")
        self.assertEqual(echeances[0], Echeance(date(2026, 11, 20), 10000, "Déjà versé"))
        self.assertEqual(echeances[1].date_limite, date(2026, 12, 10))
        self.assertEqual(sum(e.montant for e in echeances), 110000)

    def test_journal_acteur_et_avant_apres(self):
        depot = depot_ouvert()
        echeances = self.cas(depot).executer("a@x.ci", "C", "mensuel", "+2250700000000")
        (dossier, acteur, action, avant, apres, motif), = self.journal.appels
        self.assertEqual((dossier, acteur, action, motif), ("D1", "a@x.ci", "mode", ""))
        self.assertEqual(avant, {"mode": "une_fois", "echeances": [["2026-10-22", 10000, "Frais d'inscription"]]})
        self.assertEqual(apres["mode"], "mensuel")
        self.assertEqual(len(apres["echeances"]), len(echeances))

    def test_jour_d_echeance_regle(self):
        echeances = self.cas(depot_ouvert(), jour=5).executer("a@x.ci", "C", "deux_tranches", "+2250700000000")
        self.assertEqual({e.date_limite.day for e in echeances[1:]}, {5})

    def test_telephone_invalide_refuse_sans_rien_ecrire(self):
        depot = depot_ouvert()
        with self.assertRaisesRegex(TelephoneInvalide, "Numéro de téléphone invalide"):
            self.cas(depot).executer("a@x.ci", "C", "mensuel", "0700000000")
        self.assertEqual((depot.remplacements, self.journal.appels), ([], []))

    def test_mode_inconnu_refuse(self):
        with self.assertRaises(ValueError):
            self.cas(depot_ouvert()).executer("a@x.ci", "C", "trimestriel", "+2250700000000")

    def test_dossier_absent(self):
        with self.assertRaises(DossierAbsent):
            self.cas(Depot()).executer("a@x.ci", "C", "mensuel", "+2250700000000")


class TestTelephone(unittest.TestCase):
    def test_formats_acceptes(self):
        self.assertEqual(valider_telephone("+225 0700000000"), "+2250700000000")
        self.assertEqual(valider_telephone("+33 6 12 34 56 78"), "+33612345678")
        self.assertEqual(valider_telephone("+12345678"), "+12345678")

    def test_formats_refuses(self):
        for numero in ("", "0700000000", "+22507000000", "+225070000000000", "+1234567", "+1234567890123456",
                       "+225070000000a", "+33 abc"):
            with self.subTest(numero=numero), self.assertRaises(TelephoneInvalide):
                valider_telephone(numero)
