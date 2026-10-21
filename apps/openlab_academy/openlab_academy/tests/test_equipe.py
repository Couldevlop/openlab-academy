import unittest

from openlab_academy.domain.equipe import Equipe, EquipeEffective, resoudre_equipe
from openlab_academy.domain.reglages import ReglagesInvalides

LMS = ("prof.lms@x.ci",)


def resoudre(*equipes, cours="CRS1", cohorte="C1", exercice="EX1"):
    return resoudre_equipe(equipes, cours, cohorte, exercice, LMS)


class TestEquipe(unittest.TestCase):
    def test_une_seule_cible(self):
        with self.assertRaisesRegex(ReglagesInvalides, "une seule cible"):
            Equipe(cours="CRS1", cohorte="C1", titulaires=("a@x.ci",))

    def test_equipe_vide_refusee(self):
        with self.assertRaisesRegex(ReglagesInvalides, "au moins"):
            Equipe(cohorte="C1")

    def test_membre_en_double_refuse(self):
        for titulaires, suppleants in ((("a@x.ci", "a@x.ci"), ()), (("a@x.ci",), ("a@x.ci",))):
            with self.subTest(titulaires=titulaires, suppleants=suppleants), \
                    self.assertRaisesRegex(ReglagesInvalides, "a@x.ci"):
                Equipe(cohorte="C1", titulaires=titulaires, suppleants=suppleants)

    def test_niveau_et_libelle(self):
        self.assertEqual([(e.niveau, e.libelle) for e in (
            Equipe(responsable="r@x.ci"), Equipe(cours="CRS1", responsable="r@x.ci"),
            Equipe(cohorte="C1", responsable="r@x.ci"), Equipe(exercice="EX1", responsable="r@x.ci"))],
            [(0, "global"), (1, "cours CRS1"), (2, "cohorte C1"), (3, "exercice EX1")])


class TestResoudreEquipe(unittest.TestCase):
    def test_sans_equipe_formateurs_lms_et_aucun_recours(self):
        self.assertEqual(resoudre(), EquipeEffective(LMS, (), "", {"titulaires": "formateurs LMS",
                                                                    "suppleants": "aucun", "responsable": "aucun"}))

    def test_champ_par_champ_du_plus_specifique_au_global(self):
        e = resoudre(Equipe(responsable="g@x.ci", suppleants=("sg@x.ci",)),
                     Equipe(cours="CRS1", titulaires=("t1@x.ci", "t2@x.ci")),
                     Equipe(cohorte="C1", suppleants=("s1@x.ci", "s2@x.ci")),
                     Equipe(exercice="EX1", titulaires=("t3@x.ci",)))
        self.assertEqual((e.titulaires, e.suppleants, e.responsable), (("t3@x.ci",), ("s1@x.ci", "s2@x.ci"), "g@x.ci"))
        self.assertEqual(e.provenance, {"titulaires": "exercice EX1", "suppleants": "cohorte C1",
                                        "responsable": "global"})

    def test_equipes_d_autres_cibles_ignorees(self):
        e = resoudre(Equipe(cours="CRS2", titulaires=("x@x.ci",)), Equipe(cohorte="C2", suppleants=("y@x.ci",)),
                     Equipe(exercice="EX2", responsable="z@x.ci"))
        self.assertEqual((e.titulaires, e.suppleants, e.responsable), (LMS, (), ""))

    def test_sans_cohorte_ni_cours(self):
        e = resoudre(Equipe(cohorte="C1", suppleants=("s@x.ci",)), Equipe(cours="CRS1", responsable="r@x.ci"),
                     cours=None, cohorte=None)
        self.assertEqual((e.suppleants, e.responsable), ((), ""))
