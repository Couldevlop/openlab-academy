"""Journée 25 : une seule porte d'entrée des données dans l'écran."""
import pathlib

ECRAN = pathlib.Path("accueil.py")
CHARGEMENT = pathlib.Path("vue/chargement.py")


def test_le_chargement_existe():
    assert CHARGEMENT.is_file()


def test_le_chargement_est_mis_en_cache():
    assert "cache_data" in CHARGEMENT.read_text(encoding="utf-8")


def test_le_chargement_expose_une_fonction():
    assert "def charger_effectif" in CHARGEMENT.read_text(encoding="utf-8")


def test_l_ecran_passe_par_le_chargement():
    assert "charger_effectif" in ECRAN.read_text(encoding="utf-8")


def test_l_ecran_n_importe_plus_la_source_directement():
    assert "from rh.exemple" not in ECRAN.read_text(encoding="utf-8")


def test_le_coeur_et_la_preparation_restent_sans_ecran():
    for chemin in ("rh/calculs.py", "rh/indicateurs.py", "vue/donnees.py", "vue/graphiques.py"):
        assert "streamlit" not in pathlib.Path(chemin).read_text(encoding="utf-8"), chemin


def test_l_ecran_garde_ses_quatre_parties():
    source = ECRAN.read_text(encoding="utf-8")
    for marque in ("st.title", "st.dataframe", ".metric(", "bar_chart"):
        assert marque in source, marque
