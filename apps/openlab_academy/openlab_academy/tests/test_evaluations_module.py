"""Pièces d'évaluation choisies séance par séance.

Une séance porte par défaut tout l'attirail : quiz, mise en situation et livrable. Un parcours qui alterne un
rappel du matin (quiz seul) et une leçon du soir (challenge seul) a besoin de le dire séance par séance, sinon
le LMS attend un rendu qui n'existe pas et la leçon suivante ne s'ouvre jamais.
"""
import unittest

from openlab_academy.domain.parcours import Bloc, Evaluations, Module, ParcoursInvalide
from openlab_academy.domain.reglages import Reglages
from openlab_academy.infrastructure.yaml_source import FormatInvalide, depuis_dict
from openlab_academy.tests.fabriques import module_complet, parcours, parcours_brut, question

CINQ = tuple(question() for _ in range(5))


def seance(**champs):
    """Parcours de deux séances : la première est celle qu'on éprouve, la seconde est complète."""
    return parcours(questions_par_quiz=5,
                    blocs=(Bloc("B1", (Module("01", "M", "c", champs.pop("livrable", "l"), **champs),
                                       module_complet("02"))),))


class TestValeurs(unittest.TestCase):
    def test_quatre_valeurs_nommees(self):
        self.assertEqual(
            tuple(e.value for e in Evaluations), ("completes", "quiz", "livrable", "aucune"))

    def test_par_defaut_la_seance_porte_tout(self):
        m = module_complet("01")
        self.assertEqual(m.evaluations, Evaluations.COMPLETES)
        self.assertEqual((m.veut_quiz, m.veut_livrable), (True, True))

    def test_ce_que_chaque_valeur_demande(self):
        attendu = {Evaluations.COMPLETES: (True, True), Evaluations.QUIZ: (True, False),
                   Evaluations.LIVRABLE: (False, True), Evaluations.AUCUNE: (False, False)}
        for valeur, (quiz, livrable) in attendu.items():
            m = Module("01", "M", "c", "", evaluations=valeur)
            self.assertEqual((m.veut_quiz, m.veut_livrable), (quiz, livrable), valeur)


class TestInvariants(unittest.TestCase):
    def test_completes_exige_tout(self):
        with self.assertRaisesRegex(ParcoursInvalide, "module 01 : 5 questions attendues, 0 trouvées"):
            seance()

    def test_quiz_exige_le_quiz_au_complet(self):
        p = seance(evaluations=Evaluations.QUIZ, quiz=CINQ, livrable="")
        self.assertEqual(len(p.blocs[0].modules[0].quiz), 5)

    def test_quiz_incomplet_refuse(self):
        with self.assertRaisesRegex(ParcoursInvalide, "module 01 : 5 questions attendues, 2 trouvées"):
            seance(evaluations=Evaluations.QUIZ, quiz=CINQ[:2], livrable="")

    def test_quiz_refuse_un_livrable(self):
        with self.assertRaisesRegex(ParcoursInvalide, "module 01 : séance de quiz seul"):
            seance(evaluations=Evaluations.QUIZ, quiz=CINQ, livrable="Un rendu")

    def test_quiz_refuse_une_mise_en_situation(self):
        with self.assertRaisesRegex(ParcoursInvalide, "module 01 : séance de quiz seul"):
            seance(evaluations=Evaluations.QUIZ, quiz=CINQ, livrable="", mise_en_situation="Un cas")

    def test_livrable_seul_accepte(self):
        p = seance(evaluations=Evaluations.LIVRABLE, livrable="Le challenge du jour")
        self.assertEqual(p.blocs[0].modules[0].quiz, ())

    def test_livrable_refuse_un_quiz(self):
        with self.assertRaisesRegex(ParcoursInvalide, "module 01 : séance de livrable seul"):
            seance(evaluations=Evaluations.LIVRABLE, quiz=CINQ)

    def test_livrable_manquant_refuse(self):
        with self.assertRaisesRegex(ParcoursInvalide, "module 01 : livrable manquant"):
            seance(evaluations=Evaluations.LIVRABLE, livrable="")

    def test_aucune_refuse_quiz_et_mise_en_situation(self):
        with self.assertRaisesRegex(ParcoursInvalide, "module 01 : séance sans évaluation"):
            seance(evaluations=Evaluations.AUCUNE, quiz=CINQ, livrable="")

    def test_aucune_sans_rien_acceptee(self):
        p = seance(evaluations=Evaluations.AUCUNE, livrable="")
        self.assertEqual(p.blocs[0].modules[0].evaluations, Evaluations.AUCUNE)

    def test_livrable_toujours_exige_quand_la_seance_en_porte_un(self):
        with self.assertRaisesRegex(ParcoursInvalide, "module 01 : livrable manquant"):
            seance(quiz=CINQ, mise_en_situation="Un cas", livrable="")


class TestLectureDuFichier(unittest.TestCase):
    def brut(self, valeur):
        brut = parcours_brut()
        m = brut["blocs"][0]["modules"][0]
        m.update(evaluations=valeur, quiz=[], mise_en_situation="", livrable="")
        return brut

    def test_cle_lue(self):
        p = depuis_dict(self.brut("aucune"), "t.yaml", Reglages())
        self.assertEqual(p.blocs[0].modules[0].evaluations, Evaluations.AUCUNE)

    def test_valeur_inconnue_refusee_en_citant_les_valeurs_admises(self):
        with self.assertRaisesRegex(FormatInvalide,
                                    r"evaluations inconnu \['aucune', 'completes', 'livrable', 'quiz'\]"):
            depuis_dict(self.brut("sans"), "t.yaml", Reglages())

    def test_ancienne_cle_refusee(self):
        brut = parcours_brut()
        brut["blocs"][0]["modules"][0]["sans_exercices"] = True
        with self.assertRaisesRegex(FormatInvalide, "sans_exercices n'existe plus"):
            depuis_dict(brut, "t.yaml", Reglages())
