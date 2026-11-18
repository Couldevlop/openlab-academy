"""Journée 14 : les trois tests que vous écrivez vous-même."""


def verifier_la_borne_des_douze_mois(droit_aux_conges):
    """Le droit s'ouvre à douze mois révolus, borne comprise."""
    assert droit_aux_conges(12) is True


def verifier_le_mois_precedent(droit_aux_conges):
    """À onze mois, le droit n'est pas encore ouvert."""
    assert droit_aux_conges(11) is False


def verifier_le_refus_d_une_anciennete_negative(droit_aux_conges):
    """Une ancienneté négative est une donnée fausse, pas un cas métier."""
    leve = False
    try:
        droit_aux_conges(-1)
    except ValueError:
        leve = True
    assert leve
