"""Journée 10 : la chaîne exacte de l'état par poste."""
from etats import ENTETE, etat_par_poste, normaliser

EFFECTIF = [
    {"nom": "Awa", "poste": "RH", "salaire_fcfa": 250000},
    {"nom": "Bakary", "poste": "  atelier  ", "salaire_fcfa": 180000},
    {"nom": "Céline", "poste": "rh", "salaire_fcfa": 420000},
]


def test_la_normalisation_ecrase_les_espaces_et_la_casse():
    assert normaliser("   awa   kone  ") == "Awa Kone"


def test_l_etat_commence_par_son_entete():
    assert etat_par_poste(EFFECTIF).splitlines()[0] == ENTETE


def test_les_postes_sont_regroupes_apres_normalisation():
    assert len(etat_par_poste(EFFECTIF).splitlines()) == 3


def test_la_chaine_exacte():
    attendu = "\n".join([ENTETE,
                         f"{'Atelier':<12}{1:>4}{180000:>12}",
                         f"{'Rh':<12}{2:>4}{670000:>12}"])
    assert etat_par_poste(EFFECTIF) == attendu


def test_un_effectif_vide_rend_le_seul_entete():
    assert etat_par_poste([]) == ENTETE


def test_la_fonction_rend_une_chaine():
    assert isinstance(etat_par_poste(EFFECTIF), str)
