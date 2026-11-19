"""Ce que la collecte doit rendre. Ces tests sont rouges tant que `lire_annuaire` n'est pas écrit."""
import normaliser

ANNUAIRE = """date,evenement,compte,poste,resultat
2026-03-14T08:10:00Z,4624,awa.toure,POSTE-12,succes
2026-03-14T02:28:45Z,4672,kone.a,SRV-WEB-01,succes
"""


def test_l_annuaire_rend_un_evenement_par_ligne():
    assert len(normaliser.lire_annuaire(ANNUAIRE)) == 2


def test_une_ouverture_de_session_est_une_connexion():
    premier = normaliser.lire_annuaire(ANNUAIRE)[0]
    assert premier["action"] == "connexion"
    assert premier["compte"] == "awa.toure"
    assert premier["resultat"] == "succes"
    assert premier["source"] == "annuaire"


def test_une_attribution_de_privileges_se_distingue_d_une_connexion():
    # 4672 n'est pas une ouverture de session : c'est un compte qui reçoit des droits étendus,
    # et le confondre avec une connexion fait disparaître l'élévation du tableau de bord
    assert normaliser.lire_annuaire(ANNUAIRE)[1]["action"] == "privilege"


def test_l_annuaire_journalise_le_poste_et_non_l_adresse():
    evenement = normaliser.lire_annuaire(ANNUAIRE)[1]
    assert evenement["ip"] is None
    assert evenement["details"]["poste"] == "SRV-WEB-01"


def test_la_collecte_rassemble_les_quatre_sources_dans_l_ordre_du_temps():
    evenements = normaliser.collecter()
    assert {e["source"] for e in evenements} == {"web", "ssh", "pare-feu", "annuaire"}
    assert evenements == sorted(evenements, key=lambda e: e["horodatage"])
