"""Ce que les trois règles doivent trouver — et ce qu'elles ne doivent surtout pas signaler."""
import detecter
import normaliser


def evenements():
    return normaliser.collecter()


def test_la_salve_de_connexions_est_detectee_une_seule_fois():
    alertes = detecter.force_brute(evenements())
    assert len(alertes) == 1, "une alerte par couple attaquant/compte, pas une par échec"
    alerte = alertes[0]
    assert alerte["acteur"] == "185.203.44.19"
    assert alerte["compte"] == "kone.a"
    assert alerte["horodatage"] == "2026-03-14T02:19:36Z", "l'alerte porte l'instant de la réussite"


def test_les_fautes_de_frappe_honnetes_ne_declenchent_rien():
    # quelques échecs suivis d'une réussite, c'est un employé qui se trompe de touche
    assert all(a["acteur"] == "185.203.44.19" for a in detecter.force_brute(evenements()))


def test_le_fichier_depose_puis_rappele_est_detecte():
    alertes = detecter.fichier_depose(evenements())
    assert len(alertes) == 1
    assert "/uploads/avatar.php" in alertes[0]["resume"]
    assert alertes[0]["acteur"] == "185.203.44.19"


def test_la_sortie_de_nuit_vers_l_exterieur_est_detectee():
    alertes = detecter.exfiltration(evenements())
    assert len(alertes) == 1
    assert alertes[0]["horodatage"] == "2026-03-14T02:41:22Z"
    assert "185.203.44.19" in alertes[0]["resume"]


def test_la_sauvegarde_nocturne_n_est_pas_une_exfiltration():
    # 900 Mo à 01:05, mais vers la baie interne : une règle qui crie ici sera coupée, puis plus rien
    # ne gardera la porte. C'est le piège de la séance.
    assert not [a for a in detecter.exfiltration(evenements()) if "10.20.9.5" in a["resume"]]


def test_l_analyse_complete_rend_les_trois_alertes_dans_l_ordre():
    alertes = detecter.analyser()
    assert [a["regle"] for a in alertes] == ["force-brute", "fichier-depose", "exfiltration"]
