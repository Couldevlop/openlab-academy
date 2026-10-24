"""Génère les fichiers du logo OpenLab Academy (SVG vectoriels, PNG transparents, favicon) à partir d'un redessin
vectoriel du logo officiel. Textes : Montserrat (SIL Open Font License) convertie en tracés, aucune police requise
à l'affichage. Usage : python docs/charte/generer_charte.py [dossier des polices Montserrat]"""
import pathlib
import sys

from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.ttLib import TTFont

ICI = pathlib.Path(__file__).resolve().parent
SORTIE = ICI / "logo"
POLICES = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else \
    pathlib.Path("C:/Windows/Fonts")

BLEU_NUIT, ORANGE, BLEU_ROYAL, BLEU_CIEL, JAUNE = "#001E48", "#EC7623", "#244498", "#2890C8", "#FCD80F"
GRAPHITE, BLANC = "#1A1D24", "#FFFFFF"

# --- pictogramme (repère 1240 × 1184, page gauche ; la page droite est son miroir autour de x = 600) ----------
PAGE = "M 80 208 Q 345 212 578 352 L 578 1182 Q 345 1000 118 968 Z"
PAGE_FILET = "M 113 241 Q 340 246 551 372 L 551 1146 Q 345 990 148 940 Z"
TRACES = [  # (polyligne, centre de la pastille)
    ([(128, 322), (306, 322)], (327, 322)),
    ([(128, 428), (250, 428), (286, 391), (434, 391)], (455, 391)),
    ([(128, 462), (205, 462), (245, 493), (387, 493)], (408, 493)),
    ([(128, 605), (250, 605), (286, 568), (431, 568)], (452, 568)),
    ([(128, 660), (210, 660), (245, 627), (387, 627)], (408, 627)),
    ([(155, 732), (281, 732)], (302, 732)),
    ([(268, 795), (419, 795)], (440, 795)),
]
FEUILLETS = [  # pages qui s'envolent, côté gauche
    "M 150 24 L 158 46 Q 445 98 573 350 Q 478 62 150 24 Z",
    "M 98 141 L 104 163 Q 415 186 561 356 Q 410 146 98 141 Z",
]
ANNEAU = ("M 75 465 C 0 645 205 884 600 916 C 1010 948 1385 650 1122 236 "
          "C 1300 590 985 868 600 878 C 248 886 58 702 75 465 Z")


def miroir(chemin: str) -> str:
    """Miroir horizontal (x → 1200 − x) d'un chemin fait de M, L, Q, C, Z en coordonnées absolues."""
    sortie, est_x = [], True
    for j in chemin.split():
        if j.isalpha():
            sortie.append(j)
            est_x = True
            continue
        sortie.append(f"{1200 - float(j):g}" if est_x else j)
        est_x = not est_x
    return " ".join(sortie)


def pictogramme(c: dict) -> str:
    """Pictogramme dans son repère ; `c` donne les couleurs (pages, feuillets, anneau, détails, halo)."""
    morceaux = []
    for f in FEUILLETS:
        morceaux += [f'<path d="{f}" fill="{c["ciel"]}"/>', f'<path d="{miroir(f)}" fill="{c["ciel"]}"/>']
    for page, filet, couleur, m in ((PAGE, PAGE_FILET, c["gauche"], False),
                                    (miroir(PAGE), miroir(PAGE_FILET), c["droite"], True)):
        morceaux.append(f'<path d="{page}" fill="{couleur}"/>')
        morceaux.append(f'<path d="{filet}" fill="none" stroke="{c["detail"]}" stroke-width="11" '
                        f'stroke-linejoin="round"/>')
        for points, (cx, cy) in TRACES:
            pts = " ".join(f"{1200 - x if m else x},{y}" for x, y in points)
            morceaux.append(f'<polyline points="{pts}" fill="none" stroke="{c["detail"]}" stroke-width="10" '
                            f'stroke-linecap="round" stroke-linejoin="round"/>')
            morceaux.append(f'<circle cx="{1200 - cx if m else cx}" cy="{cy}" r="17" fill="{couleur}" '
                            f'stroke="{c["detail"]}" stroke-width="9"/>')
    # halo dessiné à part (paint-order n'est pas lu partout) : trait large, puis l'anneau par-dessus
    morceaux.append(f'<path d="{ANNEAU}" fill="{c["halo"]}" stroke="{c["halo"]}" stroke-width="16" '
                    f'stroke-linejoin="round"/>')
    morceaux.append(f'<path d="{ANNEAU}" fill="{c["anneau"]}"/>')
    return "\n    ".join(morceaux)


# --- logotype -----------------------------------------------------------------------------------------------
class Police:
    def __init__(self, fichier: str):
        self.f = TTFont(POLICES / fichier)
        self.glyphes = self.f.getGlyphSet()
        self.cmap = self.f.getBestCmap()
        self.hauteur_capitale = self.f["OS/2"].sCapHeight

    def ligne(self, texte: str, x: float, base: float, capitale: float, largeur: float, couleur: str,
              interlettrage: float | None = None) -> str:
        """Texte en tracés, capitales de hauteur `capitale`, sur exactement `largeur`. Sans `interlettrage`, l'espace
        entre lettres est calculé ; avec, c'est la chasse qui s'ajuste (Montserrat est plus large que le logotype)."""
        e = capitale / self.hauteur_capitale
        noms = [self.cmap[ord(ch)] for ch in texte]
        naturel = sum(self.glyphes[n].width * e for n in noms)
        if interlettrage is None:
            chasse, espace = 1.0, (largeur - naturel) / (len(noms) - 1)
        else:
            chasse, espace = (largeur - interlettrage * (len(noms) - 1)) / naturel, interlettrage
        avances = [self.glyphes[n].width * e * chasse for n in noms]
        chemins, curseur = [], x
        for nom, avance in zip(noms, avances):
            stylo = SVGPathPen(self.glyphes)
            self.glyphes[nom].draw(TransformPen(stylo, (e * chasse, 0, 0, -e, curseur, base)))
            if stylo.getCommands():
                chemins.append(stylo.getCommands())
            curseur += avance + espace
        return f'<path fill="{couleur}" d="{" ".join(chemins)}"/>'


GRAS = Police("Montserrat-Bold.ttf")
# relevés sur le logo officiel (1735 × 592)
OPENLAB = dict(texte="OPENLAB", x=692, base=305, capitale=166, largeur=1017, interlettrage=16)
ACADEMY = dict(texte="ACADEMY", x=703, base=422, capitale=73, largeur=985)
SIGNATURE = dict(texte="DIVISION FORMATION – OPENLAB CONSULTING", x=700, base=514, capitale=29, largeur=995)

COULEURS = {
    "couleur": dict(gauche=BLEU_ROYAL, droite=ORANGE, ciel=BLEU_CIEL, anneau=JAUNE, detail=BLANC, halo=BLANC,
                    openlab=BLEU_NUIT, academy=ORANGE, signature=GRAPHITE),
    "reserve": dict(gauche=BLEU_ROYAL, droite=ORANGE, ciel=BLEU_CIEL, anneau=JAUNE, detail=BLANC, halo=BLEU_NUIT,
                    openlab=BLANC, academy=ORANGE, signature=BLANC),
    "mono-nuit": dict(gauche=BLEU_NUIT, droite=BLEU_NUIT, ciel=BLEU_NUIT, anneau=BLEU_NUIT, detail=BLANC,
                      halo=BLANC, openlab=BLEU_NUIT, academy=BLEU_NUIT, signature=BLEU_NUIT),
    "mono-blanc": dict(gauche=BLANC, droite=BLANC, ciel=BLANC, anneau=BLANC, detail=BLEU_NUIT, halo=BLEU_NUIT,
                       openlab=BLANC, academy=BLANC, signature=BLANC),
}
SUR_FONCE = ("reserve", "mono-blanc")  # variantes conçues pour un fond bleu nuit


def svg(largeur: int, hauteur: int, corps: str, fond: str | None) -> str:
    rect = f'<rect width="{largeur}" height="{hauteur}" fill="{fond}"/>\n  ' if fond else ""
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {largeur} {hauteur}" width="{largeur}" '
            f'height="{hauteur}" role="img" aria-label="OpenLab Academy">\n  <title>OpenLab Academy</title>\n'
            f'  {rect}{corps}\n</svg>\n')


def horizontal(c: dict, signature: bool) -> tuple[int, int, str]:
    picto = f'<g transform="translate(40 4) scale(0.5)">\n    {pictogramme(c)}\n  </g>'
    textes = [GRAS.ligne(**OPENLAB, couleur=c["openlab"]), GRAS.ligne(**ACADEMY, couleur=c["academy"])]
    if signature:
        textes.append(GRAS.ligne(**SIGNATURE, couleur=c["signature"]))
    return 1760, 600, picto + "\n  " + "\n  ".join(textes)


def compact(c: dict) -> tuple[int, int, str]:
    """En-têtes et e-mails : pictogramme ramené à la hauteur du texte (du haut d'OPENLAB à la base d'ACADEMY)."""
    picto = f'<g transform="translate(16 10) scale(0.25)">\n    {pictogramme(c)}\n  </g>'
    textes = [GRAS.ligne(**{**OPENLAB, "x": 348, "base": 185}, couleur=c["openlab"]),
              GRAS.ligne(**{**ACADEMY, "x": 359, "base": 302}, couleur=c["academy"])]
    return 1390, 316, picto + "\n  " + "\n  ".join(textes)


def carre(c: dict) -> tuple[int, int, str]:
    """Pictogramme centré dans un carré, avec sa zone de protection."""
    return 1400, 1400, f'<g transform="translate(80 108)">\n    {pictogramme(c)}\n  </g>'


def ecrire_tout() -> list[pathlib.Path]:
    SORTIE.mkdir(exist_ok=True)
    fichiers = []
    for variante, c in COULEURS.items():
        for nom, (l, h, corps) in {f"openlab-academy-{variante}": horizontal(c, True),
                                    f"openlab-academy-court-{variante}": horizontal(c, False),
                                    f"openlab-academy-compact-{variante}": compact(c),
                                    f"pictogramme-{variante}": carre(c)}.items():
            fonds = (None, BLEU_NUIT) if variante in SUR_FONCE else (None,)
            for fond in fonds:
                fichier = SORTIE / f"{nom}{'-sur-fond' if fond else ''}.svg"
                fichier.write_text(svg(l, h, corps, fond), encoding="utf-8", newline="\n")
                fichiers.append(fichier)
    return fichiers


# --- images matricielles (PNG transparents, favicon) -----------------------------------------------------------
def rendre(fichier: pathlib.Path, largeur: int):
    """PNG RGBA : rendu sur blanc et sur noir, l'écart donne l'opacité (le moteur de rendu ignore la transparence)."""
    import numpy as np
    from PIL import Image
    from reportlab.graphics import renderPM
    from svglib.svglib import svg2rlg

    def sur(fond: int):
        dessin = svg2rlg(str(fichier))
        e = largeur / dessin.width
        dessin.width, dessin.height = dessin.width * e, dessin.height * e
        dessin.scale(e, e)
        return np.asarray(renderPM.drawToPIL(dessin, bg=fond).convert("RGB"), dtype=np.float64)

    blanc, noir = sur(0xFFFFFF), sur(0x000000)
    alpha = np.clip(255 - (blanc - noir).mean(axis=2), 0, 255)
    couleur = np.where(alpha[..., None] > 0, noir * 255 / np.maximum(alpha[..., None], 1), 0)
    rgba = np.dstack([np.clip(couleur, 0, 255), alpha]).astype(np.uint8)
    return Image.fromarray(rgba, "RGBA")


def ecrire_images() -> list[pathlib.Path]:
    from PIL import Image

    png = SORTIE / "png"
    png.mkdir(exist_ok=True)
    fichiers = []
    for nom, largeurs in {"openlab-academy-couleur": (480, 960, 1920), "openlab-academy-court-couleur": (460, 920),
                          "openlab-academy-compact-couleur": (460, 920),
                          "openlab-academy-reserve": (960, 1920), "openlab-academy-court-reserve": (460, 920),
                          "pictogramme-couleur": (64, 192, 512, 1024), "pictogramme-reserve": (512,),
                          "openlab-academy-mono-nuit": (960,), "openlab-academy-mono-blanc": (960,)}.items():
        for largeur in largeurs:
            cible = png / f"{nom}-{largeur}.png"
            rendre(SORTIE / f"{nom}.svg", largeur).save(cible, optimize=True)
            fichiers.append(cible)
    # icônes : favicon multi-tailles, icône d'écran d'accueil (fond blanc, iOS refuse la transparence)
    picto = rendre(SORTIE / "pictogramme-couleur.svg", 512)
    favicon = SORTIE / "favicon.ico"
    picto.save(favicon, sizes=[(16, 16), (32, 32), (48, 48), (64, 64)])
    pomme = Image.new("RGBA", (180, 180), "white")
    pomme.alpha_composite(picto.resize((160, 160), Image.LANCZOS), (10, 10))
    pomme.convert("RGB").save(SORTIE / "apple-touch-icon.png", optimize=True)
    # vignette de partage (réseaux sociaux) : logo en réserve sur bleu nuit, 1200 × 630
    vignette = Image.new("RGBA", (1200, 630), BLEU_NUIT)
    logo = rendre(SORTIE / "openlab-academy-reserve.svg", 960)
    vignette.alpha_composite(logo, ((1200 - logo.width) // 2, (630 - logo.height) // 2))
    vignette.convert("RGB").save(SORTIE / "vignette-partage.png", optimize=True)
    return fichiers + [favicon, SORTIE / "apple-touch-icon.png", SORTIE / "vignette-partage.png"]


if __name__ == "__main__":
    for f in ecrire_tout() + ecrire_images():
        print(f.relative_to(ICI))
