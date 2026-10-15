"""Habillage OpenLab de l'interface LMS (SPA) : injection de la feuille de style de la charte."""
FEUILLE = "/assets/openlab_academy/css/openlab.css"
LIEN = f'<link rel="stylesheet" href="{FEUILLE}">'


def injecter(html: str) -> str:
    """Ajoute la feuille OpenLab en fin de <head>, après les styles LMS, pour qu'elle prévale."""
    if FEUILLE in html or "</head>" not in html:
        return html
    return html.replace("</head>", f"{LIEN}</head>", 1)
