import unittest

from openlab_academy.domain.grilles_derivees import grille_par_defaut
from openlab_academy.domain.reglages import CritereBareme, Reglages
from openlab_academy.domain.reglages_evaluation import ReglagesEvaluation, TypeExercice
from openlab_academy.tests.fabriques import projet


def controles(grille):
    return {c.libelle: c.controles for c in grille.criteres}


class TestGrilleParDefaut(unittest.TestCase):
    def test_generique_pour_mise_en_situation_et_livrable(self):
        for type_ in (TypeExercice.MISE_EN_SITUATION, TypeExercice.LIVRABLE):
            g = grille_par_defaut(type_, None, Reglages(), ReglagesEvaluation())
            self.assertEqual([c.libelle for c in g.criteres],
                             ["Pertinence", "Rigueur", "Clarté", "Ancrage dans le contexte ivoirien"])
            self.assertEqual([n.libelle for n in g.criteres[0].niveaux],
                             ["Insuffisant", "À consolider", "Satisfaisant", "Excellent"])

    def test_projet_sur_bareme_avec_controles(self):
        p = projet(criteres_acceptation=("A1", "A2"), exigences_specifiques=("S1",))
        r = Reglages(exigences_communes=("E1", "E2"))
        for type_ in (TypeExercice.PROJET, TypeExercice.CAPSTONE):
            c = controles(grille_par_defaut(type_, p, r, ReglagesEvaluation()))
            self.assertEqual(c["Fonctionnel"], ("A1", "A2"))
            self.assertEqual(c["Qualité & tests"], ("E1", "E2", "S1"))
            self.assertEqual(c["Sécurité"], ())

    def test_rubriques_absentes_du_bareme_repli_premier_et_dernier(self):
        r = Reglages(bareme=(CritereBareme("Alpha", 60), CritereBareme("Omega", 40)), exigences_communes=("E1",))
        c = controles(grille_par_defaut(TypeExercice.PROJET, projet(), r, ReglagesEvaluation()))
        self.assertEqual(c, {"Alpha": ("a",), "Omega": ("E1",)})

    def test_bareme_a_un_seul_critere_cumule(self):
        r = Reglages(bareme=(CritereBareme("Tout", 100),), exigences_communes=("E1",))
        c = controles(grille_par_defaut(TypeExercice.PROJET, projet(), r, ReglagesEvaluation()))
        self.assertEqual(c, {"Tout": ("a", "E1")})

    def test_projet_sans_projet_refuse(self):
        with self.assertRaises(ValueError):
            grille_par_defaut(TypeExercice.PROJET, None, Reglages(), ReglagesEvaluation())
