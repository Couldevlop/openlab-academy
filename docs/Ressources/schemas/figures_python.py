"""Les schémas du parcours « Bases de Python, jour après jour », un par fonction.

Le public est débutant : une figure n'est là que si le texte seul demanderait à l'apprenant de tenir
plusieurs choses en tête à la fois. Lire une trace d'erreur, placer des seuils sur un axe, distinguer ce
qu'une fonction reçoit de ce qu'elle rend : trois objets que la prose explique mal et qu'un dessin règle.
"""
import math

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


def tranches_liste() -> Dessin:
    """J06 : les index d'une liste et les bornes d'une tranche, incluse puis exclue."""
    d = Dessin(760, 300, "Index d'une liste et bornes d'une tranche")
    d.texte(380, 34, "L'index commence à 0 ; la borne de fin est exclue.", taille=15, gras=True)
    d.texte(380, 56, "noms[1:3] prend l'index 1 et l'index 2, jamais l'index 3.", taille=12, couleur="encre2")
    noms = ["Awa", "Bakary", "Céline", "Daouda"]
    for i, nom in enumerate(noms):
        x = 110 + i * 150
        teinte = "s1" if i in (1, 2) else "trait"
        d.boite(x, 110, 130, 60, teinte=teinte)
        d.texte(x + 65, 146, nom, taille=14, gras=i in (1, 2))
        d.texte(x + 65, 190, f"index {i}", taille=11, couleur="encre2")
        d.texte(x + 65, 208, f"index {i - len(noms)}", taille=11, couleur="attenue")
    d.ajouter('<path d="M 260 96 L 560 96" fill="none" stroke="var(--s1)" stroke-width="2"/>')
    d.texte(410, 88, "noms[1:3]", taille=12, gras=True, couleur="s1")
    d.texte(380, 252, "Le dernier index vaut len(noms) moins un : noms[4] lève IndexError.",
            taille=12, gras=True, couleur="encre2")
    d.texte(380, 276, "Un index négatif compte depuis la fin : noms[-1] est le dernier.",
            taille=12, couleur="encre2")
    return d


def copie_liste() -> Dessin:
    """J08 : une copie de liste duplique la liste, pas les fiches qu'elle contient."""
    d = Dessin(760, 320, "Copie superficielle d'une liste de fiches")
    d.texte(380, 34, "effectif[:] copie la liste, pas les fiches.", taille=15, gras=True)
    d.texte(380, 56, "Modifier une fiche de la copie modifie celle de l'original.", taille=12, couleur="encre2")
    for x, titre, teinte in ((90, "effectif", "s1"), (470, "copie", "s2")):
        d.boite(x, 100, 200, 56, teinte=teinte)
        d.texte(x + 100, 133, titre, taille=14, gras=True)
    fiches = [(290, 220, "fiche Awa"), (290, 268, "fiche Bakary")]
    for x, y, libelle in fiches:
        d.boite(x - 110, y - 22, 220, 40, teinte="s3")
        d.texte(x, y + 3, libelle, taille=12)
        d.fleche(190, 160, x - 118, y - 10, teinte="s1")
        d.fleche(570, 160, x + 118, y - 10, teinte="s2")
    d.texte(380, 308, "Pour ne rien partager, construisez une nouvelle fiche plutôt que modifier celle reçue.",
            taille=12, gras=True, couleur="encre2")
    return d


def anciennete_mois() -> Dessin:
    """J09 : le mois en cours ne compte que lorsque le jour d'embauche est atteint."""
    d = Dessin(760, 300, "Ancienneté en mois révolus, et mois commencé")
    d.texte(380, 34, "Un mois compte quand il est révolu, pas quand il est commencé.", taille=15, gras=True)
    d.texte(380, 56, "Embauche le 15 mars 2024 : trois dates du jour, trois réponses.", taille=12,
            couleur="encre2")
    cas = [("14 mars 2025", "11 mois", "s2", "le jour d'embauche n'est pas atteint"),
           ("15 mars 2025", "12 mois", "s3", "le jour d'embauche est atteint"),
           ("16 mars 2025", "12 mois", "s3", "le mois en cours ne compte pas encore")]
    for i, (jour, reponse, teinte, raison) in enumerate(cas):
        x = 40 + i * 240
        d.boite(x, 100, 220, 96, teinte=teinte)
        d.texte(x + 110, 128, jour, taille=13, gras=True)
        d.texte(x + 110, 154, reponse, taille=18, gras=True)
        d.texte(x + 110, 180, raison, taille=10, couleur="encre2")
    d.texte(380, 236, "mois = (annees × 12) + mois, moins un si le jour du mois n'est pas atteint",
            taille=13, gras=True)
    d.texte(380, 266, "Une soustraction de dates donne des jours : diviser par trente est faux.",
            taille=12, couleur="encre2")
    d.texte(380, 288, "Ces trois dates sont exactement les bornes de la règle des congés.",
            taille=12, couleur="encre2")
    return d


def modules_arborescence() -> Dessin:
    """J11 : trois fichiers, trois rôles, et des imports qui ne vont que dans un sens."""
    d = Dessin(760, 330, "Trois modules et le sens unique des imports")
    d.texte(380, 34, "Les imports vont de l'habillage vers le cœur.", taille=15, gras=True)
    d.texte(380, 56, "Le cœur n'importe rien du projet : c'est ce qui le rend réutilisable.",
            taille=12, couleur="encre2")
    etages = [("main.py", "lance le programme", 100, "s2"),
              ("rh/etats.py", "met en forme pour l'humain", 170, "s1"),
              ("rh/calculs.py", "calcule, et rien d'autre", 240, "s3")]
    for nom, role, y, teinte in etages:
        d.boite(230, y, 300, 52, teinte=teinte)
        d.texte(380, y + 22, nom, taille=14, gras=True)
        d.texte(380, y + 42, role, taille=11, couleur="encre2")
    d.fleche(380, 154, 380, 166, teinte="s2")
    d.fleche(380, 224, 380, 236, teinte="s1")
    d.texte(566, 162, "importe", taille=11, ancre="start", couleur="encre2")
    d.texte(566, 232, "importe", taille=11, ancre="start", couleur="encre2")
    d.texte(380, 318, "Une flèche en sens inverse est un import circulaire : déplacez la fonction.",
            taille=12, gras=True, couleur="encre2")
    return d


def erreur_metier() -> Dessin:
    """J13 : la panne technique s'arrête à la frontière et devient un message utile."""
    d = Dessin(760, 310, "D'une panne technique à un message utile")
    d.texte(380, 34, "La frontière traduit ; le cœur ne voit que des données saines.",
            taille=15, gras=True)
    d.boite(40, 90, 200, 110, teinte="critique")
    d.texte(140, 118, "Panne technique", taille=13, gras=True, couleur="critique")
    d.lignes_de_texte(140, 144, ["FileNotFoundError", "KeyError", "ValueError"], taille=11)
    d.boite(280, 90, 200, 110, teinte="s1")
    d.texte(380, 118, "Frontière", taille=13, gras=True)
    d.lignes_de_texte(380, 144, ["try / except nommé", "raise DonneeInvalide", "from erreur"], taille=11)
    d.boite(520, 90, 200, 110, teinte="s3")
    d.texte(620, 118, "Message au gérant", taille=13, gras=True)
    d.lignes_de_texte(620, 144, ["« Colonne salaire_fcfa", "absente du fichier", "effectif.csv »"], taille=11)
    d.fleche(248, 145, 272, 145, teinte="critique")
    d.fleche(488, 145, 512, 145, teinte="s3")
    d.boite(230, 232, 300, 50, teinte="attenue", tirets=True)
    d.texte(380, 252, "Faute de frappe dans votre code", taille=12, gras=True)
    d.texte(380, 271, "la trace remonte telle quelle, sans déguisement", taille=11, couleur="encre2")
    return d


def frontiere_validation() -> Dessin:
    """J15 : un seul endroit valide, et le cœur travaille sur des données réputées saines."""
    d = Dessin(760, 320, "La validation a lieu à la frontière, une seule fois")
    d.texte(380, 34, "Un modèle d'entrée à la porte ; aucun contrôle au-delà.", taille=15, gras=True)
    d.boite(40, 95, 190, 120, teinte="s2")
    d.texte(135, 122, "Monde extérieur", taille=13, gras=True)
    d.lignes_de_texte(135, 148, ["fichier CSV", "requête d'API", "formulaire"], taille=11)
    d.boite(285, 95, 190, 120, teinte="s1")
    d.texte(380, 122, "SalarieEntrant", taille=13, gras=True)
    d.lignes_de_texte(380, 148, ["types vérifiés", "salaire positif", "date pas future"], taille=11)
    d.boite(530, 95, 190, 120, teinte="s3")
    d.texte(625, 122, "Cœur de calcul", taille=13, gras=True)
    d.lignes_de_texte(625, 148, ["données saines", "aucun contrôle", "que du métier"], taille=11)
    d.fleche(238, 155, 277, 155, teinte="s2")
    d.fleche(483, 155, 522, 155, teinte="s1")
    d.texte(380, 252, "Refusé ici, avec le champ nommé.", taille=12, gras=True, couleur="s1")
    d.texte(380, 292, "Valider dans chaque fonction coûte cher et finit par diverger.",
            taille=12, couleur="encre2")
    return d


def requete_reponse() -> Dessin:
    """J16 : les deux messages d'un échange HTTP, et ce que chacun porte."""
    d = Dessin(760, 300, "Une requête, une réponse")
    d.texte(380, 34, "Deux messages, et quatre informations à lire.", taille=15, gras=True)
    d.boite(60, 80, 180, 56, teinte="s1")
    d.texte(150, 114, "Votre navigateur", taille=13, gras=True)
    d.boite(520, 80, 180, 56, teinte="s3")
    d.texte(610, 114, "Votre API", taille=13, gras=True)
    d.fleche(246, 100, 514, 100, teinte="s1")
    d.texte(380, 92, "GET /salaries/12", taille=12, gras=True)
    d.fleche(514, 132, 246, 132, teinte="s3")
    d.texte(380, 150, "200, puis le JSON de la fiche", taille=12, gras=True)
    lignes = [("Méthode", "l'intention : GET lit, POST crée"),
              ("Chemin", "la ressource visée"),
              ("Code", "2 réussite, 4 faute de l'appelant, 5 panne du serveur"),
              ("Contenu", "le JSON, qui ressemble aux dictionnaires Python")]
    for i, (nom, role) in enumerate(lignes):
        y = 190 + i * 26
        d.texte(170, y, nom, taille=12, gras=True, ancre="end")
        d.texte(190, y, role, taille=12, ancre="start", couleur="encre2")
    return d


def api_autour_du_coeur() -> Dessin:
    """J17 : le cœur au centre, les habillages autour, et des flèches qui pointent vers le centre."""
    d = Dessin(760, 340, "Le cœur au centre, les habillages autour")
    d.texte(380, 34, "Les trois habillages dépendent du cœur ; le cœur n'en connaît aucun.",
            taille=15, gras=True)
    d.boite(290, 140, 180, 90, teinte="s3")
    d.texte(380, 172, "rh/", taille=15, gras=True)
    d.texte(380, 194, "règles et calculs", taille=11, couleur="encre2")
    d.texte(380, 214, "semaine 3", taille=11, couleur="attenue")
    autour = [(60, 90, "FastAPI", "semaine 4", "s1"), (540, 90, "Streamlit", "semaine 5", "s2"),
              (300, 276, "Django", "semaines 6 et 7", "s1")]
    for x, y, nom, quand, teinte in autour:
        d.boite(x, y, 160, 56, teinte=teinte)
        d.texte(x + 80, y + 24, nom, taille=13, gras=True)
        d.texte(x + 80, y + 43, quand, taille=10, couleur="encre2")
    d.fleche(190, 132, 286, 164, teinte="s1")
    d.fleche(570, 132, 474, 164, teinte="s2")
    d.fleche(380, 270, 380, 236, teinte="s1")
    d.texte(380, 326, "Une flèche qui partirait du cœur rendrait le cœur inutilisable ailleurs.",
            taille=12, gras=True, couleur="encre2")
    return d


def codes_http() -> Dessin:
    """J19 : à chaque situation son code, et le piège du 200 qui ment."""
    d = Dessin(760, 320, "Quel code pour quelle situation")
    d.texte(380, 34, "Le code est une information, pas une décoration.", taille=15, gras=True)
    cas = [("200", "Réussite", "le mois demandé, avec son total", "s3"),
           ("200", "Réussite vide", "aucun salarié ce mois : total nul", "s3"),
           ("422", "Faute de l'appelant", "le mois est mal écrit", "s2"),
           ("500", "Panne de votre côté", "à corriger, jamais à renvoyer sciemment", "critique")]
    for i, (code, nom, detail, teinte) in enumerate(cas):
        y = 80 + i * 52
        d.boite(60, y, 90, 40, teinte=teinte)
        d.texte(105, y + 26, code, taille=16, gras=True)
        d.texte(180, y + 18, nom, taille=13, gras=True, ancre="start")
        d.texte(180, y + 36, detail, taille=11, ancre="start", couleur="encre2")
    d.boite(60, 292, 640, 0.1, teinte="trait")
    d.texte(380, 300, "Le pire n'est pas le 500 : c'est le 200 renvoyé après une erreur étouffée.",
            taille=12, gras=True, couleur="encre2")
    return d


def streamlit_execution() -> Dessin:
    """J21 : chaque interaction rejoue le script entier, de la première ligne à la dernière."""
    d = Dessin(760, 320, "Le script Streamlit est rejoué à chaque interaction")
    d.texte(380, 34, "Un clic ne déclenche pas une fonction : il rejoue la page.", taille=15, gras=True)
    etapes = [("charger l'effectif", "refait à chaque fois, d'où le cache"),
              ("lire les widgets", "les valeurs choisies par l'utilisateur"),
              ("appeler le cœur", "filtrer, calculer, préparer les séries"),
              ("afficher", "chiffres, tableau, graphiques")]
    for i, (nom, detail) in enumerate(etapes):
        y = 80 + i * 56
        d.boite(170, y, 420, 44, teinte="s1")
        d.texte(240, y + 27, nom, taille=13, gras=True, ancre="start")
        d.texte(575, y + 27, detail, taille=10, ancre="end", couleur="encre2")
        if i < 3:
            d.fleche(380, y + 44, 380, y + 56, teinte="s1")
    d.ajouter('<path d="M 150 290 L 90 290 L 90 102 L 162 102" fill="none" stroke="var(--s2)"'
              ' stroke-width="2" marker-end="url(#pointe-s2)"/>')
    d.texte(96, 310, "clic sur un widget", taille=11, ancre="start", couleur="s2")
    d.texte(520, 310, "Ce qui mérite un test vit dans le cœur, pas ici.", taille=12, gras=True,
            couleur="encre2")
    return d


def graphique_lisible() -> Dessin:
    """J24 : la même donnée en barres triées et en camembert à douze parts."""
    d = Dessin(760, 330, "Barres triées contre camembert à douze parts")
    d.texte(380, 34, "La même donnée, deux formes : une seule répond à la question.",
            taille=15, gras=True)
    d.texte(190, 62, "Barres triées", taille=13, gras=True, couleur="s3")
    valeurs = [120, 96, 74, 58, 40, 28]
    for i, valeur in enumerate(valeurs):
        x = 60 + i * 44
        d.barre(x, 230 - valeur, 32, valeur, "s3")
    d.ajouter('<line x1="50" y1="232" x2="340" y2="232" stroke="var(--trait)" stroke-width="2"/>')
    d.texte(190, 252, "en FCFA, du plus cher au moins cher", taille=11, couleur="encre2")
    d.texte(190, 274, "lecture immédiate", taille=12, gras=True, couleur="s3")
    d.texte(570, 62, "Camembert à douze parts", taille=13, gras=True, couleur="critique")
    centre, rayon = (570, 160), 72
    for i in range(12):
        a1, a2 = i * 30, (i + 1) * 30
        x1 = centre[0] + rayon * math.cos(math.radians(a1))
        y1 = centre[1] + rayon * math.sin(math.radians(a1))
        x2 = centre[0] + rayon * math.cos(math.radians(a2))
        y2 = centre[1] + rayon * math.sin(math.radians(a2))
        d.ajouter(f'<path d="M {centre[0]} {centre[1]} L {x1:.2f} {y1:.2f} A {rayon} {rayon} 0 0 1'
                  f' {x2:.2f} {y2:.2f} Z" fill="none" stroke="var(--critique)" stroke-width="1.5"/>')
    d.texte(570, 252, "douze angles proches, une légende à décoder", taille=11, couleur="encre2")
    d.texte(570, 274, "lecture impossible", taille=12, gras=True, couleur="critique")
    d.texte(380, 314, "Une mesure par axe, et jamais deux échelles sur une même figure.",
            taille=12, gras=True, couleur="encre2")
    return d


FIGURES_PYTHON = {
    "python-trace-erreur.svg": trace_erreur,
    "python-seuils-conges.svg": seuils_conges,
    "python-fonction-entree-sortie.svg": fonction_entree_sortie,
    "python-tranches-liste.svg": tranches_liste,
    "python-copie-liste.svg": copie_liste,
    "python-anciennete-mois.svg": anciennete_mois,
    "python-modules-arborescence.svg": modules_arborescence,
    "python-erreur-metier.svg": erreur_metier,
    "python-frontiere-validation.svg": frontiere_validation,
    "python-requete-reponse.svg": requete_reponse,
    "python-api-autour-du-coeur.svg": api_autour_du_coeur,
    "python-codes-http.svg": codes_http,
    "python-streamlit-execution.svg": streamlit_execution,
    "python-graphique-lisible.svg": graphique_lisible,
}
