"""Habillage OpenLab de l'interface LMS (SPA) : feuille de style de la charte et script du paiement des parcours."""
FEUILLE = "/assets/openlab_academy/css/openlab.css"
LIEN = f'<link rel="stylesheet" href="{FEUILLE}">'
SCRIPT_PAIEMENT = "/assets/openlab_academy/js/paiement.js"
SCRIPT = f'<script src="{SCRIPT_PAIEMENT}" defer></script>'


def injecter(html: str) -> str:
    """Ajoute en fin de <head>, chacun une seule fois : la feuille OpenLab (après les styles LMS, pour qu'elle
    prévale) et le script qui renvoie un parcours bloqué vers sa page de paiement."""
    if "</head>" not in html:
        return html
    ajouts = "".join(bloc for bloc, cle in ((LIEN, FEUILLE), (SCRIPT, SCRIPT_PAIEMENT)) if cle not in html)
    return html.replace("</head>", f"{ajouts}</head>", 1)
