"""Les domaines d'un parcours : la famille à laquelle il appartient, et la teinte qui la porte.

**Ce module ne détient pas la liste.** Les domaines se gèrent depuis l'administration, comme les
rythmes ou les tarifs : une plateforme dont les familles de formation seraient gravées dans le code
obligerait à une livraison pour ouvrir une filière. Ce qui vit ici, ce sont les **règles** — ce
qu'une teinte doit valoir, ce qu'une clé a le droit d'être — et une semence pour que la plateforme
démarre remplie.

La règle de teinte mérite d'être dite. Une bande de couleur porte le titre du parcours en blanc ;
sous 4,5:1 de contraste, ce titre devient illisible pour une partie des visiteurs. L'administration
choisit donc librement sa couleur, mais le formulaire refuse celles qui ne savent pas porter leur
texte. C'est le seul endroit où la configurabilité s'arrête, et elle s'arrête sur l'accessibilité.
"""
from dataclasses import dataclass
from typing import Iterable

SEUIL_CONTRASTE = 4.5  # AA pour du texte normal, pas seulement pour un grand titre
ECART_MINIMAL = 20.0  # ΔE : deux familles doivent se distinguer d'un coup d'œil, pas se nuancer


class DomaineInconnu(ValueError):
    """Clé absente de la table des domaines.

    Une erreur à soi plutôt que `ParcoursInvalide` : ce module ne connaît pas les parcours et ne
    doit pas les connaître. C'est `parcours.py` qui importe celui-ci, jamais l'inverse.
    """


class TeinteIllisible(ValueError):
    """Teinte sur laquelle un titre blanc ne se lit pas."""


@dataclass(frozen=True)
class Domaine:
    cle: str
    libelle: str
    teinte: str  # fond de la bande ; le titre s'y écrit en blanc


def _luminance(hexa: str) -> float:
    canaux = [int(hexa[i:i + 2], 16) / 255 for i in (1, 3, 5)]
    lineaires = [c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in canaux]
    return 0.2126 * lineaires[0] + 0.7152 * lineaires[1] + 0.0722 * lineaires[2]


def contraste(a: str, b: str) -> float:
    """Rapport de contraste WCAG. Il compare des clartés : il ne vaut que face au blanc ou au noir."""
    la, lb = _luminance(a), _luminance(b)
    return (max(la, lb) + 0.05) / (min(la, lb) + 0.05)


def _lab(hexa: str) -> tuple[float, float, float]:
    """La couleur en L*a*b*, l'espace où une distance égale se voit comme un écart égal."""
    canaux = [int(hexa[i:i + 2], 16) / 255 for i in (1, 3, 5)]
    r, v, b = [c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in canaux]
    x = (0.4124 * r + 0.3576 * v + 0.1805 * b) / 0.95047
    y = 0.2126 * r + 0.7152 * v + 0.0722 * b
    z = (0.0193 * r + 0.1192 * v + 0.9505 * b) / 1.08883

    def f(t: float) -> float:
        return t ** (1 / 3) if t > 0.008856 else 7.787 * t + 16 / 116

    fx, fy, fz = f(x), f(y), f(z)
    return 116 * fy - 16, 500 * (fx - fy), 200 * (fy - fz)


def ecart_percu(a: str, b: str) -> float:
    """Distance ΔE entre deux couleurs.

    Le rapport de contraste ne convient pas ici : il ne compare que des clartés, si bien qu'un
    marine et un violet de même luminosité lui paraissent identiques alors que l'œil les sépare
    immédiatement. Un écart de 2,3 est le seuil de perception ; 20 est franc.
    """
    return sum((x - y) ** 2 for x, y in zip(_lab(a), _lab(b))) ** 0.5


def normaliser(teinte: str) -> str:
    """La teinte en minuscules avec son croisillon, ou une erreur si ce n'est pas une couleur."""
    valeur = (teinte or "").strip().lower()
    if not valeur.startswith("#"):
        valeur = "#" + valeur
    if len(valeur) != 7 or any(c not in "0123456789abcdef" for c in valeur[1:]):
        raise TeinteIllisible(f"« {teinte} » n'est pas une couleur hexadécimale à six chiffres")
    return valeur


def verifier_teinte(teinte: str) -> str:
    """La teinte normalisée si un titre blanc s'y lit, une erreur sinon."""
    valeur = normaliser(teinte)
    mesure = contraste(valeur, "#ffffff")
    if mesure < SEUIL_CONTRASTE:
        raise TeinteIllisible(
            f"la teinte {valeur} ne porte pas de texte blanc lisible "
            f"({mesure:.2f}:1, il en faut {SEUIL_CONTRASTE}:1) : choisissez une couleur plus sombre")
    return valeur


def valider(cle: str, connus: Iterable[str]) -> str:
    """La clé telle quelle si la table la connaît. Vide reste vide.

    Un parcours sans domaine est permis : sans cette tolérance, l'arrivée de la notion aurait
    invalidé d'un coup tous les parcours déjà écrits. Il prend la teinte neutre de la charte.
    """
    if not cle:
        return ""
    liste = sorted(connus)
    if cle not in liste:
        attendu = ", ".join(liste) if liste else "aucun domaine n'est encore défini"
        raise DomaineInconnu(f"domaine « {cle} » inconnu (attendu : {attendu})")
    return cle


# Semence : le contenu initial de la table, posé à l'installation si elle est vide. Ce n'est pas la
# liste des domaines — celle-ci vit en base et s'édite. Une teinte modifiée ici ne change rien à une
# plateforme déjà installée, et c'est voulu : une migration ne doit pas écraser un choix d'équipe.
DOMAINES_PAR_DEFAUT: tuple[Domaine, ...] = (
    Domaine("socle", "Socle", "#244498"),
    Domaine("developpement", "Développement", "#0f6b5c"),
    Domaine("ia", "Intelligence artificielle", "#5b2a86"),
    Domaine("donnees", "Données", "#1a6a9e"),
    Domaine("cybersecurite", "Cybersécurité", "#8c2f39"),
    Domaine("systeme", "Systèmes", "#b35210"),
)
