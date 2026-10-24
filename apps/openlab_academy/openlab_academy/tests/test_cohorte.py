import datetime
import unittest

from openlab_academy.application.ouvrir_cohorte import OuvrirCohorte
from openlab_academy.domain.cohorte import Cohorte, CohorteInvalide
from openlab_academy.domain.parcours import Bloc, Module
from openlab_academy.domain.reglages import Reglages, Rythme
from openlab_academy.tests.fabriques import parcours, projet

LUNDI = datetime.date(2026, 11, 2)
REGLAGES = Reglages()
STANDARD, INTENSIF = REGLAGES.rythme("standard"), REGLAGES.rythme("intensif")


class TestChargeDuParcours(unittest.TestCase):
    def test_charge_horaire(self):
        # 1 module × 8 h + 10 projets × 12 h + capstone 60 h
        self.assertEqual(parcours().charge_horaire(), 8 + 120 + 60)

    def test_heures_par_module_parametrables(self):
        self.assertEqual(parcours(heures_par_module=10).charge_horaire(), 10 + 120 + 60)

    def test_duree_en_semaines_arrondie_au_superieur(self):
        self.assertEqual(parcours().duree_semaines(8), 24)  # 188 / 8 = 23,5
        self.assertEqual(parcours().duree_semaines(12), 16)
        self.assertEqual(parcours().duree_semaines(16), 12)

    def test_rythme_invalide(self):
        with self.assertRaises(ValueError):
            parcours().duree_semaines(0)


class TestCohortePilote(unittest.TestCase):
    def test_pilote_calee_sur_le_parcours_et_les_reglages(self):
        c = Cohorte.pilote(parcours(title="Fondamentaux"), LUNDI, STANDARD, REGLAGES)
        self.assertEqual(c.titre, "Promo 1 — Fondamentaux · Standard 12 h")
        self.assertEqual((c.cours, c.debut, c.rythme), ("Fondamentaux", LUNDI, STANDARD))
        self.assertEqual(c.fin, LUNDI + datetime.timedelta(weeks=16))
        self.assertEqual((c.heure_debut, c.heure_fin, c.fuseau), ("18:30", "20:30", "Africa/Abidjan"))

    def test_pilote_intensive_plus_courte(self):
        c = Cohorte.pilote(parcours(title="Fondamentaux"), LUNDI, INTENSIF, REGLAGES)
        self.assertEqual(c.titre, "Promo 1 — Fondamentaux · Intensif 16 h")
        self.assertEqual(c.fin, LUNDI + datetime.timedelta(weeks=12))  # 188 / 16 = 11,75

    def test_seances_et_rythme_personnalises(self):
        reglages = Reglages(heure_debut="19:00", heure_fin="21:00", fuseau="Africa/Dakar")
        week_end = Rythme("week-end", "Week-end", (0, 0, 0, 0, 0, 5, 5))
        c = Cohorte.pilote(parcours(title="P"), LUNDI, week_end, reglages)
        self.assertEqual((c.heure_debut, c.heure_fin, c.fuseau), ("19:00", "21:00", "Africa/Dakar"))
        self.assertEqual(c.titre, "Promo 1 — P · Week-end 10 h")
        self.assertEqual(c.fin, LUNDI + datetime.timedelta(weeks=19))  # 188 / 10 = 18,8

    def test_places_reglees(self):
        self.assertEqual(Cohorte.pilote(parcours(title="P"), LUNDI, STANDARD, REGLAGES).places, 30)
        reglages = Reglages(places_par_cohorte=12)
        self.assertEqual(Cohorte.pilote(parcours(title="P"), LUNDI, STANDARD, reglages).places, 12)

    def test_places_positives(self):
        with self.assertRaisesRegex(CohorteInvalide, "au moins une place"):
            Cohorte("T", "C", LUNDI, LUNDI + datetime.timedelta(days=1), "18:30", "20:30", "Africa/Abidjan",
                    STANDARD, places=0)

    def test_seances_lisibles_tirees_des_horaires(self):
        c = Cohorte.pilote(parcours(title="P"), LUNDI, STANDARD, REGLAGES)
        self.assertEqual(c.seances, "Séances de 18 h 30 à 20 h 30 (heure d'Abidjan).")
        autre = Cohorte.pilote(parcours(title="P"), LUNDI, STANDARD,
                               Reglages(heure_debut="19:00", heure_fin="21:05", fuseau="Africa/Dakar"))
        self.assertEqual(autre.seances, "Séances de 19 h à 21 h 05 (fuseau Africa/Dakar).")

    def test_fin_apres_debut(self):
        with self.assertRaisesRegex(CohorteInvalide, "la fin doit suivre le début"):
            Cohorte("T", "C", LUNDI, LUNDI, "18:30", "20:30", "Africa/Abidjan", STANDARD)

    def test_horaires_coherents(self):
        with self.assertRaisesRegex(CohorteInvalide, "horaire"):
            Cohorte("T", "C", LUNDI, LUNDI + datetime.timedelta(days=1), "20:30", "18:30", "Africa/Abidjan", STANDARD)


class DepotCohortesEnMemoire:
    def __init__(self):
        self.cohortes = {}

    def trouver(self, titre):
        return titre if titre in self.cohortes else None

    def creer(self, cohorte):
        self.cohortes[cohorte.titre] = cohorte
        return cohorte.titre


class TestOuvrirCohorte(unittest.TestCase):
    def test_ouverture_idempotente_au_rythme_par_defaut(self):
        depot = DepotCohortesEnMemoire()
        cas = OuvrirCohorte(depot, REGLAGES)
        premiere = cas.executer(parcours(title="P0"), LUNDI)
        seconde = cas.executer(parcours(title="P0"), LUNDI + datetime.timedelta(weeks=1))
        self.assertEqual(premiere, ("Promo 1 — P0 · Standard 12 h", True))
        self.assertEqual(seconde, ("Promo 1 — P0 · Standard 12 h", False))
        self.assertEqual(depot.cohortes["Promo 1 — P0 · Standard 12 h"].debut, LUNDI)

    def test_les_deux_formats_coexistent(self):
        depot = DepotCohortesEnMemoire()
        cas = OuvrirCohorte(depot, REGLAGES)
        cas.executer(parcours(title="P0"), LUNDI)
        cas.executer(parcours(title="P0"), LUNDI, INTENSIF)
        self.assertEqual(sorted(depot.cohortes), ["Promo 1 — P0 · Intensif 16 h", "Promo 1 — P0 · Standard 12 h"])

    def test_debut_par_defaut_selon_delai_et_jour_regles(self):
        jeudi = datetime.date(2026, 10, 15)
        depot = DepotCohortesEnMemoire()
        OuvrirCohorte(depot, REGLAGES, aujourd_hui=lambda: jeudi).executer(parcours(title="P0"))
        self.assertEqual(depot.cohortes["Promo 1 — P0 · Standard 12 h"].debut, datetime.date(2026, 11, 2))

        depot = DepotCohortesEnMemoire()
        samedi_dans_une_semaine = Reglages(delai_ouverture_semaines=1, jour_ouverture=5)
        OuvrirCohorte(depot, samedi_dans_une_semaine, aujourd_hui=lambda: jeudi).executer(parcours(title="P0"))
        debut = depot.cohortes["Promo 1 — P0 · Standard 12 h"].debut
        self.assertEqual((debut, debut.weekday()), (datetime.date(2026, 10, 24), 5))


class TestParcoursParametre(unittest.TestCase):
    def test_charge_compte_tous_les_modules(self):
        blocs = (Bloc("B1", (Module("01", "a", "c", "l"), Module("02", "b", "c", "l"))),)
        p = parcours(blocs=blocs, portfolio=tuple(projet(duree_h=10) for _ in range(10)))
        self.assertEqual(p.charge_horaire(), 16 + 100 + 60)

    def test_nombre_de_projets_parametrable(self):
        p = parcours(projets_attendus=3, portfolio=tuple(projet() for _ in range(3)))
        self.assertEqual(len(p.chapitres()), 1 + 3 + 1)

    def test_heures_par_module_positives(self):
        with self.assertRaisesRegex(ValueError, "heures_par_module doit être positif"):
            parcours(heures_par_module=0)
