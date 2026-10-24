"""Accès à un parcours : bloqué seulement quand son dossier est en retard ; rôles exemptés jamais bloqués."""
import datetime
import unittest

from openlab_academy.application.acces_parcours import cours_bloques, parcours_bloque, redirection_paiement
from openlab_academy.application.ports_paiement import DossierEnregistre
from openlab_academy.domain.dossier_paiement import Dossier
from openlab_academy.domain.echeancier import Echeance, Mode, Tarif

JOUR = datetime.date(2026, 11, 15)
TARIF = Tarif(10000, 100000, 110000, 120000)


def enregistre(cours, paye, delai=None, dispense=False):
    echeances = (Echeance(datetime.date(2026, 11, 10), 10000, "Frais"),
                 Echeance(datetime.date(2026, 12, 10), 100000, "Solde"))
    return DossierEnregistre(f"D-{cours}", "aya@example.ci", cours, Mode.UNE_FOIS, "", TARIF,
                             datetime.date(2026, 11, 1), datetime.date(2027, 3, 1),
                             Dossier(echeances, paye, delai, dispense, frais_inscription=10000),
                             datetime.date(2026, 11, 1))


class DepotEnMemoire:
    def __init__(self, *dossiers):
        self.dossiers = {(d.apprenant, d.cours): d for d in dossiers}
        self.lectures = 0

    def charger(self, apprenant, cours):
        self.lectures += 1
        return self.dossiers.get((apprenant, cours))

    def cours_de(self, apprenant):
        return tuple(c for a, c in self.dossiers if a == apprenant)


class TestParcoursBloque(unittest.TestCase):
    def test_sans_dossier_jamais_bloque(self):
        self.assertFalse(parcours_bloque(DepotEnMemoire(), "aya@example.ci", "python", JOUR))

    def test_frais_impayes_bloquent(self):
        depot = DepotEnMemoire(enregistre("python", paye=0))
        self.assertTrue(parcours_bloque(depot, "aya@example.ci", "python", JOUR))

    def test_a_jour_ouvert(self):
        depot = DepotEnMemoire(enregistre("python", paye=10000))
        self.assertFalse(parcours_bloque(depot, "aya@example.ci", "python", JOUR))

    def test_delai_accorde_ouvre(self):
        depot = DepotEnMemoire(enregistre("python", paye=0, delai=datetime.date(2026, 11, 20)))
        self.assertFalse(parcours_bloque(depot, "aya@example.ci", "python", JOUR))

    def test_dispense_ouvre(self):
        depot = DepotEnMemoire(enregistre("python", paye=0, dispense=True))
        self.assertFalse(parcours_bloque(depot, "aya@example.ci", "python", JOUR))

    def test_exempte_jamais_bloque_sans_lire_le_dossier(self):
        depot = DepotEnMemoire(enregistre("python", paye=0))
        self.assertFalse(parcours_bloque(depot, "aya@example.ci", "python", JOUR, exempte=True))
        self.assertEqual(depot.lectures, 0)

    def test_un_parcours_bloque_n_affecte_pas_les_autres(self):
        depot = DepotEnMemoire(enregistre("python", paye=0), enregistre("data", paye=10000))
        self.assertTrue(parcours_bloque(depot, "aya@example.ci", "python", JOUR))
        self.assertFalse(parcours_bloque(depot, "aya@example.ci", "data", JOUR))


class TestCoursBloques(unittest.TestCase):
    def test_seuls_les_parcours_en_retard(self):
        depot = DepotEnMemoire(enregistre("python", paye=0), enregistre("data", paye=10000))
        self.assertEqual(cours_bloques(depot, "aya@example.ci", JOUR), ("python",))

    def test_exempte_aucun(self):
        depot = DepotEnMemoire(enregistre("python", paye=0))
        self.assertEqual(cours_bloques(depot, "aya@example.ci", JOUR, exempte=True), ())
        self.assertEqual(depot.lectures, 0)


class TestRedirection(unittest.TestCase):
    def test_chemin_de_paiement_du_parcours(self):
        self.assertEqual(redirection_paiement("python-pro"), "/espace/paiement/python-pro")

    def test_nom_encode(self):
        """OWASP A01/A03 : un nom de parcours ne peut ni sortir du préfixe ni injecter une URL."""
        self.assertEqual(redirection_paiement("../a b?x=1#y"), "/espace/paiement/..%2Fa%20b%3Fx%3D1%23y")
        self.assertEqual(redirection_paiement("//evil.example"), "/espace/paiement/%2F%2Fevil.example")
