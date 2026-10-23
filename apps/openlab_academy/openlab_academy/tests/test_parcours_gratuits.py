"""Parcours gratuits (MOOC) : inscription sans tarif ni dossier, tarif refusé, passage payant -> gratuit (faux ports)."""
import unittest
from dataclasses import replace
from datetime import date

from openlab_academy.application.parcours_gratuits import (
    MOTIF_GRATUIT, DispenserParcoursGratuit, TarifSurParcoursGratuit, refuser_tarif_si_gratuit, vue_parcours_gratuit)
from openlab_academy.application.paiements import (
    ChoisirMode, InscriptionTardive, OperationRefusee, OuvrirDossier, TarifAbsent)
from openlab_academy.application.ports_paiement import ReglagesPaiement
from openlab_academy.domain.dossier_paiement import bloque, rappels_dus
from openlab_academy.tests.test_paiements import (
    AUJOURDHUI, DEBUT, FIN, TARIF, Depot, Journal, Reglages, Tarifs)


class Gratuits:
    def __init__(self, *cours):
        self.cours = set(cours)
        self.lus = []

    def gratuit(self, cours):
        self.lus.append(cours)
        return cours in self.cours


def ouvrir(depot, gratuits, tarif=TARIF, aujourd_hui=AUJOURDHUI):
    return OuvrirDossier(depot, Tarifs(tarif), Reglages(ReglagesPaiement()), lambda: aujourd_hui, gratuits)


class TestInscriptionGratuite(unittest.TestCase):
    def test_parcours_gratuit_inscription_sans_tarif_ni_dossier(self):
        depot = Depot()
        cas = ouvrir(depot, Gratuits("MOOC"), tarif=None)
        self.assertIsNone(cas.verifier("MOOC", DEBUT))
        self.assertIsNone(cas.executer("a@x.ci", "MOOC", "B1", DEBUT, FIN))
        self.assertEqual((depot.noms, depot.dossiers), (0, {}))

    def test_tarif_eventuel_d_un_parcours_gratuit_ignore(self):
        depot = Depot()
        self.assertIsNone(ouvrir(depot, Gratuits("MOOC")).executer("a@x.ci", "MOOC", "B1", DEBUT, FIN))
        self.assertEqual(depot.noms, 0)

    def test_limite_d_inscription_tardive_aussi_pour_un_mooc(self):
        cas = ouvrir(Depot(), Gratuits("MOOC"), tarif=None, aujourd_hui=date(2027, 1, 3))
        with self.assertRaisesRegex(InscriptionTardive, "closes"):
            cas.executer("a@x.ci", "MOOC", "B1", DEBUT, FIN)

    def test_parcours_payant_sans_tarif_reste_refuse(self):
        """Garde-fou contre l'oubli du prix : seul un parcours explicitement gratuit se passe de tarif."""
        gratuits = Gratuits("MOOC")
        with self.assertRaisesRegex(TarifAbsent, "pas encore de tarif"):
            ouvrir(Depot(), gratuits, tarif=None).executer("a@x.ci", "C", "B1", DEBUT, FIN)
        self.assertEqual(gratuits.lus, ["C"])

    def test_parcours_payant_toujours_ouvert_avec_dossier(self):
        depot = Depot()
        self.assertEqual(ouvrir(depot, Gratuits("MOOC")).executer("a@x.ci", "C", "B1", DEBUT, FIN), "D1")

    def test_dossier_existant_d_un_parcours_devenu_gratuit_renvoye_tel_quel(self):
        depot = Depot()
        ouvrir(depot, Gratuits()).executer("a@x.ci", "C", "B1", DEBUT, FIN)
        self.assertEqual(ouvrir(depot, Gratuits("C")).executer("a@x.ci", "C", "B2", DEBUT, FIN), "D1")
        self.assertEqual(depot.noms, 1)


class TestTarif(unittest.TestCase):
    def test_tarif_refuse_sur_un_parcours_gratuit(self):
        with self.assertRaisesRegex(TarifSurParcoursGratuit, "gratuit .*aucun tarif.*Décochez"):
            refuser_tarif_si_gratuit(Gratuits("MOOC"), "MOOC")

    def test_tarif_permis_sur_un_parcours_payant(self):
        refuser_tarif_si_gratuit(Gratuits("MOOC"), "C")


class TestVue(unittest.TestCase):
    def test_etat_calme_de_l_apprenant(self):
        self.assertEqual(vue_parcours_gratuit("MOOC", "Initiation à l'IA"),
                         {"cours": "MOOC", "titre": "Initiation à l'IA", "gratuit": True})


class DepotDispense(Depot):
    def a_dispenser(self, cours):
        return tuple(d.nom for (_, c), d in self.dossiers.items() if c == cours and not d.dossier.dispense)

    def dispenser(self, nom):
        self.dispenses = getattr(self, "dispenses", []) + [nom]
        for cle, e in self.dossiers.items():
            if e.nom == nom:
                self.dossiers[cle] = replace(e, dossier=replace(e.dossier, dispense=True))


def depot_avec_dossiers():
    """Deux apprenants du parcours C (l'un en retard sur les frais), un d'un autre parcours."""
    depot = DepotDispense()
    cas = ouvrir(depot, Gratuits())
    for apprenant, cours in (("a@x.ci", "C"), ("b@x.ci", "C"), ("c@x.ci", "AUTRE")):
        cas.executer(apprenant, cours, "B1", DEBUT, FIN)
    return depot


class TestPassageAuGratuit(unittest.TestCase):
    def cas(self, depot, *gratuits, journal=None):
        return DispenserParcoursGratuit(depot, journal or Journal(), Gratuits(*gratuits), lambda: date(2026, 11, 20))

    def test_dossiers_dispenses_et_journalises(self):
        depot, journal = depot_avec_dossiers(), Journal()
        avant_b = depot.dossiers[("b@x.ci", "C")]
        depot.dossiers[("b@x.ci", "C")] = replace(avant_b, dossier=replace(avant_b.dossier, paye=10000))
        self.assertEqual(self.cas(depot, "C", journal=journal).executer("intendant@x.ci", "C"), 2)
        self.assertEqual(depot.dispenses, ["D1", "D2"])
        self.assertEqual(journal.appels, [
            ("D1", "intendant@x.ci", "dispense_parcours_gratuit", {"statut": "en_retard", "paye": 0},
             {"statut": "dispense", "paye": 0}, MOTIF_GRATUIT),
            ("D2", "intendant@x.ci", "dispense_parcours_gratuit", {"statut": "en_retard", "paye": 10000},
             {"statut": "dispense", "paye": 10000}, MOTIF_GRATUIT)])
        self.assertEqual(MOTIF_GRATUIT, "parcours devenu gratuit")
        self.assertFalse(depot.dossiers[("c@x.ci", "AUTRE")].dossier.dispense)

    def test_dossier_dispense_ni_bloque_ni_rappele(self):
        depot = depot_avec_dossiers()
        self.cas(depot, "C").executer("admin@x.ci", "C")
        d = depot.dossiers[("a@x.ci", "C")].dossier
        self.assertFalse(bloque(d, date(2027, 1, 20)))
        self.assertEqual(rappels_dus(d, date(2026, 11, 3)), ())

    def test_rejeu_sans_nouvelle_ligne(self):
        depot, journal = depot_avec_dossiers(), Journal()
        cas = self.cas(depot, "C", journal=journal)
        cas.executer("admin@x.ci", "C")
        self.assertEqual(cas.executer("admin@x.ci", "C"), 0)
        self.assertEqual(len(journal.appels), 2)

    def test_parcours_payant_intact(self):
        depot, journal = depot_avec_dossiers(), Journal()
        self.assertEqual(self.cas(depot, journal=journal).executer("admin@x.ci", "C"), 0)
        self.assertEqual((getattr(depot, "dispenses", []), journal.appels), ([], []))

    def test_dossier_dispense_aucun_changement_de_mode(self):
        depot, journal = depot_avec_dossiers(), Journal()
        self.cas(depot, "C").executer("admin@x.ci", "C")
        with self.assertRaisesRegex(OperationRefusee, "dispensé"):
            ChoisirMode(depot, journal, lambda: AUJOURDHUI).executer("a@x.ci", "C", "mensuel", "+2250700000000")
        self.assertEqual((depot.remplacements, depot.telephones, journal.appels), ([], [], []))

    def test_passage_gratuit_vers_payant_sans_dossier_retroactif(self):
        """Redevenu payant : les dispensés le restent, seuls les nouveaux inscrits reçoivent un dossier."""
        depot = depot_avec_dossiers()
        self.cas(depot, "C").executer("admin@x.ci", "C")
        ouvrir(depot, Gratuits()).executer("d@x.ci", "C", "B1", DEBUT, FIN)
        self.assertTrue(depot.dossiers[("a@x.ci", "C")].dossier.dispense)
        self.assertFalse(depot.dossiers[("d@x.ci", "C")].dossier.dispense)

