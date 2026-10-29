import pathlib
import tempfile
import unittest

import yaml

from openlab_academy.domain.parcours import Annonce, Niveau, Parcours
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

    def test_cles_de_lancement_lues(self):
        brut = parcours_brut()
        brut.update(gratuit=True, acces_limite_a_la_cohorte=True, mise_en_avant=True)
        p = depuis_dict(brut, "t.yaml")
        self.assertEqual((p.gratuit, p.acces_limite_a_la_cohorte, p.mise_en_avant), (True, True, True))

    def test_cles_de_lancement_absentes_valent_faux(self):
        p = depuis_dict(parcours_brut(), "t.yaml")
        self.assertEqual((p.gratuit, p.acces_limite_a_la_cohorte, p.mise_en_avant), (False, False, False))

    def test_cle_de_lancement_non_booleenne_refusee(self):
        for valeur in (1, "oui"):
            brut = parcours_brut()
            brut["gratuit"] = valeur
            with self.subTest(valeur), self.assertRaisesRegex(FormatInvalide, "gratuit doit être un booléen"):
                depuis_dict(brut, "t.yaml")

    def test_sans_portfolio_si_zero_projet(self):
        brut = parcours_brut()
        brut["parametres"] = {"projets_par_portfolio": 0, "heures_par_module": 3}
        del brut["portfolio"]
        p = depuis_dict(brut, "t.yaml")
        modules = sum(len(b.modules) for b in p.blocs)
        self.assertEqual(p.portfolio, ())
        self.assertEqual(p.charge_horaire(), modules * 3 + p.capstone.duree_h)

    def test_portfolio_vide_refuse_si_projets_attendus(self):
        brut = parcours_brut()
        brut["portfolio"] = []
        with self.assertRaisesRegex(FormatInvalide, "portfolio manquant"):
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
        complets = [p for p in lot if isinstance(p, Parcours)]
        self.assertEqual(len(complets), 5)
        for p in complets:
            attendus = 0 if p.title == "IA agentique : comprendre, concevoir et maîtriser les agents IA" else 10
            self.assertEqual(len(p.portfolio), attendus, p.title)
        self.assertEqual(sorted(p.title for p in lot if isinstance(p, Annonce)),
                         ["Ingénieur Cybersécurité I", "Ingénieur Cybersécurité II"])


def critere_brut(code="clarte", poids=100, **autres):
    return {"code": code, "libelle": "Clarté", "poids": poids,
            "niveaux": [{"libelle": "Faible"}, {"libelle": "Bon", "descripteur": "Bien", "points": 5}], **autres}


CORRECTION_BRUTE = {"etapes": [{"etape": "formateur", "active": True, "delai_heures": 24, "expiration": "escalader"}],
                    "nb_pairs": 1}


class TestGrilleEtCorrection(unittest.TestCase):
    def test_sans_grille_ni_correction(self):
        p = depuis_dict(parcours_brut(), "t.yaml")
        m = p.blocs[0].modules[0]
        self.assertEqual((m.grille_cas, m.correction_cas, m.grille_livrable, m.correction_livrable),
                         (None, None, None, None))
        self.assertEqual((p.portfolio[0].grille, p.capstone.correction), (None, None))

    def test_grille_et_correction_d_un_module(self):
        brut = parcours_brut()
        m = brut["blocs"][0]["modules"][0]
        m.update(grille_mise_en_situation=[critere_brut(controles=["c1"])], correction_mise_en_situation=CORRECTION_BRUTE,
                 grille_livrable=[critere_brut("autre")], correction_livrable=CORRECTION_BRUTE)
        module = depuis_dict(brut, "t.yaml").blocs[0].modules[0]
        critere = module.grille_cas.criteres[0]
        self.assertEqual((critere.code, critere.description, critere.controles), ("clarte", "Clarté", ("c1",)))
        self.assertEqual([(n.libelle, n.descripteur, n.points) for n in critere.niveaux],
                         [("Faible", "Faible", 0), ("Bon", "Bien", 5)])
        self.assertEqual(module.correction_cas.nb_pairs, 1)
        self.assertEqual(module.grille_livrable.criteres[0].code, "autre")
        self.assertEqual(module.correction_livrable.nb_pairs, 1)

    def test_grille_et_correction_d_un_projet(self):
        brut = parcours_brut()
        brut["portfolio"][0].update(grille=[critere_brut()], correction=CORRECTION_BRUTE)
        brut["capstone"].update(grille=[critere_brut()])
        p = depuis_dict(brut, "t.yaml")
        self.assertEqual(p.portfolio[0].grille.criteres[0].poids, 100)
        self.assertEqual(p.portfolio[0].correction.nb_pairs, 1)
        self.assertIsNotNone(p.capstone.grille)

    def test_grille_invalide_message_clair(self):
        cas = [
            ("pas une liste", "x", r"t\.yaml: portfolio\[0\]\.grille doit être une liste"),
            ("poids 90", [critere_brut(poids=90)], r"portfolio\[0\]\.grille invalide : grille : total 90 %"),
            ("vide", [], r"portfolio\[0\]\.grille invalide : la grille n'a aucun critère"),
            ("critere texte", ["x"], r"grille\[0\] doit être un critère"),
            ("niveaux faux", [{**critere_brut(), "niveaux": ["x"]}], r"grille\[0\]\.niveaux doit être une liste"),
            ("poids texte", [critere_brut(poids="x")], r"grille\[0\]\.poids doit être un entier"),
            ("code manquant", [{k: v for k, v in critere_brut().items() if k != "code"}], r"grille\[0\]\.code manquant"),
            ("niveau unique", [{**critere_brut(), "niveaux": [{"libelle": "A"}]}], r"au moins 2 niveaux"),
        ]
        for nom, grille, message in cas:
            brut = parcours_brut()
            brut["portfolio"][0]["grille"] = grille
            with self.subTest(nom), self.assertRaisesRegex(FormatInvalide, message):
                depuis_dict(brut, "t.yaml")

    def test_booleens_refuses_ou_un_entier_est_attendu(self):
        brut = parcours_brut()
        brut["portfolio"][0]["duree_h"] = True
        with self.assertRaisesRegex(FormatInvalide, "duree_h doit être un entier"):
            depuis_dict(brut, "t.yaml")
        brut = parcours_brut()
        brut["parametres"] = {"heures_par_module": True}
        with self.assertRaisesRegex(FormatInvalide, "doit être un entier"):
            depuis_dict(brut, "t.yaml")
        brut = parcours_brut()
        brut["portfolio"][0]["grille"] = [critere_brut(poids=True)]
        with self.assertRaisesRegex(FormatInvalide, "poids doit être un entier"):
            depuis_dict(brut, "t.yaml")
        brut = parcours_brut()
        brut["blocs"][0]["modules"][0]["quiz"][0]["bonnes"] = [True]
        with self.assertRaisesRegex(FormatInvalide, "bonnes doit être une liste"):
            depuis_dict(brut, "t.yaml")

    def test_correction_invalide_message_clair(self):
        brut = parcours_brut()
        brut["blocs"][0]["modules"][0]["correction_livrable"] = {"etapes": [{"etape": "zzz"}]}
        with self.assertRaisesRegex(FormatInvalide, r"t\.yaml: blocs\[0\]\.modules\[0\]\.correction_livrable invalide"):
            depuis_dict(brut, "t.yaml")
