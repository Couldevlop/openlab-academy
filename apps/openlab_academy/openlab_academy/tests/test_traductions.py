"""Garde-fou des traductions : chaque chaîne source de l'app a son anglais, les CSV sont bien formés."""
import csv
import re
import tempfile
import unittest
from pathlib import Path

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.translate import clear_cache, get_all_translations

RACINE = Path(__file__).resolve().parent.parent
TRADUCTIONS = RACINE / "translations"

# Littéral de chaîne Python ou Jinja passé à _(...) : guillemets doubles ou simples, échappements admis.
MOTIF = re.compile(r"""\b_\(\s*(?:"((?:[^"\\\n]|\\.)*)"|'((?:[^'\\\n]|\\.)*)')""")


def lire(fichier):
    with open(TRADUCTIONS / fichier, encoding="utf-8", newline="") as f:
        return list(csv.reader(f))


def fichiers_source(racine=RACINE):
    """Code Python de l'app (hors tests) et gabarits : les fichiers où vivent les chaînes à traduire."""
    fichiers = [p for p in racine.rglob("*.py") if "tests" not in p.relative_to(racine).parts]
    fichiers += [p for p in (racine / "templates").rglob("*") if p.suffix in (".html", ".txt")] \
        if (racine / "templates").is_dir() else []
    fichiers += [p for p in (racine / "www").rglob("*.html")] if (racine / "www").is_dir() else []
    return fichiers


def chaines_source(racine=RACINE):
    """Littéraux de `_("…")` du code Python (hors tests) et des gabarits .html/.txt."""
    trouvees = set()
    for chemin in fichiers_source(racine):
        texte = chemin.read_text(encoding="utf-8")
        for double, simple in MOTIF.findall(texte):
            trouvees.add(double or simple)
    return trouvees


# Un `_(` suivi d'un littéral, puis — après des espaces ou un retour à la ligne — d'un second
# littéral : Python les concatène avant l'appel, si bien que la clé réelle est la phrase entière
# alors que l'extracteur n'en voit que le premier morceau. La chaîne paraît traduite et ne l'est pas.
ACCOLES = re.compile(r"""\b_\(\s*(?:"(?:[^"\\\n]|\\.)*"|'(?:[^'\\\n]|\\.)*')\s*["']""")


def litteraux_accoles(racine=RACINE):
    """Fichiers et lignes où un `_()` reçoit plusieurs littéraux accolés."""
    trouves = []
    for chemin in sorted(fichiers_source(racine)):
        texte = chemin.read_text(encoding="utf-8")
        for trouve in ACCOLES.finditer(texte):
            trouves.append(f"{chemin.relative_to(racine)}:{texte[:trouve.start()].count(chr(10)) + 1}")
    return trouves


def manquantes(chaines):
    """Chaînes sources absentes de en.csv ou à traduction vide."""
    anglais = {l[0]: l[1] for l in lire("en.csv") if len(l) >= 2}
    return sorted(c for c in chaines if not anglais.get(c, "").strip())


class TestTraductions(unittest.TestCase):
    def test_toute_chaine_traduisible_a_son_anglais(self):
        self.assertEqual(manquantes(chaines_source()), [], "chaînes sans traduction dans translations/en.csv")

    def test_aucune_chaine_traduisible_n_est_coupee_en_deux_litteraux(self):
        """Python concatène deux littéraux accolés avant l'appel : la clé réelle est la phrase
        entière, l'extracteur n'en voit que le début. La chaîne paraît traduite et ne l'est pas."""
        self.assertEqual(litteraux_accoles(), [], "littéraux accolés dans un appel à _()")

    def test_les_litteraux_accoles_sont_bien_detectes(self):
        with tempfile.TemporaryDirectory() as tmp:
            racine = Path(tmp)
            (racine / "coupee.py").write_text('x = _(\n    "Un debut "\n    "et une fin")\n',
                                              encoding="utf-8")
            (racine / "entiere.py").write_text('y = _("Un debut et une fin")\n', encoding="utf-8")
            self.assertEqual(litteraux_accoles(racine), ["coupee.py:1"])

    def test_une_chaine_sans_anglais_est_signalee(self):
        self.assertEqual(manquantes({"Chaîne jamais traduite"}), ["Chaîne jamais traduite"])

    def test_l_extracteur_voit_les_deux_syntaxes_et_les_manques(self):
        with tempfile.TemporaryDirectory() as tmp:
            racine = Path(tmp)
            (racine / "templates").mkdir()
            (racine / "tests").mkdir()
            (racine / "a.py").write_text('x = _("Bonjour {0}")\ny = _(\'Au revoir\')\n', encoding="utf-8")
            (racine / "templates" / "m.html").write_text('<p>{{ _("Salut") }}</p>', encoding="utf-8")
            (racine / "tests" / "t.py").write_text('_("Ignoree")', encoding="utf-8")
            self.assertEqual(sorted(chaines_source(racine)), ["Au revoir", "Bonjour {0}", "Salut"])

    def test_fr_csv_non_vide(self):
        self.assertTrue(lire("fr.csv"))

    def test_csv_bien_formes(self):
        for fichier in ("en.csv", "fr.csv"):
            lignes = lire(fichier)
            cles = [l[0] for l in lignes]
            self.assertEqual(len(cles), len(set(cles)), f"doublon de clé dans {fichier}")
            for l in lignes:
                self.assertTrue(2 <= len(l) <= 3, f"{fichier} : {l!r}")
                self.assertTrue(l[0].strip() and l[1].strip(), f"{fichier} : {l!r}")


class TestSurchargesLms(FrappeTestCase):
    def setUp(self):
        clear_cache()

    def tearDown(self):
        clear_cache()

    def test_surcharges_lms_appliquees(self):
        fr = get_all_translations("fr")
        self.assertEqual(fr["Home"], "Accueil")
        self.assertEqual(fr["Enroll Now"], "S'inscrire")

    def test_le_bouton_du_quiz_valide_la_reponse(self):
        """LMS traduit « Check » par « Case à cocher », le nom d'un champ, alors que ce bouton valide la
        réponse de l'apprenant. L'erreur vient de lms/locale/fr.po ; notre surcharge la corrige."""
        self.assertEqual(get_all_translations("fr")["Check"], "Vérifier")
