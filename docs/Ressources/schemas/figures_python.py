"""Les schémas du parcours « Bases de Python, jour après jour », un par fonction.

Le public est débutant : une figure n'est là que si le texte seul demanderait à l'apprenant de tenir
plusieurs choses en tête à la fois. Lire une trace d'erreur, placer des seuils sur un axe, distinguer ce
qu'une fonction reçoit de ce qu'elle rend : trois objets que la prose explique mal et qu'un dessin règle.
"""
from trousse import Dessin


def trace_erreur() -> Dessin:
    """J01 : une trace Python se lit de bas en haut, et la dernière ligne nomme le problème."""
    d = Dessin(760, 330, "Lire une trace d'erreur Python de bas en haut")
    d.texte(380, 34, "Une trace se lit de bas en haut.", taille=15, gras=True)
    d.texte(380, 56, "La dernière ligne dit quoi ; la ligne au-dessus dit où.", taille=12, couleur="encre2")
    lignes = [
        ("Traceback (most recent call last):", "l'annonce, sans information utile", "attenue"),
        ('  File "fiche.py", line 7, in <module>', "le fichier et la ligne : regardez là", "s1"),
        ("    print(salaire_fcfa)", "le code fautif, recopié", "s1"),
        ("NameError: name 'salaire_fcfa' is not defined", "le problème, nommé : commencez ici", "critique"),
    ]
    for i, (code, commentaire, teinte) in enumerate(lignes):
        y = 90 + i * 52
        d.boite(40, y, 430, 40, teinte=teinte)
        d.texte(54, y + 25, code, taille=12, ancre="start")
        d.texte(492, y + 25, commentaire, taille=11, ancre="start", couleur="encre2")
    d.fleche(500, 290, 500, 120, teinte="critique")
    d.texte(380, 316, "Le nom de l'erreur et la ligne suffisent dans neuf cas sur dix.",
            taille=12, gras=True, couleur="encre2")
    return d


def seuils_conges() -> Dessin:
    """J03 : trois branches sur un axe ; les bornes se voient, elles ne se devinent pas."""
    d = Dessin(760, 290, "Les seuils du droit aux congés, et leurs bornes")
    d.texte(380, 34, "Une règle à seuils se dessine avant de s'écrire.", taille=15, gras=True)
    d.texte(380, 56, "Les bugs se logent aux bornes : 11 mois, 12 mois, 13 mois.", taille=12, couleur="encre2")
    base, gauche, droite = 170, 60, 700
    d.ajouter(f'<line x1="{gauche}" y1="{base}" x2="{droite}" y2="{base}" stroke="var(--trait)"'
              ' stroke-width="2"/>')
    bornes = [(60, "0"), (273, "6"), (486, "12"), (700, "24 mois")]
    for x, libelle in bornes:
        d.ajouter(f'<line x1="{x}" y1="{base - 7}" x2="{x}" y2="{base + 7}" stroke="var(--trait)"'
                  ' stroke-width="2"/>')
        d.texte(x, base + 26, libelle, taille=12, couleur="encre2")
    zones = [(60, 426, "s2", "moins de 12 mois", "aucun droit"),
             (486, 214, "s3", "12 mois et plus", "droit ouvert")]
    for x, largeur, teinte, titre, effet in zones:
        d.boite(x, base - 62, largeur, 48, teinte=teinte)
        d.texte(x + largeur / 2, base - 40, titre, taille=13, gras=True)
        d.texte(x + largeur / 2, base - 22, effet, taille=11, couleur="encre2")
    d.texte(486, base + 62, "La borne appartient à la seconde zone : 12 mois ouvre le droit.",
            taille=12, gras=True, couleur="encre2")
    d.texte(380, base + 92, "Écrivez un test pour 11, un pour 12, un pour 13. Les trois, pas un seul.",
            taille=12, couleur="encre2")
    return d


def fonction_entree_sortie() -> Dessin:
    """J05 : une fonction reçoit, calcule et rend ; afficher n'est pas rendre."""
    d = Dessin(760, 330, "Ce qu'une fonction reçoit, ce qu'elle rend, et ce qu'elle n'affiche pas")
    d.texte(380, 34, "Une fonction rend une valeur. Elle n'affiche rien.", taille=15, gras=True)
    d.texte(380, 56, "Qui affiche ne peut plus être réutilisé ni testé.", taille=12, couleur="encre2")
    d.boite(50, 110, 170, 70, teinte="s1")
    d.texte(135, 138, "Paramètres", taille=14, gras=True)
    d.texte(135, 160, "mensuel, primes", taille=11, couleur="encre2")
    d.boite(295, 100, 180, 90, teinte="s3")
    d.texte(385, 130, "salaire_annuel", taille=14, gras=True)
    d.texte(385, 152, "le calcul, et rien", taille=11, couleur="encre2")
    d.texte(385, 170, "d'autre", taille=11, couleur="encre2")
    d.boite(550, 110, 170, 70, teinte="s2")
    d.texte(635, 138, "Valeur rendue", taille=14, gras=True)
    d.texte(635, 160, "return montant", taille=11, couleur="encre2")
    d.fleche(228, 145, 287, 145, teinte="s1")
    d.fleche(483, 145, 542, 145, teinte="s2")
    d.boite(240, 232, 290, 56, teinte="critique", tirets=True)
    d.texte(385, 254, "print dans la fonction", taille=13, gras=True, couleur="critique")
    d.texte(385, 274, "la valeur est perdue, le test ne voit rien", taille=11, couleur="encre2")
    d.fleche(385, 198, 385, 228, teinte="critique", tirets=True)
    d.texte(380, 314, "L'appelant décide d'afficher ; la fonction décide de calculer.",
            taille=12, gras=True, couleur="encre2")
    return d


FIGURES_PYTHON = {
    "python-trace-erreur.svg": trace_erreur,
    "python-seuils-conges.svg": seuils_conges,
    "python-fonction-entree-sortie.svg": fonction_entree_sortie,
}
