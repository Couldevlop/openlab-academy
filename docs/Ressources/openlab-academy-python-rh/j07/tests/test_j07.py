"""Journée 07 : la fiche et la lecture sûre d'un champ."""
from fiches import CHAMPS, lire_champ, salarie


def fiche():
    return salarie("Awa Kone", "Assistante RH", "2024-03-01", 250000)


def test_la_fiche_porte_exactement_les_quatre_champs():
    assert sorted(fiche()) == sorted(CHAMPS)


def test_les_valeurs_sont_celles_qu_on_a_donnees():
    assert fiche()["nom"] == "Awa Kone"
    assert fiche()["salaire_fcfa"] == 250000


def test_lire_un_champ_present():
    assert lire_champ(fiche(), "poste") == "Assistante RH"


def test_lire_un_champ_absent_rend_la_valeur_par_defaut():
    assert lire_champ(fiche(), "telephone", "inconnu") == "inconnu"


def test_lire_un_champ_absent_sans_defaut_rend_rien():
    assert lire_champ(fiche(), "telephone") is None


def test_lire_un_champ_ne_modifie_pas_la_fiche():
    une_fiche = fiche()
    lire_champ(une_fiche, "telephone", "inconnu")
    assert sorted(une_fiche) == sorted(CHAMPS)
