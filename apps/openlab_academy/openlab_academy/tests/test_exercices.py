import unittest

from openlab_academy.domain.parcours import Bloc, Module, ParcoursInvalide, Question
from openlab_academy.infrastructure.yaml_source import FormatInvalide, depuis_dict
from openlab_academy.domain.reglages import Reglages
from openlab_academy.tests.fabriques import parcours, parcours_brut, question_brute


def question(**autres):
    champs = dict(enonce="Q ?", options=("a", "b", "c"), bonnes=(2,), explication="Parce que b.")
    champs.update(autres)
    return Question(**champs)


def module_complet(num="01", n=5):
    return Module(num, "M", "c", "l", quiz=tuple(question() for _ in range(n)), mise_en_situation="Cas pratique")


class TestQuestion(unittest.TestCase):
    def test_question_valide(self):
        q = question(bonnes=(1, 3))
        self.assertEqual((q.bonnes, q.choix_multiple), ((1, 3), True))
        self.assertFalse(question().choix_multiple)

    def test_nombre_d_options(self):
        for options in (("a",), tuple("abcdefg")):
            with self.subTest(n=len(options)), self.assertRaisesRegex(ParcoursInvalide, "2 à 6 options"):
                question(options=options, bonnes=(1,))

    def test_au_moins_une_bonne_reponse(self):
        with self.assertRaisesRegex(ParcoursInvalide, "au moins une bonne réponse"):
            question(bonnes=())

    def test_bonne_reponse_hors_options(self):
        with self.assertRaisesRegex(ParcoursInvalide, "bonne réponse 4 hors des options 1 à 3"):
            question(bonnes=(4,))

    def test_options_distinctes_et_non_vides(self):
        with self.assertRaisesRegex(ParcoursInvalide, "options en double"):
            question(options=("a", "a"), bonnes=(1,))
        with self.assertRaisesRegex(ParcoursInvalide, "option vide"):
            question(options=("a", " "), bonnes=(1,))

    def test_enonce_et_explication_obligatoires(self):
        with self.assertRaisesRegex(ParcoursInvalide, "énoncé manquant"):
            question(enonce="")
        with self.assertRaisesRegex(ParcoursInvalide, "explication manquante"):
            question(explication="")


class TestExercicesDuParcours(unittest.TestCase):
    def test_exercices_obligatoires_quand_regles(self):
        p = parcours(questions_par_quiz=5, blocs=(Bloc("B1", (module_complet(),)),))
        self.assertEqual(len(p.blocs[0].modules[0].quiz), 5)

    def test_nombre_de_questions_impose(self):
        with self.assertRaisesRegex(ParcoursInvalide, "module 01 : 5 questions attendues, 4 trouvées"):
            parcours(questions_par_quiz=5, blocs=(Bloc("B1", (module_complet(n=4),)),))

    def test_mise_en_situation_obligatoire(self):
        sans_cas = Module("01", "M", "c", "l", quiz=tuple(question() for _ in range(5)))
        with self.assertRaisesRegex(ParcoursInvalide, "module 01 : mise en situation manquante"):
            parcours(questions_par_quiz=5, blocs=(Bloc("B1", (sans_cas,)),))

    def test_sans_exercices_si_non_regles(self):
        self.assertEqual(parcours().questions_par_quiz, 0)


class TestSeanceSansExercices(unittest.TestCase):
    """Révision, atelier, challenge : une séance se déclare sans exercices, les autres gardent les leurs."""

    def seance(self, **champs):
        return parcours(questions_par_quiz=5, blocs=(Bloc("B1", (Module("01", "M", "c", "l", **champs),
                                                                 module_complet("02"))),))

    def test_declaration_explicite_acceptee(self):
        p = self.seance(sans_exercices=True)
        self.assertEqual((p.blocs[0].modules[0].quiz, len(p.blocs[0].modules[1].quiz)), ((), 5))

    def test_quiz_oublie_toujours_refuse(self):
        with self.assertRaisesRegex(ParcoursInvalide, "module 01 : 5 questions attendues, 0 trouvées"):
            self.seance()

    def test_declaration_contredite_par_un_quiz(self):
        with self.assertRaisesRegex(ParcoursInvalide, "module 01 : séance déclarée sans exercices"):
            self.seance(sans_exercices=True, quiz=tuple(question() for _ in range(5)))

    def test_declaration_contredite_par_une_mise_en_situation(self):
        with self.assertRaisesRegex(ParcoursInvalide, "module 01 : séance déclarée sans exercices"):
            self.seance(sans_exercices=True, mise_en_situation="Un cas")

    def test_cle_yaml_lue(self):
        brut = parcours_brut()
        module = brut["blocs"][0]["modules"][0]
        module.update(sans_exercices=True, quiz=[], mise_en_situation="")
        p = depuis_dict(brut, "t.yaml", Reglages())
        self.assertTrue(p.blocs[0].modules[0].sans_exercices)

    def test_cle_yaml_non_booleenne_refusee(self):
        brut = parcours_brut()
        brut["blocs"][0]["modules"][0]["sans_exercices"] = "oui"
        with self.assertRaisesRegex(FormatInvalide, "sans_exercices doit être un booléen"):
            depuis_dict(brut, "t.yaml")


class TestExercicesYaml(unittest.TestCase):
    def test_lecture_du_quiz_et_du_cas(self):
        p = depuis_dict(parcours_brut(), "t.yaml", Reglages())
        m = p.blocs[0].modules[0]
        self.assertEqual((len(m.quiz), m.mise_en_situation, p.questions_par_quiz), (5, "Cas pratique", 5))
        self.assertEqual(m.quiz[0].bonnes, (2,))

    def test_question_mal_formee_localisee(self):
        brut = parcours_brut()
        del brut["blocs"][0]["modules"][0]["quiz"][2]["explication"]
        with self.assertRaisesRegex(FormatInvalide, r"blocs\[0\]\.modules\[0\]\.quiz\[2\]\.explication manquant"):
            depuis_dict(brut, "t.yaml")

    def test_bonnes_reponses_entieres(self):
        brut = parcours_brut()
        brut["blocs"][0]["modules"][0]["quiz"][0]["bonnes"] = ["b"]
        with self.assertRaisesRegex(FormatInvalide, r"quiz\[0\]\.bonnes doit être une liste de numéros"):
            depuis_dict(brut, "t.yaml")

    def test_invariant_de_question_prefixe(self):
        brut = parcours_brut()
        brut["blocs"][0]["modules"][0]["quiz"][1]["bonnes"] = [9]
        with self.assertRaisesRegex(FormatInvalide, r"t\.yaml: .*bonne réponse 9 hors des options"):
            depuis_dict(brut, "t.yaml")

    def test_question_doit_etre_un_dictionnaire(self):
        brut = parcours_brut()
        brut["blocs"][0]["modules"][0]["quiz"][3] = "Quelle est la capitale ?"
        with self.assertRaisesRegex(FormatInvalide, r"quiz\[3\]\. doit être une question"):
            depuis_dict(brut, "t.yaml")

    def test_quiz_doit_etre_une_liste(self):
        brut = parcours_brut()
        brut["blocs"][0]["modules"][0]["quiz"] = "non"
        with self.assertRaisesRegex(FormatInvalide, r"quiz doit être une liste"):
            depuis_dict(brut, "t.yaml")
