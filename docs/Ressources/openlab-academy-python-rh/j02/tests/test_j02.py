"""Journée 02 : salaire annuel et mise en forme des montants."""
from calculs import formater_fcfa, salaire_annuel

ESPACE = "\u00a0"


def test_salaire_annuel_sans_prime():
    assert salaire_annuel(250000, []) == 3000000


def test_salaire_annuel_avec_primes():
    assert salaire_annuel(250000, [100000, 150000]) == 3250000


def test_salaire_annuel_d_un_salaire_nul():
    assert salaire_annuel(0, []) == 0


def test_salaire_annuel_rend_un_entier():
    assert isinstance(salaire_annuel(250000.5, []), int)


def test_salaire_annuel_arrondit_le_resultat():
    assert salaire_annuel(1000.4, [0.2]) == 12005


def test_un_montant_a_sept_chiffres_est_groupe():
    assert formater_fcfa(3250000) == "3" + ESPACE + "250" + ESPACE + "000 FCFA"


def test_un_petit_montant_reste_sans_separateur():
    assert formater_fcfa(500) == "500 FCFA"


def test_le_montant_nul_est_accepte():
    assert formater_fcfa(0) == "0 FCFA"


def test_le_montant_est_arrondi_avant_affichage():
    assert formater_fcfa(1500.6) == "1" + ESPACE + "501 FCFA"


def test_aucune_decimale_dans_la_sortie():
    assert "." not in formater_fcfa(250000.0)


def test_la_sortie_se_termine_par_l_unite():
    assert formater_fcfa(12345).endswith(" FCFA")


def test_la_sortie_est_une_chaine():
    assert isinstance(formater_fcfa(10), str)


def test_les_deux_fonctions_se_combinent():
    assert formater_fcfa(salaire_annuel(250000, [])) == "3" + ESPACE + "000" + ESPACE + "000 FCFA"
