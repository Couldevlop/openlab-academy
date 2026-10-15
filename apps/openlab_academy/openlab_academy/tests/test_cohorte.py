import datetime
import unittest

from openlab_academy.application.ouvrir_cohorte import OuvrirCohorte
from openlab_academy.domain.cohorte import Cohorte, CohorteInvalide, Rythme
from openlab_academy.domain.parcours import Bloc, Module
from openlab_academy.tests.fabriques import parcours, projet

LUNDI = datetime.date(2026, 11, 2)


class TestChargeDuParcours(unittest.TestCase):
    def test_charge_horaire(self):
        # 1 module × 8 h + 10 projets × 12 h + capstone 60 h
        self.assertEqual(parcours().charge_horaire(), 8 + 120 + 60)

    def test_duree_en_semaines_arrondie_au_superieur(self):
        self.assertEqual(parcours().duree_semaines(heures_par_semaine=8), 24)  # 188 / 8 = 23,5
        self.assertEqual(parcours().duree_semaines(heures_par_semaine=10), 19)

    def test_rythme_par_defaut_12_heures(self):
        self.assertEqual(parcours().duree_semaines(), 16)  # 188 / 12 = 15,7

    def test_rythme_invalide(self):
        with self.assertRaises(ValueError):
            parcours().duree_semaines(heures_par_semaine=0)


class TestCohortePilote(unittest.TestCase):
    def test_pilote_calee_sur_le_parcours(self):
        c = Cohorte.pilote(parcours(title="Fondamentaux"), LUNDI)
        self.assertEqual(c.titre, "Promo 1 — Fondamentaux · Standard 12 h")
        self.assertEqual(c.rythme, Rythme.STANDARD)
        self.assertEqual(c.cours, "Fondamentaux")
        self.assertEqual(c.debut, LUNDI)
        self.assertEqual(c.fin, LUNDI + datetime.timedelta(weeks=16))
        self.assertEqual((c.heure_debut, c.heure_fin, c.fuseau), ("18:30", "20:30", "Africa/Abidjan"))

    def test_fin_apres_debut(self):
        with self.assertRaisesRegex(CohorteInvalide, "la fin doit suivre le début"):
            Cohorte("T", "C", LUNDI, LUNDI, "18:30", "20:30", "Africa/Abidjan", Rythme.STANDARD)

    def test_horaires_coherents(self):
        with self.assertRaisesRegex(CohorteInvalide, "horaire"):
            Cohorte("T", "C", LUNDI, LUNDI + datetime.timedelta(days=1), "20:30", "18:30", "Africa/Abidjan",
                    Rythme.STANDARD)

    def test_pilote_intensive_plus_courte(self):
        c = Cohorte.pilote(parcours(title="Fondamentaux"), LUNDI, Rythme.INTENSIF)
        self.assertEqual(c.titre, "Promo 1 — Fondamentaux · Intensif 16 h")
        self.assertEqual(c.fin, LUNDI + datetime.timedelta(weeks=12))  # 188 / 16 = 11,75


class TestRythme(unittest.TestCase):
    def test_deux_formats(self):
        self.assertEqual((Rythme.STANDARD.heures, Rythme.INTENSIF.heures), (12, 16))
        self.assertEqual(Rythme("intensif"), Rythme.INTENSIF)

    def test_organisation_hebdomadaire_coherente_avec_les_heures(self):
        for rythme in Rythme:
            with self.subTest(rythme=rythme):
                self.assertEqual(sum(h for _, h in rythme.semaine), rythme.heures)

    def test_descriptif_lisible(self):
        self.assertIn("2 h chaque soir de semaine", Rythme.INTENSIF.descriptif)
        self.assertIn("3 h le samedi et le dimanche", Rythme.INTENSIF.descriptif)
        self.assertIn("12 h par semaine", Rythme.STANDARD.descriptif)


class DepotCohortesEnMemoire:
    def __init__(self):
        self.cohortes = {}

    def trouver(self, titre):
        return titre if titre in self.cohortes else None

    def creer(self, cohorte):
        self.cohortes[cohorte.titre] = cohorte
        return cohorte.titre


class TestOuvrirCohorte(unittest.TestCase):
    def test_ouverture_idempotente(self):
        depot = DepotCohortesEnMemoire()
        cas = OuvrirCohorte(depot)
        premiere = cas.executer(parcours(title="P0"), LUNDI)
        seconde = cas.executer(parcours(title="P0"), LUNDI + datetime.timedelta(weeks=1))
        self.assertEqual(premiere, ("Promo 1 — P0 · Standard 12 h", True))
        self.assertEqual(seconde, ("Promo 1 — P0 · Standard 12 h", False))
        self.assertEqual(depot.cohortes["Promo 1 — P0 · Standard 12 h"].debut, LUNDI)

    def test_les_deux_formats_coexistent(self):
        depot = DepotCohortesEnMemoire()
        cas = OuvrirCohorte(depot)
        cas.executer(parcours(title="P0"), LUNDI)
        cas.executer(parcours(title="P0"), LUNDI, Rythme.INTENSIF)
        self.assertEqual(sorted(depot.cohortes), ["Promo 1 — P0 · Intensif 16 h", "Promo 1 — P0 · Standard 12 h"])

    def test_debut_par_defaut_lundi_dans_deux_semaines(self):
        depot = DepotCohortesEnMemoire()
        OuvrirCohorte(depot, aujourd_hui=lambda: datetime.date(2026, 10, 15)).executer(parcours(title="P0"))
        debut = depot.cohortes["Promo 1 — P0 · Standard 12 h"].debut
        self.assertEqual(debut, datetime.date(2026, 11, 2))
        self.assertEqual(debut.weekday(), 0)


class TestParcoursMultiBlocs(unittest.TestCase):
    def test_charge_compte_tous_les_modules(self):
        blocs = (Bloc("B1", (Module("01", "a", "c", "l"), Module("02", "b", "c", "l"))),)
        p = parcours(blocs=blocs, portfolio=tuple(projet(duree_h=10) for _ in range(10)))
        self.assertEqual(p.charge_horaire(), 16 + 100 + 60)
