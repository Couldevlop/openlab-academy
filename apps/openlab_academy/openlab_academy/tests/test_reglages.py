import dataclasses
import unittest

from openlab_academy.domain.reglages import TITRE_LANCEMENT, CritereBareme, Reglages, ReglagesInvalides, Rythme

JOURS_SEMAINE = ("lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche")


def rythme(code="r", heures=(2, 0, 0, 0, 0, 3, 3), libelle="R"):
    return Rythme(code=code, libelle=libelle, heures_par_jour=heures)


class TestRythme(unittest.TestCase):
    def test_heures_et_semaine(self):
        r = rythme(heures=(2, 2, 2, 2, 2, 3, 3))
        self.assertEqual(r.heures, 16)
        self.assertEqual(r.semaine, tuple(zip(JOURS_SEMAINE, (2, 2, 2, 2, 2, 3, 3))))

    def test_descriptif_regroupe_les_jours(self):
        self.assertEqual(rythme(heures=(2, 2, 2, 2, 2, 3, 3)).descriptif,
                         "16 h par semaine : 2 h les lundi, mardi, mercredi, jeudi et vendredi, 3 h les samedi et dimanche")
        self.assertEqual(rythme(heures=(0, 0, 0, 0, 0, 4, 0)).descriptif, "4 h par semaine : 4 h le samedi")

    def test_sept_jours_obligatoires(self):
        with self.assertRaisesRegex(ReglagesInvalides, "7 valeurs"):
            rythme(heures=(2, 2))

    def test_heures_negatives_ou_nulles_refusees(self):
        with self.assertRaisesRegex(ReglagesInvalides, "rythme « r » : heures négatives"):
            rythme(heures=(-1, 0, 0, 0, 0, 0, 0))
        with self.assertRaisesRegex(ReglagesInvalides, "rythme « r » : aucune heure"):
            rythme(heures=(0,) * 7)

    def test_code_obligatoire(self):
        with self.assertRaisesRegex(ReglagesInvalides, "code de rythme manquant"):
            rythme(code=" ")


class TestReglagesParDefaut(unittest.TestCase):
    def test_valeurs_actuelles(self):
        r = Reglages()
        self.assertEqual((r.projets_par_portfolio, r.heures_par_module, r.delai_ouverture_semaines, r.jour_ouverture),
                         (10, 8, 2, 0))
        self.assertEqual((r.heure_debut, r.heure_fin, r.fuseau), ("18:30", "20:30", "Africa/Abidjan"))
        self.assertEqual((r.parcours_pilote, r.formateur), (TITRE_LANCEMENT, "Administrator"))
        self.assertIsNone(r.ouverture_lancement)
        self.assertEqual([(c.nom, c.poids) for c in r.bareme],
                         [("Fonctionnel", 40), ("Qualité & tests", 25), ("Architecture", 15), ("Sécurité", 10),
                          ("Documentation", 10)])
        self.assertIn("Tests automatisés, couverture ≥ 70 %", r.exigences_communes)
        self.assertEqual([(x.code, x.heures) for x in r.rythmes], [("standard", 12), ("intensif", 16)])

    def test_places_par_cohorte(self):
        self.assertEqual(Reglages().places_par_cohorte, 30)
        with self.assertRaisesRegex(ReglagesInvalides, "places_par_cohorte doit être positif"):
            Reglages(places_par_cohorte=0)

    def test_exercices_par_defaut(self):
        r = Reglages()
        self.assertEqual((r.questions_par_quiz, r.tentatives_max, r.score_min, r.delai_exercices_minutes),
                         (5, 3, 100, 60))

    def test_immuable(self):
        with self.assertRaises(dataclasses.FrozenInstanceError):
            Reglages().heures_par_module = 4


class TestInvariantsReglages(unittest.TestCase):
    def test_bareme_doit_totaliser_100(self):
        with self.assertRaisesRegex(ReglagesInvalides, "barème : total 90 % au lieu de 100 %"):
            Reglages(bareme=(CritereBareme("A", 50), CritereBareme("B", 40)))

    def test_poids_negatif_refuse(self):
        with self.assertRaisesRegex(ReglagesInvalides, "barème : poids négatif pour « B »"):
            Reglages(bareme=(CritereBareme("A", 110), CritereBareme("B", -10)))

    def test_au_moins_un_rythme(self):
        with self.assertRaisesRegex(ReglagesInvalides, "au moins un rythme"):
            Reglages(rythmes=())

    def test_codes_de_rythme_uniques(self):
        with self.assertRaisesRegex(ReglagesInvalides, "code de rythme « r » en double"):
            Reglages(rythmes=(rythme(), rythme()))

    def test_seance_coherente(self):
        with self.assertRaisesRegex(ReglagesInvalides, "la séance doit finir après son début"):
            Reglages(heure_debut="20:30", heure_fin="18:30")

    def test_format_heure(self):
        with self.assertRaisesRegex(ReglagesInvalides, "heure « 25:00 » invalide"):
            Reglages(heure_debut="25:00", heure_fin="26:00")

    def test_valeurs_positives(self):
        for champ in ("projets_par_portfolio", "heures_par_module"):
            with self.subTest(champ=champ), self.assertRaisesRegex(ReglagesInvalides, f"{champ} doit être positif"):
                Reglages(**{champ: 0})
        with self.assertRaisesRegex(ReglagesInvalides, "delai_ouverture_semaines ne peut pas être négatif"):
            Reglages(delai_ouverture_semaines=-1)

    def test_reglages_d_exercices_coherents(self):
        for champ in ("questions_par_quiz", "tentatives_max"):
            with self.subTest(champ=champ), self.assertRaisesRegex(ReglagesInvalides, f"{champ} doit être positif"):
                Reglages(**{champ: 0})
        for score in (0, 101):
            with self.subTest(score=score), self.assertRaisesRegex(ReglagesInvalides, "score_min entre 1 et 100"):
                Reglages(score_min=score)
        with self.assertRaisesRegex(ReglagesInvalides, "delai_exercices_minutes ne peut pas être négatif"):
            Reglages(delai_exercices_minutes=-5)

    def test_jour_ouverture_valide(self):
        with self.assertRaisesRegex(ReglagesInvalides, "jour_ouverture"):
            Reglages(jour_ouverture=7)

    def test_textes_obligatoires(self):
        for champ in ("parcours_pilote", "formateur", "fuseau"):
            with self.subTest(champ=champ), self.assertRaisesRegex(ReglagesInvalides, f"{champ} manquant"):
                Reglages(**{champ: ""})


class TestRechercheRythme(unittest.TestCase):
    def test_par_code(self):
        self.assertEqual(Reglages().rythme("intensif").heures, 16)

    def test_code_inconnu(self):
        with self.assertRaisesRegex(ReglagesInvalides, r"rythme « turbo » inconnu : \['standard', 'intensif'\]"):
            Reglages().rythme("turbo")
