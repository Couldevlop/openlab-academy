import pathlib
import tempfile
import unittest

import yaml

from openlab_academy.domain.parcours import Niveau
from openlab_academy.domain.reglages import Reglages
from openlab_academy.infrastructure.yaml_source import PARCOURS_DIR, FormatInvalide, charger_dossier, depuis_dict
from openlab_academy.tests.fabriques import parcours_brut


class TestConversion(unittest.TestCase):
    def test_conversion_vers_le_domaine(self):
        p = depuis_dict(parcours_brut(), "t.yaml")
        self.assertEqual(p.blocs[0].modules[0].num, "01")
        self.assertEqual(p.portfolio[0].niveau, Niveau.GUIDE)
        self.assertEqual(p.portfolio[0].objectifs, ("o",))
        self.assertIsNone(p.capstone.apres_module)
        self.assertEqual(p.card_gradient, "Blue")

    def test_reglages_injectes_par_defaut(self):
        p = depuis_dict(parcours_brut(), "t.yaml", Reglages(heures_par_module=6))
        self.assertEqual((p.projets_attendus, p.heures_par_module), (10, 6))

    def test_parametres_du_parcours_surchargent_les_reglages(self):
        brut = parcours_brut()
        brut["parametres"] = {"projets_par_portfolio": 3, "heures_par_module": 10}
        brut["portfolio"] = brut["portfolio"][:3]
        p = depuis_dict(brut, "t.yaml", Reglages())
        self.assertEqual((p.projets_attendus, p.heures_par_module, len(p.portfolio)), (3, 10, 3))

    def test_parametre_inconnu_refuse(self):
        brut = parcours_brut()
        brut["parametres"] = {"bonus": 1}
        with self.assertRaisesRegex(FormatInvalide, r"t\.yaml: parametres\.bonus inconnu"):
            depuis_dict(brut, "t.yaml")

    def test_parametre_non_entier_refuse(self):
        brut = parcours_brut()
        brut["parametres"] = {"heures_par_module": "huit"}
        with self.assertRaisesRegex(FormatInvalide, r"parametres\.heures_par_module doit être un entier"):
            depuis_dict(brut, "t.yaml")

    def test_parametres_doivent_etre_un_dictionnaire(self):
        brut = parcours_brut()
        brut["parametres"] = ["heures_par_module"]
        with self.assertRaisesRegex(FormatInvalide, r"parametres doit être un dictionnaire"):
            depuis_dict(brut, "t.yaml")

    def test_numero_de_module_numerique_normalise(self):
        brut = parcours_brut()
        brut["blocs"][0]["modules"][0]["num"] = 1
        for pr in brut["portfolio"]:
            pr["apres_module"] = 1
        self.assertEqual(depuis_dict(brut, "t.yaml").portfolio[0].apres_module, "1")

    def test_champ_manquant_localise(self):
        brut = parcours_brut()
        del brut["blocs"][0]["modules"][0]["livrable"]
        with self.assertRaisesRegex(FormatInvalide, r"t\.yaml: blocs\[0\]\.modules\[0\]\.livrable manquant"):
            depuis_dict(brut, "t.yaml")

    def test_liste_vide_refusee(self):
        brut = parcours_brut()
        brut["portfolio"][2]["criteres_acceptation"] = []
        with self.assertRaisesRegex(FormatInvalide, r"portfolio\[2\]\.criteres_acceptation manquant"):
            depuis_dict(brut, "t.yaml")

    def test_exigences_specifiques_vides_acceptees_mais_cle_obligatoire(self):
        brut = parcours_brut()
        del brut["capstone"]["exigences_specifiques"]
        with self.assertRaisesRegex(FormatInvalide, r"capstone\.exigences_specifiques manquant"):
            depuis_dict(brut, "t.yaml")

    def test_element_de_liste_non_texte_refuse(self):
        brut = parcours_brut()
        brut["portfolio"][1]["criteres_acceptation"] = ["ok", {"Deux réservations": "une seule réussit"}]
        with self.assertRaisesRegex(FormatInvalide, r"portfolio\[1\]\.criteres_acceptation\[1\] doit être un texte"):
            depuis_dict(brut, "t.yaml")

    def test_niveau_inconnu(self):
        brut = parcours_brut()
        brut["portfolio"][0]["niveau"] = "facile"
        with self.assertRaisesRegex(FormatInvalide, r"portfolio\[0\]\.niveau 'facile' inconnu"):
            depuis_dict(brut, "t.yaml")

    def test_duree_non_entiere(self):
        brut = parcours_brut()
        brut["portfolio"][0]["duree_h"] = "douze"
        with self.assertRaisesRegex(FormatInvalide, r"portfolio\[0\]\.duree_h doit être un entier"):
            depuis_dict(brut, "t.yaml")

    def test_invariant_du_domaine_prefixe_par_la_source(self):
        brut = parcours_brut()
        brut["portfolio"].pop()
        with self.assertRaisesRegex(FormatInvalide, r"t\.yaml: portfolio: 10 projets attendus, 9 trouvés"):
            depuis_dict(brut, "t.yaml")

    def test_racine_non_dictionnaire(self):
        with self.assertRaisesRegex(FormatInvalide, r"t\.yaml: le fichier doit contenir un parcours"):
            depuis_dict(["pas", "un", "parcours"], "t.yaml")


class TestChargementDossier(unittest.TestCase):
    def _charger(self, **fichiers):
        with tempfile.TemporaryDirectory() as d:
            for nom, texte in fichiers.items():
                pathlib.Path(d, nom).write_text(texte, encoding="utf-8")
            return charger_dossier(pathlib.Path(d))

    def test_fichiers_charges_dans_l_ordre(self):
        a, b = parcours_brut(), parcours_brut()
        a["title"], b["title"] = "A", "B"
        lot = self._charger(**{"02-b.yaml": yaml.safe_dump(b), "01-a.yaml": yaml.safe_dump(a), "notes.txt": "x"})
        self.assertEqual([p.title for p in lot], ["A", "B"])

    def test_tag_python_jamais_execute(self):
        """OWASP A08 : désérialisation non sûre refusée."""
        temoin = pathlib.Path(tempfile.gettempdir(), "openlab_pwned")
        temoin.unlink(missing_ok=True)
        with self.assertRaisesRegex(FormatInvalide, r"x\.yaml: YAML invalide ou non sûr"):
            self._charger(**{"x.yaml": f'!!python/object/apply:os.system ["touch {temoin}"]'})
        self.assertFalse(temoin.exists())

    def test_yaml_malforme(self):
        with self.assertRaisesRegex(FormatInvalide, r"x\.yaml: YAML invalide"):
            self._charger(**{"x.yaml": "title: [non fermé"})

    def test_reglages_transmis_au_chargement(self):
        a = parcours_brut()
        lot = self._charger_avec(Reglages(heures_par_module=5), **{"a.yaml": yaml.safe_dump(a)})
        self.assertEqual(lot[0].heures_par_module, 5)

    def _charger_avec(self, reglages, **fichiers):
        with tempfile.TemporaryDirectory() as d:
            for nom, texte in fichiers.items():
                pathlib.Path(d, nom).write_text(texte, encoding="utf-8")
            return charger_dossier(pathlib.Path(d), reglages)

    def test_parcours_livres_valides(self):
        lot = charger_dossier(PARCOURS_DIR)
        self.assertTrue(lot)
        for p in lot:
            self.assertEqual(len(p.portfolio), 10)
