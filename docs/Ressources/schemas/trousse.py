"""Trousse de dessin des schémas de cours : primitives SVG, palette et mise en page.

Un schéma de l'Academy est du code, pas une pièce jointe. La conséquence pratique tient en trois points :
le rendu est reproductible octet pour octet, une correction se lit dans un diff, et aucun outil extérieur
ni aucun compte n'est nécessaire pour rouvrir une figure dans deux ans.

Déterminisme : aucune date, aucun identifiant aléatoire, coordonnées arrondies au centième, attributs écrits
dans un ordre fixe. Deux exécutions produisent le même octet.

Couleurs : palette validée pour la vision des couleurs (écarts OKLab contrôlés en clair et en sombre), avec
les deux modes déclarés dans la feuille de style embarquée. Une figure ouverte dans un thème sombre se
relit sans être retournée.
"""
from __future__ import annotations

import html
from dataclasses import dataclass, field

# Palette : trois teintes catégorielles, encre et surfaces, en clair puis en sombre.
CLAIR = {
    "surface": "#fcfcfb", "encre": "#0b0b0b", "encre2": "#52514e", "attenue": "#898781",
    "trait": "#c3c2b7", "grille": "#e1e0d9",
    "s1": "#2a78d6", "s2": "#eb6834", "s3": "#1baf7a",
    "bon": "#0ca30c", "attention": "#fab219", "serieux": "#ec835a", "critique": "#d03b3b",
}
SOMBRE = {
    "surface": "#1a1a19", "encre": "#f0efec", "encre2": "#c3c2b7", "attenue": "#898781",
    "trait": "#383835", "grille": "#2c2c2a",
    "s1": "#3987e5", "s2": "#d95926", "s3": "#199e70",
    "bon": "#0ca30c", "attention": "#fab219", "serieux": "#ec835a", "critique": "#d03b3b",
}
POLICE = 'system-ui, -apple-system, "Segoe UI", sans-serif'


def _n(valeur: float) -> str:
    """Nombre écrit sans flottement : deux décimales au plus, sans zéro inutile."""
    texte = f"{valeur:.2f}".rstrip("0").rstrip(".")
    return "0" if texte in ("", "-0") else texte


def _t(texte: str) -> str:
    return html.escape(texte, quote=True)


@dataclass
class Dessin:
    """Accumulateur d'éléments SVG. L'ordre d'ajout est l'ordre de rendu."""

    largeur: float
    hauteur: float
    titre: str
    elements: list[str] = field(default_factory=list)

    def ajouter(self, element: str) -> None:
        self.elements.append(element)

    # ---- primitives -------------------------------------------------------
    def boite(self, x: float, y: float, l: float, h: float, *, teinte: str = "trait",
              remplissage: str | None = None, rayon: float = 8, tirets: bool = False) -> None:
        style = [f'x="{_n(x)}"', f'y="{_n(y)}"', f'width="{_n(l)}"', f'height="{_n(h)}"',
                 f'rx="{_n(rayon)}"', f'class="b-{teinte}"']
        if remplissage:
            style.append(f'fill="var(--{remplissage})"')
        else:
            style.append('fill="var(--surface)"')
        if tirets:
            style.append('stroke-dasharray="5 4"')
        self.ajouter(f"<rect {' '.join(style)}/>")

    def texte(self, x: float, y: float, contenu: str, *, taille: float = 13, gras: bool = False,
              ancre: str = "middle", couleur: str = "encre") -> None:
        poids = ' font-weight="600"' if gras else ""
        self.ajouter(f'<text x="{_n(x)}" y="{_n(y)}" text-anchor="{ancre}" font-size="{_n(taille)}"'
                     f'{poids} fill="var(--{couleur})">{_t(contenu)}</text>')

    def lignes_de_texte(self, x: float, y: float, lignes: list[str], *, taille: float = 12,
                        interligne: float = 15, ancre: str = "middle", couleur: str = "encre2") -> None:
        for i, ligne in enumerate(lignes):
            self.texte(x, y + i * interligne, ligne, taille=taille, ancre=ancre, couleur=couleur)

    def fleche(self, x1: float, y1: float, x2: float, y2: float, *, teinte: str = "attenue",
               courbe: float = 0, tirets: bool = False) -> None:
        if courbe:
            mx, my = (x1 + x2) / 2, (y1 + y2) / 2
            chemin = f"M {_n(x1)} {_n(y1)} Q {_n(mx + courbe)} {_n(my)} {_n(x2)} {_n(y2)}"
        else:
            chemin = f"M {_n(x1)} {_n(y1)} L {_n(x2)} {_n(y2)}"
        style = f' stroke-dasharray="5 4"' if tirets else ""
        self.ajouter(f'<path d="{chemin}" fill="none" stroke="var(--{teinte})" stroke-width="2"'
                     f'{style} marker-end="url(#pointe-{teinte})"/>')

    def barre(self, x: float, y: float, l: float, h: float, teinte: str) -> None:
        """Barre à bout arrondi côté donnée, ancrée sur la ligne de base."""
        self.ajouter(f'<rect x="{_n(x)}" y="{_n(y)}" width="{_n(l)}" height="{_n(h)}" rx="4" ry="4"'
                     f' fill="var(--{teinte})"/>')
        self.ajouter(f'<rect x="{_n(x)}" y="{_n(y + h - 6)}" width="{_n(l)}" height="6"'
                     f' fill="var(--{teinte})"/>')

    # ---- rendu ------------------------------------------------------------
    def _variables(self, valeurs: dict[str, str]) -> str:
        return "".join(f"  --{cle}: {val};\n" for cle, val in valeurs.items())

    def rendre(self) -> str:
        pointes = "".join(
            f'<marker id="pointe-{t}" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6"'
            f' markerHeight="6" orient="auto-start-reverse">'
            f'<path d="M 0 0 L 10 5 L 0 10 z" fill="var(--{t})"/></marker>'
            for t in ("attenue", "s1", "s2", "s3", "critique", "bon"))
        style = (
            "svg{font-family:" + POLICE + ";background:var(--surface)}\n"
            ":root{\n" + self._variables(CLAIR) + "}\n"
            "@media (prefers-color-scheme: dark){:root{\n" + self._variables(SOMBRE) + "}}\n"
            "rect[class^='b-']{stroke-width:1.5}\n"
            + "".join(f".b-{t}{{stroke:var(--{t})}}\n" for t in CLAIR)
        )
        corps = "\n".join(self.elements)
        return (
            f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {_n(self.largeur)} {_n(self.hauteur)}"'
            f' width="{_n(self.largeur)}" height="{_n(self.hauteur)}" role="img"'
            f' aria-label="{_t(self.titre)}">\n'
            f"<title>{_t(self.titre)}</title>\n"
            f"<defs>{pointes}</defs>\n"
            f"<style>\n{style}</style>\n"
            f'<rect width="{_n(self.largeur)}" height="{_n(self.hauteur)}" fill="var(--surface)"/>\n'
            f"{corps}\n</svg>\n")
