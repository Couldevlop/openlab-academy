"""Journée 11 : trois modules, et des imports qui ne vont que dans un sens."""
import contextlib
import importlib
import io
import pathlib

EFFECTIF = [{"nom": "Awa", "poste": "RH", "salaire_fcfa": 250000}]


def test_les_trois_fichiers_existent():
    for chemin in ("rh/calculs.py", "rh/etats.py", "main.py"):
        assert pathlib.Path(chemin).is_file(), chemin


def test_importer_un_module_n_affiche_rien():
    sortie = io.StringIO()
    with contextlib.redirect_stdout(sortie):
        for nom in ("rh.calculs", "rh.etats", "main"):
            importlib.import_module(nom)
    assert sortie.getvalue() == ""


def test_les_calculs_n_importent_rien_du_projet():
    source = pathlib.Path("rh/calculs.py").read_text(encoding="utf-8")
    assert "rh.etats" not in source
    assert "import main" not in source


def test_les_etats_appellent_les_calculs():
    source = pathlib.Path("rh/etats.py").read_text(encoding="utf-8")
    assert "rh.calculs" in source


def test_l_etat_se_rend_toujours_en_chaine():
    etats = importlib.import_module("rh.etats")
    assert isinstance(etats.etat_par_poste(EFFECTIF), str)


def test_le_point_d_entree_est_protege_par_la_garde():
    source = pathlib.Path("main.py").read_text(encoding="utf-8")
    assert "__main__" in source
