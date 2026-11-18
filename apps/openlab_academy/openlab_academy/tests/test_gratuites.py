"""Offrir un parcours à un apprenant, et revenir en arrière (faux ports).

L'apprenant s'inscrit quand même : l'inscription reste le point où la donnée est collectée, c'est le paiement
qui saute. Son dossier naît donc comme pour tout le monde, puis se dispense, et l'intendance garde qui a offert
quoi, quand, et ce que le parcours aurait coûté.
"""
import unittest
from dataclasses import replace

from openlab_academy.application.gratuites import (
    ACTION_OFFERT, ACTION_RETRAIT, AccorderGratuite, GratuiteReservee, MOTIF_OFFERT, RetirerGratuite)
from openlab_academy.application.inscriptions import InscriptionDirecte, InscriptionRefusee, verifier_inscription_directe
from openlab_academy.application.paiements import OuvrirDossier
from openlab_academy.application.ports_paiement import ReglagesPaiement
from openlab_academy.domain.dossier_paiement import reste_du
from openlab_academy.tests.test_paiements import AUJOURDHUI, DEBUT, FIN, TARIF, Depot, Journal, Reglages, Tarifs

APPRENANT = "awa@exemple.ci"
COURS = "python"


class Gratuites:
    """Faux dépôt des gratuités accordées."""

    def __init__(self, *couples):
        self.accordees = set(couples)
        self.motifs = {}

    def accordee(self, apprenant, cours):
        return (apprenant, cours) in self.accordees

    def accorder(self, apprenant, cours, acteur, motif=""):
        self.accordees.add((apprenant, cours))
        self.motifs[(apprenant, cours)] = (acteur, motif)

    def retirer(self, apprenant, cours):
        self.accordees.discard((apprenant, cours))

    def apprenants(self, cours):
        return tuple(a for a, c in sorted(self.accordees) if c == cours)


class DepotOfferts(Depot):
    """Le dépôt des dossiers, augmenté de la dispense et de son retrait."""

    def dispenser(self, nom):
        self._poser(nom, True)

    def retablir(self, nom):
        self._poser(nom, False)

    def _poser(self, nom, dispense):
        for cle, enregistre in self.dossiers.items():
            if enregistre.nom == nom:
                self.dossiers[cle] = replace(enregistre, dossier=replace(enregistre.dossier, dispense=dispense))

    def dossier(self):
        return next(iter(self.dossiers.values()))


def depot_avec_dossier(paye=0, dispense=False):
    """Un dossier ouvert pour (APPRENANT, COURS), éventuellement déjà réglé en partie ou déjà dispensé."""
    depot = DepotOfferts()
    OuvrirDossier(depot, Tarifs(TARIF), Reglages(ReglagesPaiement()), lambda: AUJOURDHUI).executer(
        APPRENANT, COURS, "B1", DEBUT, FIN)
    enregistre = depot.dossier()
    depot.dossiers[(APPRENANT, COURS)] = replace(
        enregistre, dossier=replace(enregistre.dossier, paye=paye, dispense=dispense))
    return depot


def accorder(gratuites, depot, journal):
    return AccorderGratuite(gratuites, depot, journal, lambda: AUJOURDHUI)


def retirer(gratuites, depot, journal):
    return RetirerGratuite(gratuites, depot, journal, lambda: AUJOURDHUI)


class TestAccorder(unittest.TestCase):
    def setUp(self):
        self.gratuites, self.journal = Gratuites(), Journal()

    def test_gratuite_accordee(self):
        cas = accorder(self.gratuites, DepotOfferts(), self.journal)
        self.assertTrue(cas.executer("admin", APPRENANT, COURS, habilite=True, motif="Bourse"))
        self.assertTrue(self.gratuites.accordee(APPRENANT, COURS))
        self.assertEqual(self.gratuites.motifs[(APPRENANT, COURS)], ("admin", "Bourse"))

    def test_rejouable_sans_effet(self):
        cas = accorder(Gratuites((APPRENANT, COURS)), DepotOfferts(), self.journal)
        self.assertFalse(cas.executer("admin", APPRENANT, COURS, habilite=True))
        self.assertEqual(self.journal.appels, [])

    def test_reserve_a_l_administration(self):
        cas = accorder(self.gratuites, DepotOfferts(), self.journal)
        with self.assertRaisesRegex(GratuiteReservee, "offrir"):
            cas.executer("awa", APPRENANT, COURS, habilite=False)
        self.assertFalse(self.gratuites.accordee(APPRENANT, COURS))

    def test_dossier_existant_dispense_et_journalise(self):
        depot = depot_avec_dossier()
        accorder(self.gratuites, depot, self.journal).executer("admin", APPRENANT, COURS, habilite=True,
                                                               motif="Bourse")
        self.assertTrue(depot.dossier().dossier.dispense)
        dossier, acteur, action, avant, apres, motif = self.journal.appels[0]
        self.assertEqual((dossier, acteur, action, motif), ("D1", "admin", ACTION_OFFERT, "Bourse"))
        self.assertEqual(apres["statut"], "dispense")

    def test_motif_par_defaut_quand_aucun_n_est_donne(self):
        depot = depot_avec_dossier()
        accorder(self.gratuites, depot, self.journal).executer("admin", APPRENANT, COURS, habilite=True)
        self.assertEqual(self.journal.appels[0][-1], MOTIF_OFFERT)

    def test_ce_qui_a_ete_paye_reste_paye(self):
        depot = depot_avec_dossier(paye=50_000)
        accorder(self.gratuites, depot, self.journal).executer("admin", APPRENANT, COURS, habilite=True)
        self.assertEqual(depot.dossier().dossier.paye, 50_000)
        self.assertTrue(depot.dossier().dossier.dispense)

    def test_dossier_solde_laisse_tel_quel(self):
        depot = depot_avec_dossier()
        depot = depot_avec_dossier(paye=depot.dossier().dossier.total)
        accorder(self.gratuites, depot, self.journal).executer("admin", APPRENANT, COURS, habilite=True)
        self.assertFalse(depot.dossier().dossier.dispense)
        self.assertEqual(self.journal.appels, [])

    def test_sans_dossier_la_gratuite_vaut_pour_l_inscription_a_venir(self):
        depot = DepotOfferts()
        accorder(self.gratuites, depot, self.journal).executer("admin", APPRENANT, COURS, habilite=True)
        self.assertTrue(self.gratuites.accordee(APPRENANT, COURS))
        self.assertEqual(self.journal.appels, [])


class TestRetirer(unittest.TestCase):
    def setUp(self):
        self.journal = Journal()

    def test_gratuite_retiree(self):
        gratuites = Gratuites((APPRENANT, COURS))
        self.assertTrue(retirer(gratuites, DepotOfferts(), self.journal).executer(
            "admin", APPRENANT, COURS, habilite=True))
        self.assertFalse(gratuites.accordee(APPRENANT, COURS))

    def test_rien_a_retirer(self):
        self.assertFalse(retirer(Gratuites(), DepotOfferts(), self.journal).executer(
            "admin", APPRENANT, COURS, habilite=True))

    def test_reserve_a_l_administration(self):
        gratuites = Gratuites((APPRENANT, COURS))
        with self.assertRaisesRegex(GratuiteReservee, "offrir"):
            retirer(gratuites, DepotOfferts(), self.journal).executer("awa", APPRENANT, COURS, habilite=False)
        self.assertTrue(gratuites.accordee(APPRENANT, COURS))

    def test_le_dossier_redevient_du(self):
        depot = depot_avec_dossier(dispense=True)
        retirer(Gratuites((APPRENANT, COURS)), depot, self.journal).executer(
            "admin", APPRENANT, COURS, habilite=True)
        dossier = depot.dossier().dossier
        self.assertFalse(dossier.dispense)
        self.assertEqual(reste_du(dossier), dossier.total)
        self.assertEqual(self.journal.appels[0][2], ACTION_RETRAIT)

    def test_un_dossier_non_dispense_n_est_pas_touche(self):
        depot = depot_avec_dossier()
        retirer(Gratuites((APPRENANT, COURS)), depot, self.journal).executer(
            "admin", APPRENANT, COURS, habilite=True)
        self.assertFalse(depot.dossier().dossier.dispense)
        self.assertEqual(self.journal.appels, [])


class TestInscriptionDirecte(unittest.TestCase):
    """Le parcours offert s'inscrit tout seul : l'inscription a lieu, c'est le paiement qui saute."""

    class Gratuits:
        def gratuit(self, cours):
            return False

    def test_inscription_directe_permise_par_la_gratuite(self):
        demande = InscriptionDirecte(COURS, False, False, False, gratuite_accordee=True)
        verifier_inscription_directe(self.Gratuits(), demande)

    def test_inscription_directe_refusee_sans_gratuite(self):
        demande = InscriptionDirecte(COURS, False, False, False)
        with self.assertRaises(InscriptionRefusee):
            verifier_inscription_directe(self.Gratuits(), demande)


class TestActions(unittest.TestCase):
    def test_libelles_de_journal(self):
        self.assertEqual((ACTION_OFFERT, ACTION_RETRAIT, MOTIF_OFFERT),
                         ("dispense_parcours_offert", "retrait_gratuite", "parcours offert"))
