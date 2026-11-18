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
        d.texte(504, y + 25, commentaire, taille=11, ancre="start", couleur="encre2")
    # la flèche occupe la gouttière entre les lignes de trace et leurs commentaires : sans cette
    # marge, elle passait sur le texte
    d.fleche(486, 290, 486, 120, teinte="critique")
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


def migrations() -> Dessin:
    """J27 : le modèle change, la migration l'enregistre, chaque base rejoue le même journal."""
    d = Dessin(760, 310, "Le modèle, la migration et les bases qui suivent")
    d.texte(380, 34, "La migration est un journal versionné, pas un script jetable.", taille=15, gras=True)
    d.boite(40, 90, 200, 70, teinte="s1")
    d.texte(140, 118, "Le modèle change", taille=13, gras=True)
    d.texte(140, 140, "un champ ajouté", taille=11, couleur="encre2")
    d.boite(280, 90, 200, 70, teinte="s3")
    d.texte(380, 118, "La migration", taille=13, gras=True)
    d.texte(380, 140, "générée, relue, versionnée", taille=10, couleur="encre2")
    d.fleche(248, 125, 272, 125, teinte="s1")
    bases = [("votre base", 520), ("celle d'un collègue", 520), ("la production", 520)]
    for i, (nom, x) in enumerate(bases):
        y = 72 + i * 56
        d.boite(x, y, 200, 44, teinte="s2")
        d.texte(x + 100, y + 27, nom, taille=12)
        d.fleche(488, 125, 512, y + 22, teinte="s3")
    d.texte(380, 250, "Une intention par migration : elle se relit, s'annule et se transporte.",
            taille=12, gras=True, couleur="encre2")
    d.texte(380, 280, "Modifier la base à la main fait partir la migration suivante d'un état faux.",
            taille=12, couleur="encre2")
    return d


def django_mvt() -> Dessin:
    """J30 : d'une adresse à une page, et la place de chaque responsabilité."""
    d = Dessin(760, 320, "D'une adresse à une page dans Django")
    d.texte(380, 34, "Chaque couche a une responsabilité, et une seule.", taille=15, gras=True)
    etapes = [("L'adresse", "désigne une vue", 40, "s1"), ("La vue", "prépare le contexte", 220, "s3"),
              ("Le modèle", "sert les données", 400, "s2"), ("Le gabarit", "présente, sans calculer", 580, "s1")]
    for nom, role, x, teinte in etapes:
        d.boite(x, 110, 150, 76, teinte=teinte)
        d.texte(x + 75, 140, nom, taille=13, gras=True)
        d.texte(x + 75, 164, role, taille=10, couleur="encre2")
    for x in (190, 370, 550):
        d.fleche(x, 148, x + 28, 148, teinte="attenue")
    d.boite(220, 232, 330, 50, teinte="critique", tirets=True)
    d.texte(385, 252, "Une règle métier écrite dans le gabarit", taille=12, gras=True, couleur="critique")
    d.texte(385, 271, "n'est ni testable, ni réutilisable, et personne ne l'y cherche", taille=10,
            couleur="encre2")
    d.texte(380, 306, "Une liste qui interroge la base une fois par ligne : chargez les objets liés.",
            taille=12, gras=True, couleur="encre2")
    return d


def roles_permissions() -> Dessin:
    """J33 : deux rôles, quatre pages, et le droit vérifié là où la donnée est servie."""
    d = Dessin(760, 320, "Deux rôles, quatre pages")
    d.texte(380, 34, "Le droit se vérifie là où la donnée est servie.", taille=15, gras=True)
    pages = [("Liste de l'effectif", "avec salaires", "sans salaires"),
             ("Fiche d'un salarié", "complète", "sans salaire"),
             ("Masse salariale", "oui", "refus"),
             ("Absences de l'équipe", "oui", "oui")]
    d.texte(240, 86, "Page", taille=12, gras=True, ancre="end")
    d.texte(420, 86, "RH", taille=12, gras=True)
    d.texte(620, 86, "Manager", taille=12, gras=True)
    for i, (page, rh, manager) in enumerate(pages):
        y = 118 + i * 38
        d.texte(240, y, page, taille=12, ancre="end", couleur="encre2")
        d.boite(330, y - 18, 180, 26, teinte="s3")
        d.texte(420, y, rh, taille=11)
        teinte = "critique" if manager in ("refus",) else "s2"
        d.boite(530, y - 18, 180, 26, teinte=teinte)
        d.texte(620, y, manager, taille=11)
    d.texte(380, 292, "Masquer une colonne n'empêche pas la donnée d'être envoyée dans la réponse.",
            taille=12, gras=True, couleur="encre2")
    return d


def arrondi_fcfa() -> Dessin:
    """J02 : la division rend un nombre à virgule ; le franc CFA, lui, ne se coupe pas."""
    d = Dessin(760, 330, "D'un calcul à virgule au montant payable en francs")
    d.texte(380, 34, "Un calcul rend des décimales ; une paie se verse en francs entiers.",
            taille=15, gras=True)
    d.texte(380, 56, "Arrondissez une fois, à la fin, et jamais à chaque étape.", taille=12, couleur="encre2")
    etapes = [(40, "250000 / 30", "le calcul", "s1"),
              (260, "8333.333333", "ce que Python rend", "s2"),
              (480, "8333 FCFA", "ce que la caisse verse", "s3")]
    for x, valeur, libelle, teinte in etapes:
        d.boite(x, 110, 200, 72, teinte=teinte)
        d.texte(x + 100, 142, valeur, taille=15, gras=True)
        d.texte(x + 100, 166, libelle, taille=11, couleur="encre2")
    d.fleche(246, 146, 256, 146, teinte="s2")
    d.fleche(466, 146, 476, 146, teinte="s3")
    d.boite(40, 222, 320, 62, teinte="critique", tirets=True)
    d.texte(200, 246, "0.1 + 0.2 ne vaut pas 0.3", taille=13, gras=True, couleur="critique")
    d.texte(200, 266, "les flottants approchent, ils ne comptent pas", taille=11, couleur="encre2")
    d.boite(400, 222, 320, 62, teinte="bon")
    d.texte(560, 246, "round(montant) au dernier moment", taille=13, gras=True)
    d.texte(560, 266, "un seul arrondi, sur le montant final", taille=11, couleur="encre2")
    d.texte(380, 314, "Arrondir à chaque ligne d'un bulletin fabrique un écart de plusieurs francs.",
            taille=12, gras=True, couleur="encre2")
    return d


def boucle_for() -> Dessin:
    """J04 : une boucle déroule un tour par élément ; l'accumulateur se déclare avant elle."""
    d = Dessin(760, 330, "Les tours d'une boucle et l'accumulateur qui leur survit")
    d.texte(380, 34, "Une boucle fait un tour par élément.", taille=15, gras=True)
    d.texte(380, 56, "Ce qui doit durer se déclare hors de la boucle, avant elle.",
            taille=12, couleur="encre2")
    d.boite(40, 92, 150, 50, teinte="trait", tirets=True)
    d.texte(115, 122, "total = 0", taille=13, gras=True)
    tours = [("Awa", "250000", "250000"), ("Bakary", "180000", "430000"), ("Céline", "320000", "750000")]
    for i, (nom, salaire, cumul) in enumerate(tours):
        x = 226 + i * 180
        d.boite(x, 92, 160, 112, teinte="s1")
        d.texte(x + 80, 118, "tour " + str(i + 1), taille=12, gras=True, couleur="encre2")
        d.texte(x + 80, 144, nom, taille=13)
        d.texte(x + 80, 168, "+ " + salaire, taille=12, couleur="s1")
        d.texte(x + 80, 192, "total = " + cumul, taille=12, gras=True)
        if i:
            d.fleche(x - 24, 148, x - 8, 148, teinte="s1")
    d.fleche(196, 148, 218, 148, teinte="s1")
    d.boite(40, 240, 200, 58, teinte="bon")
    d.texte(140, 264, "for : on sait combien", taille=13, gras=True)
    d.texte(140, 284, "une liste, une plage, un fichier", taille=11, couleur="encre2")
    d.boite(270, 240, 230, 58, teinte="s2")
    d.texte(385, 264, "while : on attend une condition", taille=13, gras=True)
    d.texte(385, 284, "une saisie juste, un solde épuisé", taille=11, couleur="encre2")
    d.boite(530, 240, 190, 58, teinte="critique", tirets=True)
    d.texte(625, 264, "total dans la boucle", taille=13, gras=True, couleur="critique")
    d.texte(625, 284, "remis à zéro à chaque tour", taille=11, couleur="encre2")
    return d


def liste_ou_dictionnaire() -> Dessin:
    """J07 : la liste se lit par position, le dictionnaire par clé ; la clé ne se décale pas."""
    d = Dessin(760, 320, "Lire par position ou lire par clé")
    d.texte(380, 34, "La position change ; la clé, non.", taille=15, gras=True)
    d.texte(380, 56, "Une fiche salarié se lit par clé, jamais par numéro de colonne.",
            taille=12, couleur="encre2")
    d.boite(40, 86, 330, 176, teinte="s2")
    d.texte(205, 112, "Liste : lue par position", taille=13, gras=True)
    cases = [("Awa Kone", "fiche[0]"), ("Assistante RH", "fiche[1]"), ("250000", "fiche[2]")]
    for i, (valeur, acces) in enumerate(cases):
        y = 128 + i * 42
        d.boite(58, y, 164, 32, teinte="trait")
        d.texte(140, y + 21, valeur, taille=12)
        d.texte(300, y + 21, acces, taille=12, couleur="encre2")
    d.boite(394, 86, 326, 176, teinte="s1")
    d.texte(557, 112, "Dictionnaire : lu par clé", taille=13, gras=True)
    paires = [("nom", "Awa Kone"), ("poste", "Assistante RH"), ("salaire_fcfa", "250000")]
    for i, (cle, valeur) in enumerate(paires):
        y = 128 + i * 42
        d.texte(412, y + 21, cle, taille=12, gras=True, ancre="start")
        d.fleche(516, y + 16, 538, y + 16, teinte="s1")
        d.boite(548, y, 154, 32, teinte="trait")
        d.texte(625, y + 21, valeur, taille=11)
    d.texte(380, 294, "Ajoutez une colonne au fichier : les positions se décalent, les clés tiennent.",
            taille=12, gras=True, couleur="encre2")
    return d


def normaliser_chaine() -> Dessin:
    """J10 : comparer deux noms suppose de les avoir mis dans la même forme."""
    d = Dessin(760, 310, "Mettre deux noms dans la même forme avant de les comparer")
    d.texte(380, 34, "Deux noms identiques à l'oeil peuvent différer pour la machine.",
            taille=15, gras=True)
    d.texte(380, 56, "Espaces en trop, majuscules, casse : on normalise avant de comparer.",
            taille=12, couleur="encre2")
    etapes = [(40, "\"  AWA kone \"", "saisi à la main", "critique"),
              (222, ".strip()", "sans les espaces", "s2"),
              (404, ".lower()", "tout en minuscules", "s2"),
              (586, "\"awa kone\"", "comparable", "bon")]
    for x, valeur, libelle, teinte in etapes:
        d.boite(x, 104, 134, 64, teinte=teinte)
        d.texte(x + 67, 132, valeur, taille=13, gras=True)
        d.texte(x + 67, 154, libelle, taille=11, couleur="encre2")
    for x in (178, 360, 542):
        d.fleche(x, 136, x + 38, 136, teinte="attenue")
    d.boite(40, 206, 330, 62, teinte="critique", tirets=True)
    d.texte(205, 230, "\"Awa Kone\" == \"awa kone\"", taille=13, gras=True, couleur="critique")
    d.texte(205, 250, "faux : la machine compare caractère par caractère", taille=11, couleur="encre2")
    d.boite(400, 206, 320, 62, teinte="bon")
    d.texte(560, 230, "normaliser puis comparer", taille=13, gras=True)
    d.texte(560, 250, "une seule fonction, appelée des deux côtés", taille=11, couleur="encre2")
    d.texte(380, 296, "Affichez le nom tel qu'il a été saisi ; comparez la forme normalisée.",
            taille=12, gras=True, couleur="encre2")
    return d


def csv_encodage() -> Dessin:
    """J12 : les mêmes octets lus dans deux encodages ne donnent pas le même nom."""
    d = Dessin(760, 320, "Le même fichier lu dans deux encodages")
    d.texte(380, 34, "Un accent cassé n'est pas une faute de frappe.", taille=15, gras=True)
    d.texte(380, 56, "C'est le fichier lu avec le mauvais encodage.", taille=12, couleur="encre2")
    d.boite(290, 86, 180, 58, teinte="trait")
    d.texte(380, 110, "effectif.csv", taille=13, gras=True)
    d.texte(380, 132, "des octets, rien de plus", taille=11, couleur="encre2")
    d.boite(40, 196, 320, 80, teinte="bon")
    d.texte(200, 222, "ouvert en utf-8", taille=13, gras=True)
    d.texte(200, 248, "Céline Koné", taille=15)
    d.texte(200, 268, "le nom tel qu'il a été saisi", taille=11, couleur="encre2")
    d.boite(400, 196, 320, 80, teinte="critique")
    d.texte(560, 222, "ouvert sans encodage déclaré", taille=13, gras=True)
    d.texte(560, 248, "CÃ©line KonÃ©", taille=15, couleur="critique")
    d.texte(560, 268, "les mêmes octets, mal interprétés", taille=11, couleur="encre2")
    d.fleche(330, 150, 240, 190, teinte="bon")
    d.fleche(430, 150, 520, 190, teinte="critique")
    d.texte(380, 306, "Déclarez encoding=\"utf-8\" à l'ouverture, en lecture comme en écriture.",
            taille=12, gras=True, couleur="encre2")
    return d


def rouge_puis_vert() -> Dessin:
    """J14 : un test qui n'a jamais échoué ne prouve rien ; il doit rougir d'abord."""
    d = Dessin(760, 310, "Un test rougit d'abord, puis il verdit")
    d.texte(380, 34, "Un test qui passe du premier coup ne prouve rien.", taille=15, gras=True)
    d.texte(380, 56, "Faites-le échouer une fois : vous saurez qu'il regarde la bonne chose.",
            taille=12, couleur="encre2")
    etapes = [(40, "1. Écrire le test", "il décrit la règle attendue", "s1"),
              (280, "2. Le voir rouge", "la règle n'est pas encore tenue", "critique"),
              (520, "3. Le voir vert", "le code tient la règle", "bon")]
    for x, titre, libelle, teinte in etapes:
        d.boite(x, 104, 200, 72, teinte=teinte)
        d.texte(x + 100, 134, titre, taille=13, gras=True)
        d.texte(x + 100, 158, libelle, taille=11, couleur="encre2")
    d.fleche(248, 140, 272, 140, teinte="critique")
    d.fleche(488, 140, 512, 140, teinte="bon")
    d.boite(140, 214, 480, 62, teinte="trait", tirets=True)
    d.texte(380, 240, "Trois tests pour une règle à seuil : 11 mois, 12 mois, 13 mois.",
            taille=13, gras=True)
    d.texte(380, 262, "La borne est l'endroit où les bugs se logent ; elle mérite son propre test.",
            taille=11, couleur="encre2")
    d.texte(380, 298, "Un test porte le nom de la règle, pas le nom de la fonction testée.",
            taille=12, gras=True, couleur="encre2")
    return d


def effectif_par_service() -> Dessin:
    """J22 : un effectif se lit d'un coup d'oeil en barres, service par service."""
    d = Dessin(760, 350, "Effectif par service, en barres")
    d.texte(380, 34, "Compter par service avant de filtrer.", taille=15, gras=True)
    d.texte(380, 56, "Une barre par service, triée : la lecture ne demande aucun effort.",
            taille=12, couleur="encre2")
    base, haut = 266, 96
    services = [("Production", 18, "s1"), ("Commercial", 12, "s1"), ("Logistique", 9, "s1"),
                ("Administration", 6, "s2"), ("Direction", 3, "s2")]
    maximum = 18
    d.ajouter('<line x1="60" y1="' + str(base) + '" x2="716" y2="' + str(base)
              + '" stroke="var(--trait)" stroke-width="2"/>')
    for i, (service, effectif, teinte) in enumerate(services):
        x = 84 + i * 128
        hauteur = (base - haut) * effectif / maximum
        d.barre(x, base - hauteur, 84, hauteur, teinte)
        d.texte(x + 42, base - hauteur - 10, str(effectif), taille=13, gras=True)
        d.texte(x + 42, base + 22, service, taille=11, couleur="encre2")
    d.texte(380, base + 56, "Les barres partent de zéro : couper l'axe exagère les écarts.",
            taille=12, gras=True, couleur="encre2")
    d.texte(380, base + 78, "Classez du plus grand au plus petit ; l'ordre alphabétique ne dit rien.",
            taille=12, couleur="encre2")
    return d


def masse_salariale_mois() -> Dessin:
    """J28 : une somme par mois se lit en courbe ; la marche d'escalier a une cause."""
    d = Dessin(760, 350, "Masse salariale mois par mois")
    d.texte(380, 34, "Une somme agrégée par mois raconte une histoire.", taille=15, gras=True)
    d.texte(380, 56, "La marche de juillet, ce sont trois embauches : la courbe pose la question.",
            taille=12, couleur="encre2")
    base, haut, gauche, droite = 266, 106, 70, 710
    valeurs = [8.2, 8.2, 8.4, 8.4, 8.4, 8.6, 10.1, 10.1, 10.3, 10.3, 10.6, 10.6]
    mois = ["jan", "fév", "mar", "avr", "mai", "juin", "juil", "août", "sep", "oct", "nov", "déc"]
    bas, cime = 7.5, 11.0
    d.ajouter('<line x1="' + str(gauche) + '" y1="' + str(base) + '" x2="' + str(droite)
              + '" y2="' + str(base) + '" stroke="var(--trait)" stroke-width="2"/>')
    d.ajouter('<line x1="' + str(gauche) + '" y1="' + str(haut - 16) + '" x2="' + str(gauche)
              + '" y2="' + str(base) + '" stroke="var(--trait)" stroke-width="2"/>')
    pas = (droite - gauche) / (len(valeurs) - 1)
    points = []
    for i, valeur in enumerate(valeurs):
        x = gauche + i * pas
        y = base - (base - haut) * (valeur - bas) / (cime - bas)
        points.append((x, y))
        d.texte(x, base + 22, mois[i], taille=11, couleur="encre2")
    chemin = " ".join(("M" if i == 0 else "L") + " " + format(x, ".2f") + " " + format(y, ".2f")
                      for i, (x, y) in enumerate(points))
    d.ajouter('<path d="' + chemin + '" fill="none" stroke="var(--s1)" stroke-width="3"/>')
    for x, y in points:
        d.ajouter('<circle cx="' + format(x, ".2f") + '" cy="' + format(y, ".2f")
                  + '" r="4" fill="var(--s1)"/>')
    rupture = points[6]
    d.ajouter('<line x1="' + format(rupture[0], ".2f") + '" y1="' + str(haut - 10) + '" x2="'
              + format(rupture[0], ".2f") + '" y2="' + str(base)
              + '" stroke="var(--s2)" stroke-width="2" stroke-dasharray="5 4"/>')
    d.texte(rupture[0] + 8, haut - 14, "trois embauches en juillet", taille=11, ancre="start",
            couleur="s2")
    d.texte(gauche - 6, haut - 32, "millions de FCFA", taille=11, ancre="start", couleur="encre2")
    d.texte(380, base + 56, "Une agrégation par mois se demande à la base, pas en parcourant les fiches.",
            taille=12, gras=True, couleur="encre2")
    d.texte(380, base + 78, "Une requête rend douze lignes ; mille allers-retours en rendraient autant, bien plus lentement.",
            taille=12, couleur="encre2")
    return d


def issues_du_post() -> Dessin:
    """J18 : une création a trois issues, et chacune a son code."""
    d = Dessin(760, 330, "Les trois issues d'une création par POST")
    d.texte(380, 34, "Une création a trois issues, et chacune a son code.", taille=15, gras=True)
    d.texte(380, 56, "Le code dit à l'appelant quoi faire ensuite ; le corps lui dit pourquoi.",
            taille=12, couleur="encre2")
    d.boite(290, 86, 180, 56, teinte="s1")
    d.texte(380, 110, "POST /salaries", taille=13, gras=True)
    d.texte(380, 130, "un salarié à créer", taille=11, couleur="encre2")
    issues = [(40, "201 Created", "le salarié existe", "la fiche créée", "bon"),
              (290, "422", "la saisie est mal formée", "le champ fautif, nommé", "s2"),
              (540, "409", "le matricule existe déjà", "le conflit, expliqué", "critique")]
    for x, code, quand, corps, teinte in issues:
        d.boite(x, 192, 180, 92, teinte=teinte)
        d.texte(x + 90, 218, code, taille=15, gras=True)
        d.texte(x + 90, 242, quand, taille=11, couleur="encre2")
        d.texte(x + 90, 266, corps, taille=11, couleur="encre2")
    d.fleche(340, 146, 170, 186, teinte="bon")
    d.fleche(380, 146, 380, 186, teinte="s2")
    d.fleche(420, 146, 610, 186, teinte="critique")
    d.texte(380, 314, "Un message d'erreur nomme le champ fautif ; il ne recopie jamais la trace Python.",
            taille=12, gras=True, couleur="encre2")
    return d


def secrets_hors_du_code() -> Dessin:
    """J20 : un secret écrit dans le code part avec le code, pour toujours."""
    d = Dessin(760, 330, "Où vit un secret, et où il ne vit jamais")
    d.texte(380, 34, "Un secret écrit dans le code part avec le code.", taille=15, gras=True)
    d.texte(380, 56, "Retiré plus tard, il reste dans l'historique du dépôt.", taille=12, couleur="encre2")
    d.boite(40, 100, 200, 100, teinte="critique", tirets=True)
    d.texte(140, 128, "api.py", taille=13, gras=True)
    d.texte(140, 152, "CLE = \"sk-vrai-secret\"", taille=11, couleur="critique")
    d.texte(140, 176, "versionné, donc public", taille=11, couleur="encre2")
    d.boite(280, 100, 200, 100, teinte="bon")
    d.texte(380, 128, ".env", taille=13, gras=True)
    d.texte(380, 152, "CLE=sk-vrai-secret", taille=11, couleur="encre2")
    d.texte(380, 176, "ignoré par git", taille=11, couleur="encre2")
    d.boite(520, 100, 200, 100, teinte="s1")
    d.texte(620, 128, ".env.exemple", taille=13, gras=True)
    d.texte(620, 152, "CLE=a-remplir", taille=11, couleur="encre2")
    d.texte(620, 176, "versionné, sans valeur", taille=11, couleur="encre2")
    d.boite(180, 236, 400, 58, teinte="trait")
    d.texte(380, 260, "Le code lit la variable d'environnement, jamais le fichier en dur.",
            taille=13, gras=True)
    d.texte(380, 282, "os.environ[\"CLE\"] : absente, l'application refuse de démarrer.",
            taille=11, couleur="encre2")
    d.texte(380, 318, "Un secret publié par erreur se révoque : le retirer du code ne suffit pas.",
            taille=12, gras=True, couleur="encre2")
    return d


def formulaire_vers_coeur() -> Dessin:
    """J23 : l'écran recueille, le cœur décide, l'écran rend compte."""
    d = Dessin(760, 330, "Un formulaire branché sur le cœur métier")
    d.texte(380, 34, "L'écran recueille ; le cœur décide.", taille=15, gras=True)
    d.texte(380, 56, "La règle d'embauche ne se réécrit pas dans l'écran : elle s'appelle.",
            taille=12, couleur="encre2")
    etapes = [(40, "Formulaire", "nom, poste, salaire", "s1"),
              (280, "Validation", "des champs bien formés", "s2"),
              (520, "Cœur métier", "la règle d'embauche", "s3")]
    for x, titre, libelle, teinte in etapes:
        d.boite(x, 104, 200, 74, teinte=teinte)
        d.texte(x + 100, 134, titre, taille=14, gras=True)
        d.texte(x + 100, 158, libelle, taille=11, couleur="encre2")
    d.fleche(248, 140, 272, 140, teinte="s2")
    d.fleche(488, 140, 512, 140, teinte="s3")
    d.boite(270, 222, 450, 62, teinte="bon")
    d.texte(495, 246, "Refus du cœur : le message revient dans l'écran", taille=13, gras=True)
    d.texte(495, 268, "le champ fautif est désigné, la saisie est conservée", taille=11, couleur="encre2")
    d.fleche(560, 186, 470, 216, teinte="bon")
    d.texte(150, 246, "Jamais deux règles", taille=13, gras=True, couleur="critique")
    d.texte(150, 268, "une dans l'écran, une dans le cœur", taille=11, couleur="encre2")
    d.texte(380, 316, "L'écran peut changer de technologie ; la règle, elle, reste au même endroit.",
            taille=12, gras=True, couleur="encre2")
    return d


def effet_du_cache() -> Dessin:
    """J25 : le cache ne rend pas le calcul plus rapide, il l'évite."""
    d = Dessin(760, 392, "Temps de réponse d'un écran, avec et sans cache")
    d.texte(380, 34, "Le cache ne rend pas le calcul rapide : il l'évite.", taille=15, gras=True)
    d.texte(380, 56, "Même écran, même fichier de 5000 lignes, quatre interactions de suite.",
            taille=12, couleur="encre2")
    gauche, large = 230, 420
    series = [("Sans cache", [2.1, 2.1, 2.0, 2.1], "s2"), ("Avec cache", [2.1, 0.1, 0.1, 0.1], "s1")]
    maximum = 2.4
    y = 104
    for titre, valeurs, teinte in series:
        d.texte(40, y + 18, titre, taille=13, gras=True, ancre="start")
        for i, valeur in enumerate(valeurs):
            yy = y + i * 24
            largeur = large * valeur / maximum
            d.ajouter('<rect x="' + str(gauche) + '" y="' + str(yy) + '" width="'
                      + format(largeur, ".2f") + '" height="16" rx="4" fill="var(--' + teinte + ')"/>')
            d.texte(gauche + largeur + 10, yy + 13, format(valeur, ".1f") + " s", taille=11,
                    ancre="start", couleur="encre2")
            d.texte(gauche - 10, yy + 13, "passage " + str(i + 1), taille=11, ancre="end",
                    couleur="attenue")
        y += 120
    d.texte(380, 352, "Le premier passage coûte autant : c'est lui qui remplit le cache.",
            taille=12, gras=True, couleur="encre2")
    d.texte(380, 376, "Un cache sans durée de vie finit par servir des chiffres faux.",
            taille=12, couleur="encre2")
    return d


def projet_django() -> Dessin:
    """J26 : ce qu'un projet Django pose sur la table avant la première ligne écrite."""
    d = Dessin(760, 330, "Ce qu'un projet Django apporte dès le départ")
    d.texte(380, 34, "Django arrive avec ce qu'une application de gestion redemande toujours.",
            taille=15, gras=True)
    d.texte(380, 56, "Vous écrivez les règles ; le reste est déjà là, et il est éprouvé.",
            taille=12, couleur="encre2")
    acquis = [(40, "Comptes et sessions", "connexion, déconnexion"),
              (226, "Administration", "un back-office immédiat"),
              (412, "Migrations", "la base suit les modèles"),
              (598, "Sécurité", "CSRF, mots de passe hachés")]
    for x, titre, libelle in acquis:
        d.boite(x, 100, 162, 76, teinte="s1")
        d.texte(x + 81, 128, titre, taille=12, gras=True)
        d.texte(x + 81, 152, libelle, taille=11, couleur="encre2")
    d.boite(40, 206, 330, 80, teinte="s3")
    d.texte(205, 232, "Ce que vous écrivez", taille=13, gras=True)
    d.texte(205, 256, "les modèles, les règles, les écrans", taille=11, couleur="encre2")
    d.texte(205, 276, "autrement dit, votre métier", taille=11, couleur="encre2")
    d.boite(400, 206, 320, 80, teinte="trait", tirets=True)
    d.texte(560, 232, "manage.py, config/, salaries/", taille=13, gras=True)
    d.texte(560, 256, "un projet, puis une application par domaine", taille=11, couleur="encre2")
    d.texte(560, 276, "la même disposition dans toutes les équipes", taille=11, couleur="encre2")
    d.texte(380, 318, "Choisir Django, c'est accepter ses conventions et gagner le temps qu'elles font économiser.",
            taille=12, gras=True, couleur="encre2")
    return d


def admin_et_metier() -> Dessin:
    """J29 : l'administration édite les données ; elle ne décide pas des règles."""
    d = Dessin(760, 320, "Ce que l'administration couvre, et où elle s'arrête")
    d.texte(380, 34, "L'administration est un back-office, pas votre application.", taille=15, gras=True)
    d.texte(380, 56, "Elle sert l'équipe interne ; elle ne porte pas la règle métier.",
            taille=12, couleur="encre2")
    d.boite(40, 92, 330, 170, teinte="bon")
    d.texte(205, 118, "Ce qu'elle couvre très bien", taille=13, gras=True)
    for i, ligne in enumerate(["corriger une fiche à la main",
                               "chercher, filtrer, trier",
                               "voir qui a changé quoi",
                               "ouvrir l'accès à un gestionnaire"]):
        d.texte(205, 146 + i * 28, ligne, taille=12, couleur="encre2")
    d.boite(394, 92, 326, 170, teinte="critique", tirets=True)
    d.texte(557, 118, "Ce qu'elle ne doit pas porter", taille=13, gras=True)
    for i, ligne in enumerate(["le calcul des congés",
                               "les règles d'embauche",
                               "un écran pour les managers",
                               "les accès des salariés"]):
        d.texte(557, 146 + i * 28, ligne, taille=12, couleur="encre2")
    d.texte(380, 296, "Un compte d'administration ne se crée jamais dans une migration : chacun le sien.",
            taille=12, gras=True, couleur="encre2")
    return d


def double_validation() -> Dessin:
    """J31 : le navigateur conseille, le serveur décide."""
    d = Dessin(760, 320, "Validation côté navigateur et validation côté serveur")
    d.texte(380, 34, "Le navigateur conseille ; le serveur décide.", taille=15, gras=True)
    d.texte(380, 56, "Tout ce qui arrive au serveur a pu être fabriqué à la main.",
            taille=12, couleur="encre2")
    d.boite(40, 96, 280, 96, teinte="s2")
    d.texte(180, 124, "Dans le navigateur", taille=13, gras=True)
    d.texte(180, 148, "champ obligatoire, format attendu", taille=11, couleur="encre2")
    d.texte(180, 170, "confort de saisie, rien de plus", taille=11, couleur="encre2")
    d.boite(440, 96, 280, 96, teinte="bon")
    d.texte(580, 124, "Sur le serveur", taille=13, gras=True)
    d.texte(580, 148, "types, bornes, règles métier", taille=11, couleur="encre2")
    d.texte(580, 170, "la seule validation qui engage", taille=11, couleur="encre2")
    d.fleche(328, 144, 432, 144, teinte="attenue")
    d.boite(140, 222, 480, 62, teinte="critique", tirets=True)
    d.texte(380, 246, "Une requête peut arriver sans passer par votre page", taille=13, gras=True,
            couleur="critique")
    d.texte(380, 268, "un outil en ligne de commande suffit : le serveur revalide tout",
            taille=11, couleur="encre2")
    d.texte(380, 308, "Le formulaire réaffiche la saisie et désigne le champ fautif, sans tout effacer.",
            taille=12, gras=True, couleur="encre2")
    return d


def parcours_connexion() -> Dessin:
    """J32 : d'une page protégée à la connexion, puis retour au point de départ."""
    d = Dessin(760, 320, "Le chemin d'une connexion")
    d.texte(380, 34, "Une page protégée renvoie vers la connexion, puis ramène au point de départ.",
            taille=15, gras=True)
    d.texte(380, 56, "Le détour est transparent pour l'utilisateur ; il tient en un paramètre.",
            taille=12, couleur="encre2")
    etapes = [(30, "/effectif", "demandé sans compte", "s2"),
              (218, "/connexion", "avec ?next=/effectif", "s1"),
              (406, "Session ouverte", "le compte est reconnu", "s3"),
              (594, "/effectif", "servi, cette fois", "bon")]
    for x, titre, libelle, teinte in etapes:
        d.boite(x, 110, 166, 76, teinte=teinte)
        d.texte(x + 83, 140, titre, taille=13, gras=True)
        d.texte(x + 83, 164, libelle, taille=11, couleur="encre2")
    for x in (196, 384, 572):
        d.fleche(x, 148, x + 22, 148, teinte="attenue")
    d.boite(140, 222, 480, 62, teinte="trait", tirets=True)
    d.texte(380, 246, "Un mot de passe ne se garde jamais en clair", taille=13, gras=True)
    d.texte(380, 268, "la base garde une empreinte ; même volée, elle ne rend pas le mot de passe",
            taille=11, couleur="encre2")
    d.texte(380, 308, "Déconnexion : la session est détruite côté serveur, pas seulement oubliée côté page.",
            taille=12, gras=True, couleur="encre2")
    return d


def coeur_partage() -> Dessin:
    """J34 : la même règle, appelée par trois portes d'entrée."""
    d = Dessin(760, 330, "Une règle, trois portes d'entrée")
    d.texte(380, 34, "Trois portes d'entrée, une seule règle.", taille=15, gras=True)
    d.texte(380, 56, "Une commande de gestion n'est qu'un appelant de plus.", taille=12, couleur="encre2")
    portes = [(40, "API", "une requête HTTP"),
              (290, "Écran", "un formulaire"),
              (540, "Commande", "un import de fichier")]
    for x, titre, libelle in portes:
        d.boite(x, 96, 180, 70, teinte="s1")
        d.texte(x + 90, 124, titre, taille=13, gras=True)
        d.texte(x + 90, 148, libelle, taille=11, couleur="encre2")
    d.boite(240, 216, 280, 76, teinte="s3")
    d.texte(380, 246, "Cœur métier", taille=14, gras=True)
    d.texte(380, 270, "embaucher, calculer, refuser", taille=11, couleur="encre2")
    d.fleche(130, 172, 300, 210, teinte="s1")
    d.fleche(380, 172, 380, 210, teinte="s1")
    d.fleche(630, 172, 460, 210, teinte="s1")
    d.texte(380, 318, "Si la règle change, elle change une fois : les trois portes en héritent.",
            taille=12, gras=True, couleur="encre2")
    return d


def sept_semaines() -> Dessin:
    """J35 : la route parcourue, semaine par semaine, et ce qui se montre."""
    d = Dessin(760, 320, "Les sept semaines du parcours, d'un bout à l'autre")
    d.texte(380, 34, "Trente-cinq journées, sept marches.", taille=15, gras=True)
    d.texte(380, 56, "La démonstration finale repart du début : c'est elle qui rend la route visible.",
            taille=12, couleur="encre2")
    semaines = [("S1", "Les bases"), ("S2", "Les données"), ("S3", "Le code juste"),
                ("S4", "L'API"), ("S5", "L'écran"), ("S6", "Django"), ("S7", "La mise en service")]
    base, haut = 232, 110
    for i, (code, titre) in enumerate(semaines):
        x = 40 + i * 100
        hauteur = (base - haut) * (i + 1) / len(semaines)
        teinte = "s1" if i < 5 else "s3"
        d.barre(x, base - hauteur, 80, hauteur, teinte)
        d.texte(x + 40, base - hauteur - 10, code, taille=12, gras=True)
        d.texte(x + 40, base + 22, titre, taille=11, couleur="encre2")
    d.ajouter('<line x1="30" y1="' + str(base) + '" x2="730" y2="' + str(base)
              + '" stroke="var(--trait)" stroke-width="2"/>')
    d.texte(380, base + 54, "Cinq minutes de démonstration : le problème, l'écran, une règle refusée, la suite.",
            taille=12, gras=True, couleur="encre2")
    d.texte(380, base + 76, "Montrez un refus, pas seulement un succès : c'est le refus qui prouve la règle.",
            taille=12, couleur="encre2")
    return d


def objet_ou_composition() -> Dessin:
    """Développeur Python, module 04 : la règle vit près des données, et l'héritage se mérite."""
    d = Dessin(760, 340, "Une classe porte ses règles ; l'héritage se mérite")
    d.texte(380, 34, "Une classe réunit des données et les règles qui les concernent.", taille=15,
            gras=True)
    d.texte(380, 56, "Si la règle vit ailleurs, la classe n'est qu'un dictionnaire déguisé.",
            taille=12, couleur="encre2")
    d.boite(40, 92, 320, 136, teinte="s3")
    d.texte(200, 118, "Lot", taille=14, gras=True)
    for i, ligne in enumerate(["poids_kg, qualite, humide", "prix_fcfa() applique la pénalité",
                               "immuable : frozen=True"]):
        d.texte(200, 148 + i * 26, ligne, taille=11, couleur="encre2")
    d.boite(400, 92, 320, 136, teinte="s1")
    d.texte(560, 118, "Producteur", taille=14, gras=True)
    for i, ligne in enumerate(["nom, lots", "total_fcfa() somme ses lots",
                               "contient des Lot : composition"]):
        d.texte(560, 148 + i * 26, ligne, taille=11, couleur="encre2")
    d.fleche(392, 160, 368, 160, teinte="s1")
    d.boite(40, 258, 320, 58, teinte="bon")
    d.texte(200, 282, "Composition : A contient B", taille=13, gras=True)
    d.texte(200, 302, "le cas courant, souple et sans surprise", taille=11, couleur="encre2")
    d.boite(400, 258, 320, 58, teinte="critique", tirets=True)
    d.texte(560, 282, "Héritage : A est un B", taille=13, gras=True, couleur="critique")
    d.texte(560, 302, "seulement si tout ce qui vaut de B vaut de A", taille=11, couleur="encre2")
    return d


def flux_ou_liste() -> Dessin:
    """Développeur Python, module 06 : une liste occupe la mémoire, un générateur la traverse."""
    d = Dessin(760, 330, "Construire une liste entière, ou produire au fil de l'eau")
    d.texte(380, 34, "Une liste occupe la mémoire ; un générateur la traverse.", taille=15, gras=True)
    d.texte(380, 56, "Même résultat, même code ou presque, et une machine qui ne sature plus.",
            taille=12, couleur="encre2")
    d.texte(40, 100, "Liste intermédiaire", taille=13, gras=True, ancre="start")
    for i in range(8):
        x = 230 + i * 56
        d.boite(x, 86, 48, 34, teinte="s2")
    d.texte(690, 108, "en mémoire", taille=11, ancre="start", couleur="encre2")
    d.texte(40, 128, "les 8 valeurs existent en même temps", taille=11, ancre="start", couleur="encre2")
    d.texte(40, 194, "Générateur", taille=13, gras=True, ancre="start")
    for i in range(8):
        x = 230 + i * 56
        teinte = "s1" if i == 3 else "trait"
        d.boite(x, 180, 48, 34, teinte=teinte, tirets=i != 3)
    d.texte(690, 202, "une à la fois", taille=11, ancre="start", couleur="encre2")
    d.texte(40, 222, "yield rend la valeur, puis reprend là", taille=11, ancre="start", couleur="encre2")
    d.boite(140, 258, 480, 58, teinte="trait", tirets=True)
    d.texte(380, 282, "Un générateur ne se parcourt qu'une fois", taille=13, gras=True)
    d.texte(380, 302, "pour le relire, convertissez-le en liste, en connaissance de cause",
            taille=11, couleur="encre2")
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
    "python-migrations.svg": migrations,
    "python-django-mvt.svg": django_mvt,
    "python-roles-permissions.svg": roles_permissions,
    "python-arrondi-fcfa.svg": arrondi_fcfa,
    "python-boucle-for.svg": boucle_for,
    "python-liste-ou-dictionnaire.svg": liste_ou_dictionnaire,
    "python-normaliser-chaine.svg": normaliser_chaine,
    "python-csv-encodage.svg": csv_encodage,
    "python-rouge-puis-vert.svg": rouge_puis_vert,
    "python-effectif-par-service.svg": effectif_par_service,
    "python-masse-salariale-mois.svg": masse_salariale_mois,
    "python-issues-du-post.svg": issues_du_post,
    "python-secrets-hors-du-code.svg": secrets_hors_du_code,
    "python-formulaire-vers-coeur.svg": formulaire_vers_coeur,
    "python-effet-du-cache.svg": effet_du_cache,
    "python-projet-django.svg": projet_django,
    "python-admin-et-metier.svg": admin_et_metier,
    "python-double-validation.svg": double_validation,
    "python-parcours-connexion.svg": parcours_connexion,
    "python-coeur-partage.svg": coeur_partage,
    "python-sept-semaines.svg": sept_semaines,
    "python-objet-ou-composition.svg": objet_ou_composition,
    "python-flux-ou-liste.svg": flux_ou_liste,
}
