"""Journée 06 : tri et tranches, sans effet de bord."""
from listes import effectif_trie, trois_derniers

NOMS = ["Daouda", "Awa", "Céline", "Bakary"]


def test_le_tri_rend_une_nouvelle_liste_triee():
    assert effectif_trie(NOMS) == ["Awa", "Bakary", "Céline", "Daouda"]


def test_le_tri_ne_modifie_pas_la_liste_recue():
    noms = list(NOMS)
    effectif_trie(noms)
    assert noms == NOMS


def test_le_tri_d_une_liste_vide_rend_une_liste_vide():
    assert effectif_trie([]) == []


def test_les_accents_sont_tries_sans_plantage():
    assert effectif_trie(["Cédric", "Céline"]) == ["Cédric", "Céline"]


def test_les_trois_derniers_d_une_liste_de_quatre():
    assert trois_derniers(NOMS) == ["Awa", "Céline", "Bakary"]


def test_les_trois_derniers_d_une_liste_de_deux():
    assert trois_derniers(["Awa", "Bakary"]) == ["Awa", "Bakary"]


def test_les_trois_derniers_d_une_liste_vide():
    assert trois_derniers([]) == []


def test_les_trois_derniers_ne_modifient_pas_la_liste_recue():
    noms = list(NOMS)
    trois_derniers(noms)
    assert noms == NOMS
