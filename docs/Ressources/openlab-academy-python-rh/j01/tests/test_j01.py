"""Journée 01 : les quatre informations de la fiche."""
import fiche


def test_le_nom_est_un_texte_non_vide():
    assert isinstance(fiche.nom, str)
    assert fiche.nom.strip()


def test_le_poste_est_un_texte_non_vide():
    assert isinstance(fiche.poste, str)
    assert fiche.poste.strip()


def test_le_salaire_est_un_entier_positif():
    assert isinstance(fiche.salaire_fcfa, int)
    assert fiche.salaire_fcfa > 0


def test_le_resume_reprend_les_trois_informations():
    assert fiche.nom in fiche.resume
    assert fiche.poste in fiche.resume
    assert str(fiche.salaire_fcfa) in fiche.resume
    assert fiche.resume.endswith("FCFA")
