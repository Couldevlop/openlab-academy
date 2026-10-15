import pathlib
import tempfile
import unittest

from openlab_academy.seed.schema import SeedError, load_dir, validate

PARCOURS_DIR = pathlib.Path(__file__).parents[1] / "seed" / "parcours"


def projet(num="01", niveau="guide"):
    return {
        "titre": "P", "apres_module": num, "duree_h": 12, "niveau": niveau,
        "contexte": "c", "objectifs": ["o"], "fonctionnalites": ["f"], "stack": ["s"],
        "criteres_acceptation": ["a"], "exigences_specifiques": [], "livrables": ["l"],
    }


def parcours_valide():
    cap = projet()
    cap.pop("apres_module")
    cap["duree_h"] = 60
    cap["niveau"] = "autonome"
    return {
        "title": "T", "short_introduction": "s", "description": "d", "tags": ["x"],
        "blocs": [{"title": "B1", "modules": [{"num": "01", "title": "M", "contenu": "c", "livrable": "l"}]}],
        "portfolio": [projet() for _ in range(10)],
        "capstone": cap,
    }


class TestSchema(unittest.TestCase):
    def test_parcours_valide(self):
        validate(parcours_valide(), "t.yaml")

    def test_champ_manquant(self):
        p = parcours_valide()
        del p["blocs"][0]["modules"][0]["livrable"]
        with self.assertRaisesRegex(SeedError, r"t\.yaml: blocs\[0\]\.modules\[0\]\.livrable"):
            validate(p, "t.yaml")

    def test_portfolio_pas_10(self):
        p = parcours_valide()
        p["portfolio"].pop()
        with self.assertRaisesRegex(SeedError, r"portfolio: 10 projets attendus, 9 trouvés"):
            validate(p, "t.yaml")

    def test_apres_module_inconnu(self):
        p = parcours_valide()
        p["portfolio"][4]["apres_module"] = "99"
        with self.assertRaisesRegex(SeedError, r"portfolio\[4\]\.apres_module: module '99' inexistant"):
            validate(p, "t.yaml")

    def test_niveau_invalide(self):
        p = parcours_valide()
        p["portfolio"][0]["niveau"] = "facile"
        with self.assertRaisesRegex(SeedError, r"portfolio\[0\]\.niveau"):
            validate(p, "t.yaml")

    def test_salaire_interdit(self):
        p = parcours_valide()
        p["description"] = "Rémunération visée : 35–55 k€"
        with self.assertRaisesRegex(SeedError, r"description: rémunération en k€ interdite"):
            validate(p, "t.yaml")

    def test_fichiers_reels_valides(self):
        self.assertTrue(load_dir(PARCOURS_DIR))

    def test_liste_vide_refusee(self):
        p = parcours_valide()
        p["portfolio"][2]["criteres_acceptation"] = []
        with self.assertRaisesRegex(SeedError, r"portfolio\[2\]\.criteres_acceptation manquant"):
            validate(p, "t.yaml")

    def test_capstone_incomplet(self):
        p = parcours_valide()
        del p["capstone"]["livrables"]
        with self.assertRaisesRegex(SeedError, r"capstone\.livrables manquant"):
            validate(p, "t.yaml")

    def test_fichier_non_dictionnaire(self):
        with self.assertRaisesRegex(SeedError, r"t\.yaml: le fichier doit contenir un parcours"):
            validate(["pas", "un", "parcours"], "t.yaml")


class TestSecuriteYaml(unittest.TestCase):
    """OWASP A08 (intégrité / désérialisation non sûre) : aucun tag Python exécuté."""

    def _charger(self, texte):
        with tempfile.TemporaryDirectory() as d:
            pathlib.Path(d, "x.yaml").write_text(texte, encoding="utf-8")
            return load_dir(pathlib.Path(d))

    def test_tag_python_refuse(self):
        temoin = pathlib.Path(tempfile.gettempdir(), "openlab_pwned")
        temoin.unlink(missing_ok=True)
        with self.assertRaisesRegex(SeedError, r"x\.yaml: YAML invalide ou non sûr"):
            self._charger(f'!!python/object/apply:os.system ["touch {temoin}"]')
        self.assertFalse(temoin.exists())

    def test_yaml_malforme(self):
        with self.assertRaisesRegex(SeedError, r"x\.yaml: YAML invalide"):
            self._charger("title: [non fermé")
