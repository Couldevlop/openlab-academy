"""Inscriptions : directe au parcours (gratuit seulement, hors équipe et cohorte), parcours facturé d'une cohorte."""
import unittest

from openlab_academy.application.inscriptions import (
    HORS_COHORTE, PLUSIEURS_PAYANTS, InscriptionDirecte, InscriptionRefusee, parcours_facture,
    verifier_inscription_directe)


class Gratuits:
    def __init__(self, *gratuits):
        self.gratuits = set(gratuits)

    def gratuit(self, cours):
        return cours in self.gratuits


def demande(cours="payant", **autres):
    return InscriptionDirecte(cours, **({"membre_exempte": False, "par_administrateur": False,
                                         "via_cohorte": False} | autres))


class TestInscriptionDirecte(unittest.TestCase):
    def test_parcours_payant_refuse_hors_cohorte(self):
        with self.assertRaisesRegex(InscriptionRefusee, "Inscrivez-vous à une cohorte de ce parcours."):
            verifier_inscription_directe(Gratuits("mooc"), demande())
        self.assertEqual(HORS_COHORTE, "Inscrivez-vous à une cohorte de ce parcours.")

    def test_parcours_gratuit_en_autonomie(self):
        verifier_inscription_directe(Gratuits("mooc"), demande("mooc"))

    def test_inscription_creee_par_la_cohorte(self):
        verifier_inscription_directe(Gratuits(), demande(via_cohorte=True))

    def test_membre_de_l_equipe(self):
        verifier_inscription_directe(Gratuits(), demande(membre_exempte=True))

    def test_administrateur_qui_inscrit(self):
        verifier_inscription_directe(Gratuits(), demande(par_administrateur=True))


class TestParcoursFacture(unittest.TestCase):
    def test_un_parcours(self):
        self.assertEqual(parcours_facture(Gratuits(), ("a",)), "a")
        self.assertEqual(parcours_facture(Gratuits("a"), ("a",)), "a")

    def test_cohorte_sans_parcours(self):
        self.assertIsNone(parcours_facture(Gratuits(), ()))

    def test_le_seul_parcours_payant_porte_le_dossier(self):
        self.assertEqual(parcours_facture(Gratuits("mooc"), ("mooc", "payant")), "payant")

    def test_parcours_tous_gratuits_le_premier(self):
        self.assertEqual(parcours_facture(Gratuits("m1", "m2"), ("m1", "m2")), "m1")

    def test_deux_parcours_payants_refuses(self):
        with self.assertRaisesRegex(InscriptionRefusee, "plusieurs parcours payants"):
            parcours_facture(Gratuits("mooc"), ("a", "mooc", "b"))
        self.assertIn("plusieurs parcours payants", PLUSIEURS_PAYANTS)
