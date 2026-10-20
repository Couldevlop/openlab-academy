import unittest

from openlab_academy.domain.grille import Critere, Grille, GrilleInvalide, Niveau, grille_generique, grille_projet
from openlab_academy.domain.reglages import BAREME_DEFAUT, CritereBareme

NIVEAUX = ("Insuffisant", "Passable", "Bien", "Excellent")


def _grille(poids=(40, 60)):
    return grille_generique((("Fonctionnel", poids[0]), ("Qualité", poids[1])), NIVEAUX)


class TestValidation(unittest.TestCase):
    def test_poids_total_different_de_100(self):
        with self.assertRaisesRegex(GrilleInvalide, "total 90 %"):
            _grille((40, 50))

    def test_moins_de_deux_niveaux(self):
        with self.assertRaisesRegex(GrilleInvalide, "au moins 2 niveaux"):
            grille_generique((("A", 100),), ("Seul",))

    def test_points_non_strictement_croissants(self):
        niveaux = (Niveau("a", "a", 0), Niveau("b", "b", 0))
        with self.assertRaisesRegex(GrilleInvalide, "strictement croissants"):
            Critere("a", "A", "A", 100, niveaux)

    def test_codes_en_double(self):
        with self.assertRaisesRegex(GrilleInvalide, "en double"):
            grille_generique((("Qualité", 50), ("qualite", 50)), NIVEAUX)

    def test_aucun_critere(self):
        with self.assertRaisesRegex(GrilleInvalide, "aucun critère"):
            Grille(())

    def test_code_manquant(self):
        with self.assertRaisesRegex(GrilleInvalide, "code de critère manquant"):
            Critere(" ", "A", "A", 100, (Niveau("a", "a", 0), Niveau("b", "b", 1)))

    def test_poids_non_positif(self):
        with self.assertRaisesRegex(GrilleInvalide, "poids doit être positif"):
            Critere("a", "A", "A", 0, (Niveau("a", "a", 0), Niveau("b", "b", 1)))


class TestNote(unittest.TestCase):
    def test_tous_au_max(self):
        self.assertEqual(_grille().note({"fonctionnel": 3, "qualite": 3}, 20), 20.0)

    def test_tous_au_min(self):
        self.assertEqual(_grille().note({"fonctionnel": 0, "qualite": 0}, 20), 0.0)

    def test_mixte(self):
        self.assertEqual(_grille().note({"fonctionnel": 3, "qualite": 0}, 20), 8.0)

    def test_arrondi_au_demi_point(self):
        # 40 % * 1/3 = 13,33 % de 20 = 2,67 -> 2,5
        self.assertEqual(_grille().note({"fonctionnel": 1, "qualite": 0}, 20), 2.5)

    def test_critere_absent(self):
        with self.assertRaisesRegex(GrilleInvalide, "niveau manquant"):
            _grille().note({"fonctionnel": 3}, 20)

    def test_niveau_inexistant(self):
        with self.assertRaisesRegex(GrilleInvalide, "niveau 4 inexistant"):
            _grille().note({"fonctionnel": 4, "qualite": 0}, 20)
        with self.assertRaisesRegex(GrilleInvalide, "niveau -1 inexistant"):
            _grille().note({"fonctionnel": -1, "qualite": 0}, 20)


class TestEmpreinteEtSerialisation(unittest.TestCase):
    def test_empreinte_stable(self):
        self.assertEqual(_grille().empreinte(), _grille().empreinte())
        self.assertEqual(len(_grille().empreinte()), 64)

    def test_empreinte_change_si_un_descripteur_change(self):
        g = _grille()
        c0 = g.criteres[0]
        niveaux = (Niveau("Insuffisant", "autre texte", 0),) + c0.niveaux[1:]
        modifiee = Grille((Critere(c0.code, c0.libelle, c0.description, c0.poids, niveaux),) + g.criteres[1:])
        self.assertNotEqual(g.empreinte(), modifiee.empreinte())

    def test_aller_retour(self):
        g = grille_projet(BAREME_DEFAUT, {"Sécurité": ("OWASP",)}, NIVEAUX)
        self.assertEqual(Grille.depuis_dict(g.vers_dict()), g)

    def test_depuis_dict_sans_controles(self):
        d = _grille().vers_dict()
        for c in d["criteres"]:
            del c["controles"]
        self.assertEqual(Grille.depuis_dict(d), _grille())


class TestFabriques(unittest.TestCase):
    def test_generique_points_et_code(self):
        c = _grille().criteres[1]
        self.assertEqual((c.code, c.libelle, c.poids), ("qualite", "Qualité", 60))
        self.assertEqual([n.points for n in c.niveaux], [0, 1, 2, 3])

    def test_projet_un_critere_par_entree_avec_controles(self):
        bareme = (CritereBareme("Qualité & tests", 60), CritereBareme("Sécurité", 40))
        g = grille_projet(bareme, {"Sécurité": ("OWASP de base",)}, NIVEAUX)
        self.assertEqual([c.code for c in g.criteres], ["qualite_tests", "securite"])
        self.assertEqual([c.poids for c in g.criteres], [60, 40])
        self.assertEqual(g.criteres[0].controles, ())
        self.assertEqual(g.criteres[1].controles, ("OWASP de base",))
