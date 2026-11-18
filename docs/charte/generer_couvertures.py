"""Génère les images de couverture des parcours (1200 × 675, JPEG) aux couleurs de la charte.

Pas de photographie de banque d'images (charte §4) : chaque couverture est dessinée, fond bleu nuit gravé du
motif de circuit imprimé du logo, un glyphe propre au domaine, le surtitre et le titre du parcours en Montserrat
converti en tracés, et le filet quatre couleurs en pied. Le rendu ne dépend donc d'aucune police installée côté
navigateur.

Usage : python docs/charte/generer_couvertures.py [dossier des polices Montserrat]
Sortie : apps/openlab_academy/openlab_academy/data/ressources/couverture-<parcours>.jpg
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import generer_charte as charte  # noqa: E402  (le chemin doit être posé avant l'import)
from generer_charte import BLANC, BLEU_CIEL, BLEU_NUIT, BLEU_ROYAL, JAUNE, ORANGE  # noqa: E402

ICI = pathlib.Path(__file__).resolve().parent
SORTIE = ICI.parent.parent / "apps/openlab_academy/openlab_academy/data/ressources"
LARGEUR, HAUTEUR = 1200, 675
MARGE = 86
# la vignette du catalogue recadre la couverture : tout ce qui compte tient entre ces deux hauteurs
HAUT_SUR, BAS_SUR = 150, 540
SIGNATURE = 524
GRAS = charte.GRAS
REGULIER = charte.Police("Montserrat-Regular.ttf")


# --- fond ------------------------------------------------------------------------------------------------------
def melange(couleur: str, fond: str, part: float) -> str:
    """Couleur posée à `part` sur `fond`, calculée ici : le rendu matriciel n'applique pas toujours `opacity`."""
    a = [int(couleur[i:i + 2], 16) for i in (1, 3, 5)]
    b = [int(fond[i:i + 2], 16) for i in (1, 3, 5)]
    return "#" + "".join(f"{round(x * part + y * (1 - part)):02X}" for x, y in zip(a, b))


def circuit(part: float = 0.16) -> str:
    """Pistes et pastilles reprises du pictogramme, gravées en filigrane dans la moitié droite du fond
    (charte §4) : jamais derrière le titre, qui doit rester net."""
    teinte = melange(BLANC, BLEU_NUIT, part)
    morceaux = []
    for decalage in (600, 980):
        for points, (cx, cy) in charte.TRACES:
            pts = " ".join(f"{x * 0.58 + decalage:g},{y * 0.58 + 40:g}" for x, y in points)
            morceaux.append(f'<polyline points="{pts}" fill="none" stroke="{teinte}" stroke-width="5" '
                            f'stroke-linecap="round" stroke-linejoin="round"/>')
            morceaux.append(f'<circle cx="{cx * 0.58 + decalage:g}" cy="{cy * 0.58 + 40:g}" r="9" '
                            f'fill="none" stroke="{teinte}" stroke-width="5"/>')
    return "".join(morceaux)


def filet() -> str:
    """Filet quatre couleurs du logo, en pied de couverture."""
    bandes = ((0, 0.34, BLEU_ROYAL), (0.34, 0.16, BLEU_CIEL), (0.50, 0.34, ORANGE), (0.84, 0.16, JAUNE))
    return "".join(f'<rect x="{d * LARGEUR:g}" y="{HAUTEUR - 12}" width="{l * LARGEUR:g}" height="12" '
                   f'fill="{c}"/>' for d, l, c in bandes)


def voile() -> str:
    """Pan diagonal en bleu royal assourdi : il donne du relief au fond sans teinter la couverture (un mélange
    avec le jaune ou l'orange virerait au terne). La couleur du domaine reste au surtitre et au glyphe."""
    return (f'<path d="M {LARGEUR * 0.56:g} 0 L {LARGEUR} 0 L {LARGEUR} {HAUTEUR} L {LARGEUR * 0.38:g} {HAUTEUR} Z" '
            f'fill="{melange(BLEU_ROYAL, BLEU_NUIT, 0.26)}"/>')


# --- glyphes de domaine ------------------------------------------------------------------------------------------
def _trait(d: str, couleur: str, epaisseur: int = 9) -> str:
    return (f'<path d="{d}" fill="none" stroke="{couleur}" stroke-width="{epaisseur}" stroke-linecap="round" '
            f'stroke-linejoin="round"/>')


def glyphe_statistique(c: str) -> str:
    """Nuage de points et courbe d'ajustement : la data science."""
    points = [(0, 150), (46, 118), (92, 126), (138, 84), (184, 92), (230, 46), (276, 54), (322, 14)]
    return ("".join(f'<circle cx="{x}" cy="{y}" r="11" fill="{c}"/>' for x, y in points)
            + _trait("M 0 168 Q 160 140 330 6", c, 7))


def glyphe_code(c: str) -> str:
    """Chevrons et barre oblique : écrire du code."""
    return (_trait("M 96 32 L 20 96 L 96 160", c, 12) + _trait("M 238 32 L 314 96 L 238 160", c, 12)
            + _trait("M 190 20 L 144 172", c, 12))


def glyphe_agents(c: str) -> str:
    """Nœuds reliés à un nœud central : un modèle et ses outils."""
    centre, rayon = (166, 96), 74
    noeuds = [(166, 22), (240, 96), (166, 170), (92, 96)]
    liens = "".join(_trait(f"M {centre[0]} {centre[1]} L {x} {y}", c, 6) for x, y in noeuds)
    return (liens + f'<circle cx="{centre[0]}" cy="{centre[1]}" r="26" fill="{c}"/>'
            + "".join(f'<circle cx="{x}" cy="{y}" r="16" fill="none" stroke="{c}" stroke-width="8"/>'
                      for x, y in noeuds) + f'<circle cx="{centre[0]}" cy="{centre[1]}" r="{rayon}" fill="none" '
            f'stroke="{c}" stroke-width="4" opacity="0.45"/>')


def glyphe_pipeline(c: str) -> str:
    """Entrepôt et flux : les pipelines de données."""
    cyl = []
    for x in (14, 214):
        cyl.append(f'<ellipse cx="{x + 56}" cy="40" rx="56" ry="20" fill="none" stroke="{c}" stroke-width="9"/>')
        cyl.append(_trait(f"M {x} 40 L {x} 132", c))
        cyl.append(_trait(f"M {x + 112} 40 L {x + 112} 132", c))
        cyl.append(f'<ellipse cx="{x + 56}" cy="132" rx="56" ry="20" fill="none" stroke="{c}" stroke-width="9"/>')
    fleche = _trait("M 136 86 L 196 86", c) + _trait("M 176 70 L 196 86 L 176 102", c)
    return "".join(cyl) + fleche


def glyphe_bouclier(c: str, double: bool = False) -> str:
    """Bouclier, doublé en arrière-plan pour le second parcours (la suite du cursus) : la cybersécurité."""
    forme = "M 96 14 L 178 46 L 178 104 Q 178 158 96 182 Q 14 158 14 104 L 14 46 Z"
    fond = ""
    if double:
        pale = melange(c, BLEU_NUIT, 0.45)
        fond = (f'<g transform="translate(128 26) scale(0.84)">{_trait(forme, pale, 11)}</g>'
                f'<path d="{forme}" fill="{BLEU_NUIT}" opacity="0.92"/>')
    return fond + _trait(forme, c, 10) + _trait("M 58 100 L 86 128 L 138 70", c, 10)


def glyphe_escalier(c: str) -> str:
    """Marches qui montent, une par journée : un parcours quotidien se gravit."""
    marches = []
    for i in range(4):
        x, y = 14 + i * 76, 160 - i * 40
        marches.append(_trait(f"M {x} {y} L {x + 76} {y} L {x + 76} {y - 40}", c, 11))
    return "".join(marches) + f'<circle cx="{14 + 4 * 76}" cy="{160 - 4 * 40 + 6}" r="18" fill="{c}"/>'


def glyphe_boucle(c: str) -> str:
    """Boucle d'exécution d'un agent : percevoir, décider, agir."""
    return (_trait("M 60 96 A 76 76 0 1 1 136 172", c, 11)
            + _trait("M 112 150 L 136 174 L 112 198", c, 11)
            + f'<circle cx="136" cy="96" r="20" fill="{c}"/>')


# --- texte ---------------------------------------------------------------------------------------------------
def lignes(titre: str, maximum: int) -> list[str]:
    """Coupe le titre en lignes d'au plus `maximum` caractères, sans jamais couper un mot."""
    sortie, courante = [], ""
    for mot in titre.split():
        essai = f"{courante} {mot}".strip()
        if len(essai) > maximum and courante:
            sortie.append(courante)
            courante = mot
        else:
            courante = essai
    return sortie + [courante] if courante else sortie


def titre_compose(texte: str, largeur_max: float, couleur: str, haut: float = 236, bas: float = 448) -> str:
    """Titre cadré à gauche, dans la bande laissée libre entre le surtitre et la signature : la taille des
    capitales descend jusqu'à ce que le bloc tienne en trois lignes au plus, puis le bloc est centré dans la
    bande. Un titre long reste donc lisible sans jamais mordre sur le logo."""
    for capitale in (58, 51, 45, 40):
        decoupe = lignes(texte, max(10, int(largeur_max / (capitale * 0.60))))
        if len(decoupe) <= 3:
            break
    interligne = capitale * 1.3
    hauteur_bloc = capitale + interligne * (len(decoupe) - 1)
    y = haut + (bas - haut - hauteur_bloc) / 2 + capitale
    morceaux = []
    for ligne in decoupe:
        largeur = min(largeur_max, _largeur_naturelle(ligne, capitale))
        morceaux.append(GRAS.ligne(ligne, MARGE, y, capitale, largeur, couleur, interlettrage=1))
        y += interligne
    return "".join(morceaux)


def _largeur_naturelle(texte: str, capitale: float) -> float:
    e = capitale / GRAS.hauteur_capitale
    return sum(GRAS.glyphes[GRAS.cmap[ord(ch)]].width * e for ch in texte) + len(texte)


def surtitre(texte: str, couleur: str) -> str:
    """Surtitre en capitales espacées, comme « ACADEMY » du logotype (charte §3)."""
    capitale = 26
    return REGULIER.ligne(texte.upper(), MARGE, 190, capitale, min(560, _largeur_naturelle(texte.upper(), capitale)
                                                                   + 10 * len(texte)), couleur, interlettrage=10)


# --- parcours ---------------------------------------------------------------------------------------------------
PARCOURS = (
    dict(nom="fondamentaux-data-science", surtitre="Parcours 0 · socle commun",
         titre="Fondamentaux de la Data Science", accent=JAUNE, glyphe=glyphe_statistique),
    dict(nom="developpeur-python", surtitre="Parcours I · développement",
         titre="Développeur Python", accent=BLEU_CIEL, glyphe=glyphe_code),
    dict(nom="ai-engineer", surtitre="Parcours II · applications LLM",
         titre="AI Engineer", accent=ORANGE, glyphe=glyphe_agents),
    dict(nom="data-engineer", surtitre="Parcours III · plateformes de données",
         titre="Data Engineer", accent=BLEU_CIEL, glyphe=glyphe_pipeline),
    dict(nom="cybersecurite-i", surtitre="Parcours IV · ouverture prochaine",
         titre="Ingénieur Cybersécurité I", accent=JAUNE,
         glyphe=lambda c: glyphe_bouclier(c, double=False)),
    dict(nom="cybersecurite-ii", surtitre="Parcours V · ouverture prochaine",
         titre="Ingénieur Cybersécurité II", accent=ORANGE,
         glyphe=lambda c: glyphe_bouclier(c, double=True)),
    dict(nom="ia-agentique", surtitre="Formation · agents IA",
         titre="IA agentique : concevoir et maîtriser les agents", accent=ORANGE, glyphe=glyphe_boucle),
    dict(nom="python-application-rh", surtitre="Formation · 35 journées",
         titre="Bases de Python, jour après jour", accent=JAUNE, glyphe=glyphe_escalier),
)


def couverture(p: dict) -> str:
    """SVG d'une couverture : fond gravé, voile du domaine, glyphe, surtitre, titre, pictogramme et filet."""
    corps = [
        f'<rect width="{LARGEUR}" height="{HAUTEUR}" fill="{BLEU_NUIT}"/>',
        circuit(),
        voile(),
        f'<g transform="translate({LARGEUR - 440} {HAUTEUR / 2 - 92})">{p["glyphe"](p["accent"])}</g>',
        surtitre(p["surtitre"], p["accent"]),
        titre_compose(p["titre"], LARGEUR * 0.55, BLANC),
        # signature dans la bande centrale : la vignette du catalogue recadre la couverture et mangerait un pied
        f'<g transform="translate({MARGE} {SIGNATURE - 44}) scale(0.048)">'
        f'{charte.pictogramme(charte.COULEURS["couleur"])}</g>',
        REGULIER.ligne("OPENLAB ACADEMY", MARGE + 84, SIGNATURE, 20,
                       _largeur_naturelle("OPENLAB ACADEMY", 20) + 8 * 15, BLANC, interlettrage=8),
        filet(),
    ]
    return charte.svg(LARGEUR, HAUTEUR, "\n  ".join(corps), None)


def ecrire() -> list[pathlib.Path]:
    """Écrit chaque couverture en JPEG (le format attendu par les fichiers de parcours), via le SVG intermédiaire."""
    from PIL import Image

    SORTIE.mkdir(parents=True, exist_ok=True)
    provisoire = ICI / "couvertures"
    provisoire.mkdir(exist_ok=True)
    fichiers = []
    for p in PARCOURS:
        svg = provisoire / f"couverture-{p['nom']}.svg"
        svg.write_text(couverture(p), encoding="utf-8", newline="\n")
        image = charte.rendre(svg, LARGEUR)
        plat = Image.new("RGB", image.size, BLEU_NUIT)
        plat.paste(image, mask=image.split()[3])
        cible = SORTIE / f"couverture-{p['nom']}.jpg"
        plat.save(cible, quality=88, optimize=True, progressive=True)
        fichiers.append(cible)
    return fichiers


if __name__ == "__main__":
    for f in ecrire():
        print(f)
