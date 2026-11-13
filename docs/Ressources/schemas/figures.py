"""Les schémas du parcours IA agentique, un par fonction.

Chaque figure répond à une question que le texte seul traite mal : un cycle, un ordre d'échanges, une
comparaison à quatre entrées, une reprise après panne, une frontière de risque, un ordre de grandeur. Là où
une phrase suffit, il n'y a pas de figure.
"""
from trousse import Dessin


def boucle_agent() -> Dessin:
    """Séance 1 : percevoir, raisonner, agir, observer, et ce qui arrête la boucle."""
    d = Dessin(760, 360, "La boucle d'un agent et ses conditions d'arrêt")
    etapes = [("Percevoir", "lit le contexte", 70), ("Raisonner", "choisit l'action", 250),
              ("Agir", "appelle un outil", 430), ("Observer", "lit le résultat", 610)]
    for nom, sous_titre, x in etapes:
        d.boite(x, 110, 150, 72, teinte="s1")
        d.texte(x + 75, 139, nom, taille=15, gras=True)
        d.texte(x + 75, 161, sous_titre, taille=12, couleur="encre2")
    for x in (220, 400, 580):
        d.fleche(x, 146, x + 28, 146, teinte="s1")
    d.ajouter('<path d="M 685 182 L 685 250 L 145 250 L 145 182" fill="none" stroke="var(--s1)"'
              ' stroke-width="2" marker-end="url(#pointe-s1)"/>')
    d.texte(415, 270, "tant qu'aucune condition d'arrêt n'est remplie", taille=12, couleur="encre2")
    d.boite(255, 292, 250, 46, teinte="critique", tirets=True)
    d.texte(380, 311, "Conditions d'arrêt", taille=12, gras=True, couleur="critique")
    d.texte(380, 328, "objectif atteint · plafond d'étapes · budget", taille=11, couleur="encre2")
    d.texte(380, 40, "Le modèle choisit l'étape suivante ; le code borne la boucle.",
            taille=14, gras=True)
    d.texte(380, 62, "Sans borne explicite, un agent répète les mêmes appels jusqu'à épuiser son budget.",
            taille=12, couleur="encre2")
    return d


def appel_outil() -> Dessin:
    """Séance 2 : qui parle à qui, dans quel ordre, et où se place la validation des arguments."""
    d = Dessin(760, 400, "Le cycle d'un appel d'outil")
    voies = [("Modèle", 110, "s1"), ("Votre code", 380, "s3"), ("Outil", 650, "s2")]
    for nom, x, teinte in voies:
        d.boite(x - 85, 40, 170, 40, teinte=teinte)
        d.texte(x, 65, nom, taille=14, gras=True)
        d.ajouter(f'<line x1="{x}" y1="80" x2="{x}" y2="360" stroke="var(--grille)" stroke-width="1.5"'
                  ' stroke-dasharray="4 4"/>')
    echanges = [(110, 380, 120, "demande l'outil et ses arguments", "s1"),
                (380, 380, 165, "valide le contrat : types, bornes, chemins", "s3"),
                (380, 650, 215, "exécute si le contrat passe", "s3"),
                (650, 380, 260, "résultat, ou erreur lisible", "s2"),
                (380, 110, 305, "observation renvoyée au modèle", "s3")]
    for depart, arrivee, y, libelle, teinte in echanges:
        if depart == arrivee:
            d.ajouter(f'<path d="M {depart} {y - 12} q 60 0 60 12 q 0 12 -60 12" fill="none"'
                      f' stroke="var(--{teinte})" stroke-width="2" marker-end="url(#pointe-{teinte})"/>')
            d.texte(depart + 80, y + 4, libelle, taille=11, ancre="start", couleur="encre2")
        else:
            sens = 1 if arrivee > depart else -1
            d.fleche(depart + 8 * sens, y, arrivee - 8 * sens, y, teinte=teinte)
            d.texte((depart + arrivee) / 2, y - 10, libelle, taille=11, couleur="encre2")
    d.texte(380, 390, "Une erreur d'outil devient un résultat, jamais une exception qui arrête la boucle.",
            taille=12, gras=True, couleur="encre2")
    return d


def quatre_familles() -> Dessin:
    """Séance 1 : ce qui sépare un chatbot, un RAG, un workflow et un agent."""
    d = Dessin(780, 330, "Quatre familles de systèmes sur un même besoin")
    colonnes = [
        ("Chatbot", ["message", "réponse"], "une réponse par message", "attenue"),
        ("RAG", ["question", "recherche", "réponse"], "un seul passage", "s3"),
        ("Workflow", ["étape 1", "étape 2", "étape 3"], "ordre fixé par le code", "s2"),
        ("Agent", ["décider", "agir", "observer"], "ordre choisi par le modèle", "s1"),
    ]
    for i, (nom, etapes, note, teinte) in enumerate(colonnes):
        x = 30 + i * 190
        d.texte(x + 80, 48, nom, taille=15, gras=True)
        for j, etape in enumerate(etapes):
            y = 70 + j * 56
            d.boite(x, y, 160, 38, teinte=teinte)
            d.texte(x + 80, y + 24, etape, taille=12)
            if j < len(etapes) - 1:
                d.fleche(x + 80, y + 38, x + 80, y + 52, teinte=teinte)
        if nom == "Agent":
            d.ajouter(f'<path d="M {x + 160} {234} q 26 -56 0 -112" fill="none" stroke="var(--s1)"'
                      ' stroke-width="2" marker-end="url(#pointe-s1)"/>')
        d.lignes_de_texte(x + 80, 272, _couper(note, 22), taille=11)
    d.texte(390, 310, "Si l'ordre des étapes est connu d'avance, un workflow fait mieux qu'un agent.",
            taille=12, gras=True, couleur="encre2")
    return d


def etat_reprise() -> Dessin:
    """Séance 4 : état persistant, interruption, reprise sans doublon."""
    d = Dessin(760, 330, "État persistant et reprise sans doublon")
    etats = [("Brouillon", 24, 150), ("Validation demandée", 210, 180),
             ("Approuvé", 426, 140), ("Enregistré", 600, 140)]
    for nom, x, largeur in etats:
        d.boite(x, 90, largeur, 54, teinte="s1")
        d.texte(x + largeur / 2, 122, nom, taille=13, gras=True)
    for depart, arrivee in ((174, 210), (390, 426), (566, 600)):
        d.fleche(depart, 117, arrivee - 4, 117, teinte="s1")
    d.ajouter('<path d="M 300 144 L 300 192 L 670 192 L 670 148" fill="none" stroke="var(--critique)"'
              ' stroke-width="2" stroke-dasharray="5 4" marker-end="url(#pointe-critique)"/>')
    d.texte(485, 210, "reprise après interruption : la clé d'idempotence mène à l'état déjà atteint",
            taille=12, couleur="critique")
    d.boite(230, 236, 300, 56, teinte="trait", tirets=True)
    d.texte(380, 258, "Fichier d'état", taille=12, gras=True)
    d.texte(380, 277, "chaque transition est écrite avant d'être annoncée", taille=11, couleur="encre2")
    d.texte(380, 48, "Une reprise lit l'état, elle ne rejoue pas le passé.", taille=14, gras=True)
    return d


def chaine_mcp() -> Dessin:
    """Séance 5 : ce que MCP déplace, du code de l'agent vers un serveur interrogeable."""
    d = Dessin(780, 300, "La chaîne MCP, du client au serveur d'outils")
    etages = [("Agent", 26, "s1", ["décide d'appeler", "un outil"]),
              ("Client MCP", 214, "s3", ["découvre les outils", "et leurs schémas"]),
              ("Serveur MCP", 402, "s3", ["expose les outils", "et leurs contrats"]),
              ("Système réel", 590, "s2", ["base, fichiers,", "API"])]
    for nom, x, teinte, lignes in etages:
        d.boite(x, 90, 164, 96, teinte=teinte)
        d.texte(x + 82, 118, nom, taille=14, gras=True)
        d.lignes_de_texte(x + 82, 140, lignes, taille=11)
    for x in (190, 378, 566):
        d.fleche(x, 138, x + 20, 138, teinte="attenue")
    d.texte(390, 220, "Le contrat d'outil vit côté serveur : l'agent n'embarque plus ni schéma ni client.",
            taille=12, gras=True, couleur="encre2")
    d.boite(240, 240, 360, 44, teinte="critique", tirets=True)
    d.texte(420, 258, "Le serveur reste une frontière de confiance", taille=12, gras=True,
            couleur="critique")
    d.texte(420, 275, "un outil distant vaut une liste blanche et une limite de débit", taille=11,
            couleur="encre2")
    return d


def topologies_multi_agents() -> Dessin:
    """Séance 6 : trois façons d'assembler plusieurs agents, et ce que chacune coûte."""
    d = Dessin(780, 340, "Trois topologies multi-agents")
    def noeud(x, y, libelle, teinte="s1", l=108):
        d.boite(x, y, l, 34, teinte=teinte)
        d.texte(x + l / 2, y + 22, libelle, taille=11)

    d.texte(130, 44, "Superviseur", taille=14, gras=True)
    noeud(76, 64, "superviseur", "s2")
    for i, nom in enumerate(("analyste", "rédacteur")):
        noeud(10 + i * 130, 150, nom)
        d.fleche(130, 98, 64 + i * 130, 146, teinte="s2")
    d.lignes_de_texte(130, 212, ["un décideur, des exécutants", "coût : un tour de plus"], taille=11)

    d.texte(390, 44, "Chaîne", taille=14, gras=True)
    for i, nom in enumerate(("segmenter", "analyser", "rédiger")):
        noeud(336, 64 + i * 56, nom, "s3")
        if i:
            d.fleche(390, 54 + i * 56, 390, 60 + i * 56, teinte="s3")
    d.lignes_de_texte(390, 248, ["ordre connu d'avance", "coût : rigidité"], taille=11)

    d.texte(650, 44, "Pairs", taille=14, gras=True)
    for i, nom in enumerate(("agent A", "agent B")):
        noeud(596, 64 + i * 96, nom)
    # aller et retour tracés hors des boîtes, pour qu'aucune pointe ne mord sur un libellé
    d.ajouter('<path d="M 716 82 q 34 48 0 96" fill="none" stroke="var(--attenue)" stroke-width="2"'
              ' marker-end="url(#pointe-attenue)"/>')
    d.ajouter('<path d="M 584 178 q -34 -48 0 -96" fill="none" stroke="var(--attenue)" stroke-width="2"'
              ' marker-end="url(#pointe-attenue)"/>')
    d.lignes_de_texte(650, 212, ["négociation directe", "coût : difficile à tracer"], taille=11)

    d.texte(390, 318, "Un agent de plus, c'est un budget de plus : la topologie se justifie par le besoin.",
            taille=12, gras=True, couleur="encre2")
    return d


def echelle_risque() -> Dessin:
    """Séance 1 et 7 : classer les actions, puis placer la frontière d'autonomie."""
    d = Dessin(760, 376, "Échelle de risque des actions et frontière d'autonomie")
    actions = [("Lire les factures", "bon", 60), ("Calculer l'exposition", "bon", 95),
               ("Rédiger un brouillon", "attention", 150), ("Enregistrer une simulation", "serieux", 250),
               ("Envoyer une relance", "critique", 340)]
    # libellés dans leur propre colonne : un texte posé sur un aplat de couleur se lit mal, et la règle
    # d'encre du système interdit de teindre le texte avec la série
    base = 250
    for i, (nom, teinte, longueur) in enumerate(actions):
        y = 76 + i * 54
        d.texte(base - 16, y + 23, nom, taille=12, ancre="end", couleur="encre")
        d.barre(base, y, longueur, 32, teinte)
    d.ajouter('<line x1="470" y1="58" x2="470" y2="340" stroke="var(--critique)" stroke-width="2"'
              ' stroke-dasharray="6 4"/>')
    d.texte(470, 44, "frontière d'autonomie acceptable", taille=12, gras=True, couleur="critique")
    d.texte(360, 362, "automatique", taille=11, couleur="encre2")
    d.texte(600, 362, "accord humain exigé", taille=11, couleur="encre2")
    return d


def cout_par_etapes() -> Dessin:
    """Séance 7 : deux grandeurs, deux graphiques. Jamais deux échelles sur un même axe.

    Les valeurs sont des ordres de grandeur destinés à montrer la forme de la courbe. Elles ne sont
    pas des mesures du dépôt de départ, dont la boucle est déterministe et n'appelle aucun modèle :
    les annoncer comme telles serait faux. L'apprenant mesure les siennes en séance 7.
    """
    d = Dessin(760, 344, "Coût et latence selon le nombre d'étapes, ordres de grandeur")
    series = [("Jetons consommés (milliers)", 40, "s1", [(2, 4), (5, 11), (10, 24), (20, 51)]),
              ("Latence observée (secondes)", 410, "s2", [(2, 3), (5, 8), (10, 17), (20, 36)])]
    for titre, x0, teinte, points in series:
        d.texte(x0 + 150, 42, titre, taille=13, gras=True)
        maximum = max(v for _, v in points)
        base = 268
        for i, (etapes, valeur) in enumerate(points):
            hauteur = (valeur / maximum) * 180
            x = x0 + 24 + i * 72
            d.barre(x, base - hauteur, 44, hauteur, teinte)
            d.texte(x + 22, base - hauteur - 8, str(valeur), taille=11, couleur="encre2")
            d.texte(x + 22, base + 18, f"{etapes} ét.", taille=11, couleur="attenue")
        d.ajouter(f'<line x1="{x0 + 14}" y1="{base}" x2="{x0 + 310}" y2="{base}"'
                  ' stroke="var(--trait)" stroke-width="1.5"/>')
    d.texte(380, 306, "Ordres de grandeur, à mesurer sur votre propre exécution : la figure montre la forme "
                      "de la courbe,", taille=11, couleur="encre2")
    d.texte(380, 322, "pas une facture. Ce qui compte : le coût suit le nombre d'étapes, la qualité non.",
            taille=11, couleur="encre2")
    return d


def patterns_orchestration() -> Dessin:
    """Séance 3 : quatre façons d'enchaîner des étapes, et le signe qui désigne la bonne."""
    d = Dessin(780, 372, "Quatre patterns d'orchestration")
    def bloc(x, y, libelle, teinte="s1", l=96, h=32):
        d.boite(x, y, l, h, teinte=teinte)
        d.texte(x + l / 2, y + 21, libelle, taille=11)

    d.texte(190, 44, "Chaînage", taille=14, gras=True)
    for i, nom in enumerate(("extraire", "calculer", "rédiger")):
        bloc(30 + i * 128, 64, nom, "s3")
        if i:
            d.fleche(14 + i * 128, 80, 26 + i * 128, 80, teinte="s3")
    d.texte(190, 124, "chaque étape consomme la précédente", taille=11, couleur="encre2")

    d.texte(590, 44, "Routage", taille=14, gras=True)
    bloc(434, 64, "classer", "s2")
    for i, nom in enumerate(("litige", "relance")):
        bloc(620, 48 + i * 44, nom, "s2")
        d.fleche(534, 80, 614, 64 + i * 44, teinte="s2")
    d.texte(590, 150, "un seul chemin est emprunté", taille=11, couleur="encre2")

    d.texte(190, 196, "Parallélisation", taille=14, gras=True)
    bloc(30, 216, "segmenter", "s1")
    for i, nom in enumerate(("lot A", "lot B")):
        bloc(158, 200 + i * 44, nom, "s1")
        d.fleche(130, 232, 152, 216 + i * 44, teinte="s1")
    bloc(286, 216, "fusionner", "s1")
    for i in range(2):
        d.fleche(256, 216 + i * 44, 280, 232, teinte="s1")
    d.texte(205, 304, "les lots ne se parlent pas", taille=11, couleur="encre2")

    d.texte(590, 196, "Réflexion", taille=14, gras=True)
    bloc(470, 216, "produire", "s2")
    bloc(626, 216, "critiquer", "s2")
    d.fleche(568, 226, 620, 226, teinte="s2")
    d.ajouter('<path d="M 674 248 q 0 40 -78 40 q -78 0 -78 -40" fill="none" stroke="var(--s2)"'
              ' stroke-width="2" marker-end="url(#pointe-s2)"/>')
    d.texte(590, 304, "une passe de plus, bornée", taille=11, couleur="encre2")

    d.texte(390, 352, "Le pattern se choisit sur la dépendance entre les étapes, pas sur la mode du moment.",
            taille=12, gras=True, couleur="encre2")
    return d


def _couper(texte: str, largeur: int) -> list[str]:
    lignes, courante = [], ""
    for mot in texte.split():
        essai = f"{courante} {mot}".strip()
        if len(essai) > largeur and courante:
            lignes.append(courante)
            courante = mot
        else:
            courante = essai
    if courante:
        lignes.append(courante)
    return lignes
def frise_agentique() -> Dessin:
    """Séance 1 : les cinq âges de l'agentique, et ce que chacun a laissé derrière lui."""
    d = Dessin(900, 420, "De 1966 à aujourd'hui : cinq âges de l'agentique")
    ages = [
        ("1966\u20131985", "Programmes\nsymboliques", ["ELIZA, SHRDLU,", "systèmes experts"],
         "règles écrites à la main", "attenue"),
        ("1986\u20132005", "Agents\nlogiciels", ["agents BDI,", "systèmes multi-agents"],
         "autonomie théorisée", "attenue"),
        ("2006\u20132016", "Apprentissage", ["apprentissage profond,", "renforcement, AlphaGo"],
         "l'agent apprend sa politique", "s3"),
        ("2017\u20132021", "Transformeur", ["attention, GPT,", "prompting"],
         "le langage devient interface", "s3"),
        ("2022\u20132026", "Agents outillés", ["ReAct, tool calling,", "MCP, A2A"],
         "le modèle agit sur le monde", "s1"),
    ]
    for i, (periode, titre, lignes, apport, teinte) in enumerate(ages):
        x = 24 + i * 176
        d.texte(x + 80, 84, periode, taille=12, gras=True, couleur="encre2")
        d.boite(x, 96, 160, 108, teinte=teinte)
        for j, ligne in enumerate(titre.split("\n")):
            d.texte(x + 80, 124 + j * 18, ligne, taille=14, gras=True)
        d.lignes_de_texte(x + 80, 168, lignes, taille=11)
        d.lignes_de_texte(x + 80, 232, _couper(apport, 20), taille=11, couleur="encre2")
        if i < len(ages) - 1:
            d.fleche(x + 160, 150, x + 172, 150, teinte="attenue")
    d.texte(450, 40, "Rien n'a commencé en 2022 : chaque âge a légué une idée qui sert encore.",
            taille=14, gras=True)
    d.texte(450, 62, "La boucle percevoir, décider, agir date des agents logiciels ; le modèle n'a fait "
                     "que remplacer les règles.", taille=12, couleur="encre2")
    d.boite(140, 296, 620, 68, teinte="s2", tirets=True)
    d.texte(450, 320, "Ce qui est vraiment nouveau depuis 2022", taille=13, gras=True, couleur="s2")
    d.texte(450, 342, "un seul modèle généraliste sait choisir l'outil, lire le résultat et "
                      "recommencer, sans code spécifique.", taille=11, couleur="encre2")
    d.texte(450, 392, "Les échecs de chaque âge sont instructifs : ils reviennent dès qu'on retire "
                      "une borne.", taille=12, gras=True, couleur="encre2")
    return d


def anatomie_llm() -> Dessin:
    """Séance 2 : du texte à la distribution de probabilité, et ce qui se règle à chaque étape."""
    d = Dessin(880, 400, "Ce qu'un modèle de langage fait d'un texte")
    etapes = [
        ("Découpage", ["le texte devient", "des jetons"], "s3", "un mot rare coûte plusieurs jetons"),
        ("Plongement", ["chaque jeton devient", "un vecteur"], "s3", "le sens devient une position"),
        ("Attention", ["chaque jeton regarde", "les précédents"], "s1", "coût quadratique du contexte"),
        ("Distribution", ["un score par jeton", "du vocabulaire"], "s1", "le modèle ne choisit pas encore"),
        ("Échantillonnage", ["un jeton est tiré,", "puis tout recommence"], "s2",
         "température et top-p agissent ici"),
    ]
    for i, (nom, lignes, teinte, note) in enumerate(etapes):
        x = 20 + i * 172
        d.boite(x, 110, 158, 92, teinte=teinte)
        d.texte(x + 79, 138, nom, taille=14, gras=True)
        d.lignes_de_texte(x + 79, 160, lignes, taille=11)
        d.lignes_de_texte(x + 79, 224, _couper(note, 24), taille=11, couleur="encre2")
        if i < len(etapes) - 1:
            d.fleche(x + 158, 156, x + 168, 156, teinte=teinte)
    d.ajouter('<path d="M 790 202 L 790 274 L 99 274 L 99 206" fill="none" stroke="var(--s2)"'
              ' stroke-width="2" marker-end="url(#pointe-s2)"/>')
    d.texte(445, 292, "un jeton à la fois : la réponse entière est cette boucle répétée",
            taille=12, couleur="s2")
    d.texte(440, 40, "Un modèle prédit le jeton suivant. Tout le reste en découle.", taille=14, gras=True)
    d.texte(440, 62, "Il ne consulte rien, ne vérifie rien et ne sait pas qu'il ignore : d'où les outils.",
            taille=12, couleur="encre2")
    d.boite(120, 316, 640, 64, teinte="critique", tirets=True)
    d.texte(440, 340, "Conséquence pour un agent", taille=12, gras=True, couleur="critique")
    d.texte(440, 362, "la fenêtre de contexte est une mémoire de travail payante, pas un disque dur.",
            taille=11, couleur="encre2")
    return d


def familles_modeles() -> Dessin:
    """Séance 2 : propriétaire, poids ouverts, pleinement ouvert, et ce que chacun vous laisse faire."""
    d = Dessin(860, 380, "Trois familles de modèles, et ce que vous recevez vraiment")
    familles = [
        ("Propriétaire", "s2", ["une API et une facture"],
         ["Pas de poids, pas de données", "Mise à jour subie", "Données envoyées au fournisseur"],
         "le meilleur niveau, le moins de maîtrise"),
        ("Poids ouverts", "s1", ["les poids, pas la recette"],
         ["Exécution locale possible", "Réglage fin autorisé", "Licence parfois restrictive"],
         "le compromis le plus fréquent"),
        ("Pleinement ouvert", "s3", ["poids, données et code"],
         ["Reproductible et auditable", "Souveraineté réelle", "Niveau souvent en retrait"],
         "le seul vérifiable de bout en bout"),
    ]
    for i, (nom, teinte, recu, points, note) in enumerate(familles):
        x = 24 + i * 278
        d.boite(x, 86, 262, 196, teinte=teinte)
        d.texte(x + 131, 116, nom, taille=16, gras=True)
        d.texte(x + 131, 140, recu[0], taille=12, couleur="encre2")
        for j, point in enumerate(points):
            d.texte(x + 131, 172 + j * 24, point, taille=11, couleur="encre2")
        d.lignes_de_texte(x + 131, 306, _couper(note, 30), taille=12, couleur=teinte)
    d.texte(430, 40, "« Open source » recouvre trois réalités très différentes.", taille=14, gras=True)
    d.texte(430, 62, "La question utile n'est pas le nom de la licence, mais ce que vous pouvez "
                     "exécuter, vérifier et garder.", taille=12, couleur="encre2")
    d.texte(430, 358, "Pour un agent : la famille choisie décide de l'endroit où vont vos données "
                      "et du coût par exécution.", taille=12, gras=True, couleur="encre2")
    return d


def anatomie_prompt() -> Dessin:
    """Séance 3 : les couches d'un prompt d'agent, et la frontière entre consigne et donnée."""
    d = Dessin(820, 440, "Les couches d'un prompt d'agent")
    couches = [
        ("Rôle et mission", "ce que l'agent est et ce qu'il doit obtenir", "s1"),
        ("Contraintes dures", "ce qui est interdit, en toutes lettres", "s1"),
        ("Outils disponibles", "nom, usage, arguments, effet de bord", "s3"),
        ("Format de sortie", "la forme exacte attendue, montrée", "s3"),
        ("Exemples", "deux cas, dont un cas limite", "s3"),
    ]
    for i, (nom, detail, teinte) in enumerate(couches):
        y = 92 + i * 52
        d.boite(140, y, 540, 44, teinte=teinte)
        d.texte(170, y + 27, nom, taille=13, gras=True, ancre="start")
        d.texte(660, y + 27, detail, taille=11, ancre="end", couleur="encre2")
    d.boite(140, 360, 540, 56, teinte="critique", tirets=True)
    d.texte(170, 382, "Données lues par l'agent", taille=13, gras=True, ancre="start", couleur="critique")
    d.texte(170, 402, "factures, documents, résultats d'outils : citées, jamais fusionnées avec les consignes",
            taille=11, ancre="start", couleur="encre2")
    d.fleche(410, 352, 410, 358, teinte="critique")
    d.texte(410, 40, "Un prompt d'agent s'écrit en couches, de la plus stable à la plus volatile.",
            taille=14, gras=True)
    d.texte(410, 62, "Les quatre premières changent rarement ; la dernière change à chaque exécution.",
            taille=12, couleur="encre2")
    d.texte(410, 434, "Une consigne et une donnée qui se ressemblent à l'écran se confondront "
                      "aussi dans le modèle.", taille=12, gras=True, couleur="encre2")
    return d
def jetons_decoupage() -> Dessin:
    """Séance 2 : une même phrase découpée en jetons, et ce que le découpage coûte."""
    d = Dessin(860, 340, "Le découpage en jetons, et son coût")
    exemples = [
        ("Anglais", ["The", " invoice", " is", " late"], "4 jetons", "s3"),
        ("Français", ["La", " fact", "ure", " est", " en", " ret", "ard"], "7 jetons", "s1"),
        ("Identifiant", ["FAC", "-", "0", "11"], "4 jetons pour 7 signes", "s2"),
    ]
    for i, (langue, morceaux, total, teinte) in enumerate(exemples):
        y = 96 + i * 76
        d.texte(96, y + 28, langue, taille=13, gras=True, ancre="end")
        x = 116
        for morceau in morceaux:
            largeur = max(42, 13 + len(morceau) * 11)
            d.boite(x, y, largeur, 44, teinte=teinte)
            d.texte(x + largeur / 2, y + 28, morceau.strip() or "␣", taille=12)
            x += largeur + 8
        d.texte(x + 12, y + 28, total, taille=12, ancre="start", couleur="encre2")
    d.texte(430, 42, "Un jeton n'est ni un mot ni une lettre : c'est un fragment fréquent.",
            taille=14, gras=True)
    d.texte(430, 64, "La même phrase coûte plus cher en français, et un identifiant coûte "
                     "plus cher qu'un mot courant.", taille=12, couleur="encre2")
    d.boite(150, 258, 560, 60, teinte="critique", tirets=True)
    d.texte(430, 282, "Ce que le modèle ne voit pas", taille=12, gras=True, couleur="critique")
    d.texte(430, 303, "les lettres à l'intérieur d'un jeton : d'où les erreurs de comptage et "
                      "de recopie d'identifiants.", taille=11, couleur="encre2")
    return d


def temperature_echantillonnage() -> Dessin:
    """Séance 2 : la même distribution, échantillonnée froid puis chaud."""
    d = Dessin(820, 360, "La température agit sur le tirage, pas sur le savoir du modèle")
    colonnes = [("Température 0", 60, "s1", [96, 10, 6, 4, 2], "le jeton le plus probable gagne presque toujours"),
                ("Température 1", 450, "s2", [46, 24, 16, 9, 5], "les jetons rares deviennent atteignables")]
    etiquettes = ["lister", "calculer", "rédiger", "demander", "arrêter"]
    for titre, x0, teinte, hauteurs, note in colonnes:
        d.texte(x0 + 155, 96, titre, taille=14, gras=True)
        base = 260
        for i, h in enumerate(hauteurs):
            hauteur = h * 1.3
            x = x0 + i * 62
            d.barre(x, base - hauteur, 44, hauteur, teinte)
            d.texte(x + 22, base + 18, etiquettes[i], taille=10, couleur="encre2")
            d.texte(x + 22, base - hauteur - 8, f"{h} %", taille=10, couleur="encre2")
        d.ajouter(f'<line x1="{x0 - 10}" y1="{base}" x2="{x0 + 300}" y2="{base}"'
                  ' stroke="var(--trait)" stroke-width="1.5"/>')
        d.lignes_de_texte(x0 + 145, 302, _couper(note, 34), taille=11, couleur="encre2")
    d.texte(410, 42, "Le modèle produit des scores ; la température décide de ce qu'on en fait.",
            taille=14, gras=True)
    d.texte(410, 64, "Pour décider d'un outil, on veut la colonne de gauche. Pour rédiger à un "
                     "humain, celle de droite.", taille=12, couleur="encre2")
    d.texte(410, 348, "Température 0 ne veut pas dire reproductible : le calcul flottant et les "
                      "mises à jour font varier le résultat.", taille=11, gras=True, couleur="encre2")
    return d


def trois_temps_entrainement() -> Dessin:
    """Séance 2 : pré-entraînement, instructions, alignement, et ce que chacun vous laisse."""
    d = Dessin(860, 340, "Les trois temps d'un entraînement")
    temps = [
        ("Pré-entraînement", "s3", ["prédire le jeton suivant", "sur un très grand corpus"],
         "donne la langue et la culture, fixe la date de coupure"),
        ("Instructions", "s1", ["obéir plutôt que", "continuer le texte"],
         "donne la variante instruite, la seule utile pour un agent"),
        ("Alignement", "s2", ["préférences humaines", "ou règles écrites"],
         "donne la prudence, et explique une partie des refus"),
    ]
    for i, (nom, teinte, lignes, apport) in enumerate(temps):
        x = 30 + i * 272
        d.boite(x, 100, 252, 104, teinte=teinte)
        d.texte(x + 126, 132, nom, taille=15, gras=True)
        d.lignes_de_texte(x + 126, 156, lignes, taille=11)
        d.lignes_de_texte(x + 126, 230, _couper(apport, 36), taille=11, couleur="encre2")
        if i < 2:
            d.fleche(x + 252, 152, x + 266, 152, teinte="attenue")
    d.texte(430, 42, "Trois étapes que vous ne referez pas, et dont vous héritez.", taille=14, gras=True)
    d.texte(430, 64, "Deux opérations légères complètent le tableau : la distillation vers un petit "
                     "modèle, et la quantification.", taille=12, couleur="encre2")
    d.boite(180, 276, 500, 52, teinte="trait", tirets=True)
    d.texte(430, 298, "Le réglage fin n'est presque jamais la première réponse", taille=12, gras=True)
    d.texte(430, 317, "un meilleur prompt, de meilleurs outils et de meilleures données coûtent "
                      "moins et se corrigent plus vite.", taille=11, couleur="encre2")
    return d


def memoire_modeles_locaux() -> Dessin:
    """Séance 2 : mémoire nécessaire selon la taille du modèle, en quantification 4 bits."""
    d = Dessin(800, 360, "Mémoire nécessaire pour exécuter un modèle en local, en 4 bits")
    mesures = [("3 à 4 Md", 2.5, "extraction simple"), ("7 à 8 Md", 5.5, "agent simple"),
               ("12 à 14 Md", 9, "point d'équilibre"), ("30 à 34 Md", 20, "machine équipée"),
               ("70 Md", 42, "serveur ou carte pro")]
    base, echelle = 288, 4.6
    for i, (nom, giga, usage) in enumerate(mesures):
        x = 90 + i * 136
        hauteur = giga * echelle
        teinte = "s3" if giga <= 10 else ("s1" if giga <= 22 else "s2")
        d.barre(x, base - hauteur, 78, hauteur, teinte)
        d.texte(x + 39, base - hauteur - 10, f"{giga:g} Go", taille=12, gras=True)
        d.texte(x + 39, base + 20, nom, taille=12)
        d.lignes_de_texte(x + 39, base + 40, _couper(usage, 16), taille=10, couleur="encre2")
    d.ajouter(f'<line x1="60" y1="{base}" x2="740" y2="{base}" stroke="var(--trait)" stroke-width="1.5"/>')
    d.texte(400, 42, "La mémoire disponible décide du modèle, pas l'inverse.", taille=14, gras=True)
    d.texte(400, 64, "Ordres de grandeur en quantification agressive, à vérifier sur votre machine.",
            taille=12, couleur="encre2")
    return d
def description_outil() -> Dessin:
    """Séance 3 : la même fonction décrite deux fois, et ce que le modèle en fait."""
    d = Dessin(860, 400, "Deux descriptions du même outil, deux comportements")
    colonnes = [
        ("Description pauvre", 30, "critique",
         ['"name": "lister"', '"description": "liste les factures"',
          '"age_min_jours": {"type": "integer"}'],
         ["Appelé à contretemps", "Arguments hors bornes acceptés",
          "Confondu avec l'outil de calcul"]),
        ("Description utile", 450, "s3",
         ['"name": "lister_factures_impayees"',
          '"description": "Liste les factures dont le retard',
          'atteint age_min_jours. Exclut les litiges."',
          '"age_min_jours": {"type":"integer","minimum":0,',
          '"maximum":365}'],
         ["Appelé au bon moment", "Arguments refusés avant exécution",
          "Jamais confondu avec un autre outil"]),
    ]
    for titre, x, teinte, lignes, effets in colonnes:
        d.texte(x + 190, 96, titre, taille=15, gras=True, couleur=teinte)
        d.boite(x, 110, 380, 128, teinte=teinte)
        for i, ligne in enumerate(lignes):
            d.texte(x + 16, 136 + i * 21, ligne, taille=11, ancre="start", couleur="encre2")
        for i, effet in enumerate(effets):
            d.texte(x + 190, 270 + i * 24, effet, taille=12)
    d.texte(430, 42, "Le modèle ne lit pas votre code : il lit la description de l'outil.",
            taille=14, gras=True)
    d.texte(430, 64, "C'est le texte le plus rentable de tout votre projet, et le plus souvent bâclé.",
            taille=12, couleur="encre2")
    d.texte(430, 372, "Une description dit quand utiliser l'outil, quand ne pas l'utiliser, "
                      "et ce qu'il renvoie.", taille=12, gras=True, couleur="encre2")
    return d


def techniques_prompting() -> Dessin:
    """Séance 3 : ce qui agit vraiment, et ce qui relève du folklore."""
    d = Dessin(860, 420, "Ce qui agit sur la qualité d'un prompt, et ce qui n'agit pas")
    utiles = [("Objectif précis et vérifiable", "toujours"),
              ("Format de sortie montré, pas décrit", "toujours"),
              ("Deux exemples, dont un cas limite", "tâches ambiguës"),
              ("Découper en plusieurs appels", "tâche à étapes"),
              ("Demander de citer la source", "réponses sur documents")]
    inutiles = [("« Tu es un expert mondial »", "aucun effet mesurable"),
                ("Menaces ou récompenses", "aucun effet mesurable"),
                ("« Sois précis » sans critère", "trop vague pour agir"),
                ("Prompt de quatre pages", "dilue et coûte à chaque tour"),
                ("Raisonnement imposé pas à pas", "déjà interne aux modèles récents")]
    for i, (texte, quand) in enumerate(utiles):
        y = 110 + i * 54
        d.boite(30, y, 380, 44, teinte="s3")
        d.texte(48, y + 20, texte, taille=12, gras=True, ancre="start")
        d.texte(48, y + 36, quand, taille=10, ancre="start", couleur="encre2")
    for i, (texte, quand) in enumerate(inutiles):
        y = 110 + i * 54
        d.boite(450, y, 380, 44, teinte="attenue", tirets=True)
        d.texte(468, y + 20, texte, taille=12, ancre="start", couleur="encre2")
        d.texte(468, y + 36, quand, taille=10, ancre="start", couleur="attenue")
    d.texte(220, 90, "Ce qui agit", taille=14, gras=True, couleur="s3")
    d.texte(640, 90, "Ce qui relève du folklore", taille=14, gras=True, couleur="attenue")
    d.texte(430, 42, "Un prompt se juge sur un jeu de cas, pas sur une impression.", taille=14, gras=True)
    d.texte(430, 64, "Toute recette qui ne survit pas à vingt cas mesurés est une superstition.",
            taille=12, couleur="encre2")
    d.texte(430, 404, "Changez une chose à la fois, et remesurez : c'est la seule méthode qui "
                      "progresse.", taille=12, gras=True, couleur="encre2")
    return d


def frontiere_donnee_consigne() -> Dessin:
    """Séance 3 : où placer la donnée pour qu'elle ne devienne jamais une consigne."""
    d = Dessin(820, 380, "La frontière entre la consigne et la donnée")
    d.boite(90, 100, 300, 180, teinte="s1")
    d.texte(240, 128, "Zone des consignes", taille=14, gras=True, couleur="s1")
    for i, ligne in enumerate(["message système", "règles dures", "outils et formats",
                               "écrit par vous", "stable entre deux exécutions"]):
        d.texte(240, 158 + i * 24, ligne, taille=11, couleur="encre2")
    d.boite(430, 100, 300, 180, teinte="critique", tirets=True)
    d.texte(580, 128, "Zone des données", taille=14, gras=True, couleur="critique")
    for i, ligne in enumerate(["notes de factures", "documents lus", "résultats d'outils",
                               "écrit par n'importe qui", "change à chaque exécution"]):
        d.texte(580, 158 + i * 24, ligne, taille=11, couleur="encre2")
    d.ajouter('<line x1="410" y1="92" x2="410" y2="296" stroke="var(--s2)" stroke-width="3"'
              ' stroke-dasharray="7 5"/>')
    d.texte(410, 318, "une donnée ne traverse jamais cette ligne", taille=12, gras=True, couleur="s2")
    d.texte(410, 42, "Tout ce qui vient du monde extérieur est une donnée, même si c'est écrit "
                     "à l'impératif.", taille=14, gras=True)
    d.texte(410, 64, "Citez les données dans un bloc nommé, annoncez qu'elles ne sont pas fiables, "
                     "et n'y obéissez jamais.", taille=12, couleur="encre2")
    d.texte(410, 362, "Si vous concaténez les deux zones dans une seule chaîne, la frontière "
                      "n'existe plus.", taille=12, gras=True, couleur="critique")
    return d
def trois_memoires() -> Dessin:
    """Séance 9 : mémoire de travail, mémoire des faits, mémoire des connaissances."""
    d = Dessin(880, 360, "Les trois mémoires d'un agent, et ce qui les distingue")
    memoires = [
        ("Mémoire de travail", "s1", ["l'historique du tour en cours"],
         ["Vit le temps d'une exécution", "Payée à chaque appel", "Bornée par un résumé"],
         "le contexte"),
        ("Mémoire des faits", "s3", ["ce que l'agent a déjà fait"],
         ["Survit au programme", "Relue à la reprise", "Clé d'idempotence"],
         "le fichier d'état"),
        ("Mémoire des connaissances", "s2", ["ce que l'organisation sait"],
         ["Indépendante des exécutions", "Interrogée par un outil", "Citée dans la réponse"],
         "l'index documentaire"),
    ]
    for i, (nom, teinte, sous_titre, points, support) in enumerate(memoires):
        x = 24 + i * 286
        d.boite(x, 92, 268, 180, teinte=teinte)
        d.texte(x + 134, 120, nom, taille=14, gras=True)
        d.texte(x + 134, 142, sous_titre[0], taille=11, couleur="encre2")
        for j, point in enumerate(points):
            d.texte(x + 134, 174 + j * 26, point, taille=11, couleur="encre2")
        d.texte(x + 134, 292, support, taille=12, gras=True, couleur=teinte)
    d.texte(440, 42, "Confondre ces trois mémoires est la cause la plus fréquente de contextes "
                     "obèses.", taille=14, gras=True)
    d.texte(440, 64, "Chacune a sa durée de vie, son support et son coût.", taille=12, couleur="encre2")
    d.texte(440, 336, "Règle : ce qui peut être relu par un outil ne reste pas dans le contexte.",
            taille=12, gras=True, couleur="encre2")
    return d


def pipeline_rag() -> Dessin:
    """Séance 9 : de la question à la réponse citée, avec l'endroit où chaque réglage agit."""
    d = Dessin(900, 380, "Le trajet d'une question dans une recherche documentaire")
    etapes = [("Question", "s1", "reformulée si besoin"), ("Recherche", "s3", "lexicale et vectorielle"),
              ("Fusion", "s3", "les deux listes réunies"), ("Sélection", "s3", "les k meilleurs passages"),
              ("Réponse", "s2", "citations obligatoires")]
    for i, (nom, teinte, note) in enumerate(etapes):
        x = 22 + i * 176
        d.boite(x, 110, 158, 76, teinte=teinte)
        d.texte(x + 79, 140, nom, taille=14, gras=True)
        d.texte(x + 79, 164, note, taille=10, couleur="encre2")
        if i < len(etapes) - 1:
            d.fleche(x + 158, 148, x + 168, 148, teinte=teinte)
    d.boite(22, 228, 334, 88, teinte="trait", tirets=True)
    d.texte(189, 252, "Préparé à l'avance, une fois", taille=12, gras=True)
    d.lignes_de_texte(189, 274, ["découpage des documents en passages",
                                 "index lexical et vecteurs calculés"], taille=11)
    d.boite(546, 228, 334, 88, teinte="critique", tirets=True)
    d.texte(713, 252, "Ce qui se vérifie à chaque réponse", taille=12, gras=True, couleur="critique")
    d.lignes_de_texte(713, 274, ["chaque affirmation porte sa source",
                                 "un passage non cité ne compte pas"], taille=11)
    d.texte(450, 42, "Une recherche documentaire n'est pas un agent : c'est un outil que l'agent appelle.",
            taille=14, gras=True)
    d.texte(450, 64, "Elle répond à une question sur vos documents, et elle cite ses sources.",
            taille=12, couleur="encre2")
    d.texte(450, 352, "Si la réponse ne peut pas être citée, l'agent doit dire qu'il ne sait pas.",
            taille=12, gras=True, couleur="encre2")
    return d


def decoupage_documents() -> Dessin:
    """Séance 9 : trois découpages du même document, et ce que chacun retrouve."""
    d = Dessin(880, 380, "Trois découpages du même document, trois qualités de réponse")
    cas = [
        ("Trop petit", "critique", [26, 26, 26, 26, 26, 26],
         "la phrase trouvée a perdu son contexte"),
        ("Par section", "s3", [58, 58, 58],
         "le passage se suffit à lui-même"),
        ("Document entier", "attenue", [184],
         "le passage utile se noie dans le reste"),
    ]
    for i, (nom, teinte, blocs, note) in enumerate(cas):
        x = 40 + i * 290
        d.texte(x + 110, 100, nom, taille=14, gras=True, couleur=teinte)
        y = 118
        for hauteur in blocs:
            d.boite(x, y, 220, hauteur - 6, teinte=teinte)
            y += hauteur
        d.lignes_de_texte(x + 110, 324, _couper(note, 28), taille=11, couleur="encre2")
    d.texte(440, 42, "Le découpage décide de ce que la recherche peut retrouver.", taille=14, gras=True)
    d.texte(440, 64, "Un passage doit être compréhensible seul, et porter le titre de sa section.",
            taille=12, couleur="encre2")
    d.texte(440, 370, "Règle de départ : une section, un passage ; puis mesurez avant de régler.",
            taille=12, gras=True, couleur="encre2")
    return d
def graphe_langgraph() -> Dessin:
    """Séance 10 : le même fil rouge, écrit comme un graphe d'états."""
    d = Dessin(880, 420, "Le fil rouge écrit comme un graphe d'états")
    d.boite(360, 96, 160, 54, teinte="s1")
    d.texte(440, 128, "decider", taille=14, gras=True)
    d.boite(170, 214, 160, 54, teinte="s3")
    d.texte(250, 246, "agir", taille=14, gras=True)
    d.boite(560, 214, 180, 54, teinte="s2", tirets=True)
    d.texte(650, 240, "valider", taille=14, gras=True)
    d.texte(650, 258, "pause humaine", taille=10, couleur="encre2")
    d.boite(370, 326, 140, 48, teinte="attenue")
    d.texte(440, 356, "fin", taille=13, gras=True)
    d.fleche(440, 72, 440, 92, teinte="attenue")
    d.texte(440, 64, "entrée", taille=11, couleur="encre2")
    d.fleche(380, 150, 280, 210, teinte="s3")
    d.texte(290, 186, "appel d'outil demandé", taille=10, ancre="end", couleur="encre2")
    d.fleche(510, 150, 620, 210, teinte="s2")
    d.texte(600, 186, "écriture demandée", taille=10, ancre="start", couleur="encre2")
    d.fleche(250, 268, 390, 330, teinte="attenue")
    d.fleche(650, 268, 500, 330, teinte="attenue")
    d.ajouter('<path d="M 250 214 L 250 170 L 356 170" fill="none" stroke="var(--s3)"'
              ' stroke-width="2" marker-end="url(#pointe-s3)"/>')
    d.texte(250, 160, "observation renvoyée", taille=10, couleur="encre2")
    d.boite(40, 326, 240, 60, teinte="trait", tirets=True)
    d.texte(160, 350, "Point de sauvegarde", taille=12, gras=True)
    d.texte(160, 370, "écrit après chaque nœud", taille=10, couleur="encre2")
    d.texte(440, 42, "Les nœuds sont vos fonctions ; les arêtes sont vos conditions d'enchaînement.",
            taille=14, gras=True)
    d.texte(440, 406, "Le cadre fournit la reprise et la pause humaine ; la logique métier reste "
                      "la vôtre.", taille=12, gras=True, couleur="encre2")
    return d
def cinq_implementations() -> Dessin:
    """Séance 11 : le même fil rouge écrit cinq fois, et ce que chaque écriture met en avant."""
    d = Dessin(920, 420, "Le même fil rouge, écrit cinq fois")
    cadres = [
        ("À la main", "s1", "une boucle", ["tout visible", "tout à écrire"]),
        ("LangGraph", "s3", "un graphe", ["état et reprise", "vocabulaire à apprendre"]),
        ("CrewAI", "s2", "une équipe", ["rôles explicites", "contrôle moins fin"]),
        ("PydanticAI", "s3", "des types", ["sorties garanties", "jeune, API mouvante"]),
        ("GenAI", "s1", "le SDK du modèle", ["au plus près du modèle", "lié à un fournisseur"]),
    ]
    for i, (nom, teinte, forme, points) in enumerate(cadres):
        x = 22 + i * 178
        d.boite(x, 104, 160, 150, teinte=teinte)
        d.texte(x + 80, 134, nom, taille=15, gras=True)
        d.texte(x + 80, 158, forme, taille=11, couleur="encre2")
        for j, point in enumerate(points):
            d.texte(x + 80, 192 + j * 26, point, taille=11, couleur="encre2")
        d.texte(x + 80, 282, f"{i + 1}", taille=12, gras=True, couleur=teinte)
    d.texte(460, 42, "Cinq écritures, un seul comportement attendu.", taille=14, gras=True)
    d.texte(460, 64, "Les mêmes douze critères d'acceptation passent sur les cinq, ou la comparaison "
                     "ne vaut rien.", taille=12, couleur="encre2")
    d.boite(120, 310, 680, 72, teinte="trait", tirets=True)
    d.texte(460, 334, "Ce qui ne change jamais, quel que soit le cadre", taille=13, gras=True)
    d.texte(460, 356, "la liste blanche, les contrats d'arguments, la trace filtrée, le budget "
                      "et la validation humaine.", taille=11, couleur="encre2")
    d.texte(460, 406, "Un cadre se choisit sur ce qu'il vous économise, jamais sur sa popularité.",
            taille=12, gras=True, couleur="encre2")
    return d
def pipeline_deploiement() -> Dessin:
    """Séance 15 : du commit à la production, les étapes et ce qui bloque à chacune."""
    d = Dessin(940, 420, "Du commit à la production, sans geste manuel")
    etapes = [
        ("commit", "s1", "branche de travail"),
        ("tests", "s3", "unitaires et critères"),
        ("image", "s2", "conteneur épinglé"),
        ("recette", "s3", "scénario complet"),
        ("production", "s1", "après approbation"),
    ]
    for i, (nom, teinte, sous) in enumerate(etapes):
        x = 28 + i * 180
        d.boite(x, 118, 150, 84, teinte=teinte)
        d.texte(x + 75, 150, nom, taille=15, gras=True)
        d.texte(x + 75, 176, sous, taille=10, couleur="encre2")
        if i < 4:
            d.fleche(x + 150, 160, x + 178, 160, teinte="attenue")
    d.texte(470, 42, "Chaque étape peut refuser de passer la suivante.", taille=15, gras=True)
    d.texte(470, 66, "Un déploiement manuel est un déploiement que personne ne sait rejouer.",
            taille=12, couleur="encre2")
    d.boite(28, 236, 330, 96, teinte="trait", tirets=True)
    d.texte(193, 262, "Ce qui bloque le passage", taille=13, gras=True)
    d.texte(193, 286, "un test rouge, un critère d'acceptation", taille=11, couleur="encre2")
    d.texte(193, 306, "échoué, un secret absent, une image", taille=11, couleur="encre2")
    d.texte(193, 326, "non reproductible.", taille=11, couleur="encre2")
    d.boite(392, 236, 330, 96, teinte="trait", tirets=True)
    d.texte(557, 262, "Ce qui ne voyage jamais dans l'image", taille=13, gras=True)
    d.texte(557, 286, "les clés d'API, la base de données,", taille=11, couleur="encre2")
    d.texte(557, 306, "les traces, le fichier d'état : tout cela", taille=11, couleur="encre2")
    d.texte(557, 326, "vient de l'extérieur, au démarrage.", taille=11, couleur="encre2")
    d.boite(756, 236, 156, 96, teinte="s2")
    d.texte(834, 262, "Retour arrière", taille=13, gras=True)
    d.texte(834, 288, "l'image précédente", taille=11, couleur="encre2")
    d.texte(834, 308, "reste déployable", taille=11, couleur="encre2")
    d.texte(834, 328, "en une commande.", taille=11, couleur="encre2")
    d.texte(470, 392, "Un agent se déploie comme un service : versionné, reproductible, réversible.",
            taille=12, gras=True, couleur="encre2")
    return d


def exploitation_agent() -> Dessin:
    """Séance 16 : ce qu'on surveille une fois l'agent en service."""
    d = Dessin(900, 440, "Ce qu'on surveille, et ce qu'on fait quand ça sonne")
    familles = [
        ("Santé", "s1", ["le service répond", "le modèle répond", "les outils répondent"]),
        ("Qualité", "s3", ["taux de réussite", "litiges relancés : zéro", "brouillons rejetés"]),
        ("Coût", "s2", ["jetons par exécution", "francs CFA par jour", "tours par exécution"]),
        ("Humain", "s3", ["délai de validation", "file d'attente", "taux d'approbation"]),
    ]
    for i, (nom, teinte, lignes) in enumerate(familles):
        x = 30 + i * 215
        d.boite(x, 96, 190, 146, teinte=teinte)
        d.texte(x + 95, 126, nom, taille=15, gras=True)
        for j, ligne in enumerate(lignes):
            d.texte(x + 95, 160 + j * 26, ligne, taille=11, couleur="encre2")
    d.texte(450, 42, "Quatre familles de mesures, et une seule question par famille.",
            taille=15, gras=True)
    d.texte(450, 66, "Une alerte qui ne dit pas quoi faire finit par être ignorée.",
            taille=12, couleur="encre2")
    d.boite(90, 282, 720, 108, teinte="trait", tirets=True)
    d.texte(450, 308, "Quand une alerte sonne, dans cet ordre", taille=13, gras=True)
    d.texte(450, 332, "1. arrêter la casse : couper l'agent ou revenir à l'image précédente.", taille=11, couleur="encre2")
    d.texte(450, 354, "2. comprendre : relire la trace de l'exécution fautive, pas les suppositions.", taille=11, couleur="encre2")
    d.texte(450, 376, "3. empêcher le retour : un test qui aurait échoué avant l'incident.", taille=11, couleur="encre2")
    d.texte(450, 424, "L'incident se termine par un test ajouté, jamais par une explication seule.",
            taille=12, gras=True, couleur="encre2")
    return d
def port_et_adaptateurs() -> Dessin:
    """Séance 17 : un port unique, plusieurs adaptateurs, un seul métier."""
    d = Dessin(940, 460, "Un port, plusieurs systèmes, un seul métier")
    d.boite(360, 86, 220, 64, teinte="s1")
    d.texte(470, 112, "Votre domaine", taille=15, gras=True)
    d.texte(470, 134, "règles et décisions", taille=10, couleur="encre2")
    d.boite(330, 184, 280, 60, teinte="s3", tirets=True)
    d.texte(470, 208, "PorteSI", taille=15, gras=True)
    d.texte(470, 230, "factures, paiements, note interne", taille=10, couleur="encre2")
    d.fleche(470, 150, 470, 180, teinte="attenue")
    adaptateurs = [
        ("Odoo", "JSON-RPC", "s2"),
        ("Dolibarr", "REST + clé", "s2"),
        ("ERPNext", "REST + token", "s2"),
        ("Fichier", "CSV de secours", "attenue"),
    ]
    for i, (nom, protocole, teinte) in enumerate(adaptateurs):
        x = 36 + i * 228
        d.boite(x, 300, 200, 76, teinte=teinte)
        d.texte(x + 100, 328, nom, taille=14, gras=True)
        d.texte(x + 100, 352, protocole, taille=10, couleur="encre2")
        d.fleche(470, 244, x + 100, 296, teinte="attenue")
    d.texte(470, 44, "Le domaine ne connaît aucun ERP. Il connaît un port.", taille=15, gras=True)
    d.texte(470, 66, "Changer d'ERP devient un fichier à écrire, jamais une refonte.",
            taille=12, couleur="encre2")
    d.texte(470, 420, "Lecture seule par défaut. L'écriture est une note interne, après validation humaine.",
            taille=12, gras=True, couleur="encre2")
    d.texte(470, 446, "Les identifiants viennent du gestionnaire de secrets, jamais du dépôt.",
            taille=11, couleur="encre2")
    return d


def ecosysteme_ouvert() -> Dessin:
    """Séance 17 : ce que chaque brique open source apporte autour de l'agent."""
    d = Dessin(920, 440, "Ce qui entoure l'agent, et ce que chaque brique apporte")
    groupes = [
        ("Données métier", "s1", ["Odoo", "Dolibarr", "ERPNext"], "d'où viennent les factures"),
        ("Documents", "s3", ["Nextcloud"], "les justificatifs, par WebDAV"),
        ("Identité", "s2", ["Keycloak"], "qui a validé, de manière opposable"),
        ("Pilotage", "s3", ["Metabase", "n8n", "Grafana"], "mesurer, déclencher, surveiller"),
    ]
    for i, (nom, teinte, briques, role) in enumerate(groupes):
        x = 26 + i * 222
        d.boite(x, 104, 196, 180, teinte=teinte)
        d.texte(x + 98, 134, nom, taille=14, gras=True)
        for j, brique in enumerate(briques):
            d.texte(x + 98, 166 + j * 26, brique, taille=12, couleur="encre2")
        d.texte(x + 98, 262, role, taille=10, couleur="encre2")
    d.texte(460, 44, "Un agent utile vit dans un système d'information, pas tout seul.",
            taille=15, gras=True)
    d.texte(460, 68, "Chaque brique ajoute une dépendance : on ne l'ajoute que contre un besoin nommé.",
            taille=12, couleur="encre2")
    d.boite(120, 322, 680, 76, teinte="trait", tirets=True)
    d.texte(460, 348, "La question à poser avant chaque branchement", taille=13, gras=True)
    d.texte(460, 372, "que se passe-t-il quand ce service est indisponible, lent, ou renvoie faux ?",
            taille=11, couleur="encre2")
    d.texte(460, 426, "Pas de réponse écrite à cette question : pas de branchement.",
            taille=12, gras=True, couleur="encre2")
    return d
def famille_ia() -> Dessin:
    """Séance 2 : les quatre niveaux emboîtés, et les deux familles de modèles."""
    d = Dessin(920, 460, "Quatre niveaux emboites, et deux questions")
    niveaux = [
        ("Intelligence artificielle", "automatiser une tache qui demande de l'intelligence, depuis 1956"),
        ("Apprentissage automatique", "le systeme deduit ses regles des donnees"),
        ("Apprentissage profond", "des couches de neurones, des representations abstraites"),
        ("IA generative", "produire un contenu nouveau, pas une etiquette"),
        ("Modeles de langage", "la specialisation texte : notre sujet"),
    ]
    for i, (nom, detail) in enumerate(niveaux):
        x = 30 + i * 22
        y = 70 + i * 54
        teinte = "s1" if i == 4 else "trait"
        d.boite(x, y, 500 - i * 44, 46, teinte=teinte)
        d.texte(x + 16, y + 20, nom, taille=13, gras=True, ancre="start")
        d.texte(x + 16, y + 37, detail, taille=10, couleur="encre2", ancre="start")
    d.texte(30, 44, "Quatre niveaux qui s'emboitent, et qu'on confond souvent",
            taille=15, gras=True, ancre="start")
    d.boite(580, 70, 310, 130, teinte="s2")
    d.texte(735, 96, "Modele discriminatif", taille=14, gras=True)
    d.lignes_de_texte(735, 122, ["A quelle categorie appartient", "cette entree ?",
                                 "Sortie : une etiquette, un score"], taille=11)
    d.texte(735, 188, "espace des reponses ferme", taille=11, gras=True, couleur="encre2")
    d.boite(580, 226, 310, 130, teinte="s3")
    d.texte(735, 252, "Modele generatif", taille=14, gras=True)
    d.lignes_de_texte(735, 278, ["Quelle suite plausible", "puis-je produire ?",
                                 "Sortie : un contenu inedit"], taille=11)
    d.texte(735, 344, "espace des reponses ouvert", taille=11, gras=True, couleur="encre2")
    d.texte(460, 410, "Aucun des deux ne comprend : tous deux exploitent des regularites statistiques apprises.",
            taille=12, gras=True)
    d.texte(460, 436, "L'ouverture du second fait sa puissance et tout son risque : c'est a vous de la borner.",
            taille=11, couleur="encre2")
    return d


def plongements_geometrie() -> Dessin:
    """Séance 2 : le sens devient de la géométrie, et la proximité se mesure."""
    d = Dessin(920, 440, "Le sens devient de la geometrie")
    d.boite(30, 70, 440, 300, teinte="grille")
    d.texte(250, 56, "deux dimensions, des centaines en realite", taille=11, couleur="encre2")
    nuages = [
        ("s1", [(110, 130, "chien"), (158, 158, "chat"), (96, 182, "cheval")]),
        ("s3", [(330, 120, "Paris"), (378, 150, "Abidjan"), (318, 176, "Lyon")]),
    ]
    for teinte, points in nuages:
        for x, y, mot in points:
            d.ajouter(f'<circle cx="{x}" cy="{y}" r="5" fill="var(--{teinte})"/>')
            d.texte(x + 12, y + 4, mot, taille=11, ancre="start", couleur="encre2")
    paires = [((110, 270, "homme"), (230, 250, "femme")), ((170, 340, "roi"), (290, 320, "reine"))]
    for (x1, y1, a), (x2, y2, b) in paires:
        d.ajouter(f'<circle cx="{x1}" cy="{y1}" r="5" fill="var(--s2)"/>')
        d.ajouter(f'<circle cx="{x2}" cy="{y2}" r="5" fill="var(--s2)"/>')
        d.texte(x1 - 10, y1 + 4, a, taille=11, ancre="end", couleur="encre2")
        d.texte(x2 + 12, y2 + 4, b, taille=11, ancre="start", couleur="encre2")
        d.fleche(x1 + 8, y1 - 2, x2 - 8, y2 + 2, teinte="s2")
    d.texte(250, 390, "meme direction = meme relation", taille=11, gras=True, couleur="encre2")
    cartes = [
        ("Une liste de nombres", "chaque jeton devient un vecteur de", "plusieurs centaines de dimensions"),
        ("Une distance mesurable", "la similarite cosinus dit la proximite", "sans aucun mot commun"),
        ("Le sens depend du contexte", "le vecteur de << avocat >> est recalcule", "selon les mots qui l'entourent"),
        ("Le socle de la recherche", "retrouver << conge de maternite >> a partir", "de << arret apres accouchement >>"),
    ]
    for i, (titre, l1, l2) in enumerate(cartes):
        y = 70 + i * 78
        d.boite(500, y, 390, 66, teinte="s1" if i == 3 else "trait")
        d.texte(516, y + 24, titre, taille=13, gras=True, ancre="start")
        d.texte(516, y + 42, l1, taille=10, couleur="encre2", ancre="start")
        d.texte(516, y + 57, l2, taille=10, couleur="encre2", ancre="start")
    return d


def architecture_transformeur() -> Dessin:
    """Séance 2 : la pile d'un transformeur, et ce que l'attention résout."""
    d = Dessin(940, 480, "Dans le moteur : la pile, et ce que l'attention resout")
    etages = [
        ("Texte decoupe en jetons", "s1", 40),
        ("Plongements + position", "s1", 40),
        ("Attention multi-tete : chaque jeton regarde les autres", "s2", 40),
        ("Reseau dense : transformation apprise", "s2", 40),
        ("Normalisation + connexion residuelle", "s2", 40),
        ("Projection sur le vocabulaire", "s3", 40),
    ]
    y = 76
    for i, (nom, teinte, h) in enumerate(etages):
        d.boite(40, y, 420, h, teinte=teinte, tirets=2 <= i <= 4)
        d.texte(250, y + 25, nom, taille=12, gras=i in (0, 5))
        if i < len(etages) - 1:
            d.fleche(250, y + h, 250, y + h + 12)
        y += h + 12
    d.boite(474, 196, 22, 160, teinte="trait", tirets=True)
    d.texte(520, 268, "x N", taille=13, gras=True, ancre="start")
    d.texte(520, 288, "32 a 120 couches", taille=10, couleur="encre2", ancre="start")
    d.texte(40, 52, "La meme brique, empilee, du texte a la probabilite du jeton suivant",
            taille=15, gras=True, ancre="start")
    d.texte(690, 76, "A quoi regarde << il >> ?", taille=14, gras=True)
    phrase = [("le", 2), ("trophee", 46), ("n'entre", 4), ("pas", 2), ("dans", 3), ("la", 4),
              ("valise", 17), ("car", 4), ("il", 7), ("est", 3), ("trop", 4), ("grand", 4)]
    yy = 104
    for mot, poids in phrase:
        largeur = 4 + poids * 3.2
        d.barre(600, yy, largeur, 14, "s2" if poids >= 15 else "attenue")
        d.texte(594, yy + 12, mot, taille=10, ancre="end", couleur="encre2")
        d.texte(606 + largeur, yy + 12, f"{poids} %", taille=10, ancre="start", couleur="encre2")
        yy += 22
    d.texte(740, 404, "Aucune regle de grammaire ne dit que << il >> designe le trophee :",
            taille=11, couleur="encre2")
    d.texte(740, 422, "le modele l'a appris, et son attention le montre.", taille=11, couleur="encre2")
    d.texte(470, 464, "La phrase entiere est traitee d'un bloc : l'entrainement se parallelise, et deux jetons distants se lient directement.",
            taille=11, gras=True, couleur="encre2")
    return d


def methode_clair() -> Dessin:
    """Séance 3 : les cinq questions à poser avant d'écrire un prompt."""
    d = Dessin(920, 440, "Cinq questions avant d'ecrire")
    lignes = [
        ("C", "Contexte", "De quoi parle-t-on, pour qui, dans quel but ?", "Factures echues, lues par un comptable"),
        ("L", "Livrable", "Quelle forme, quelle longueur, quel support ?", "Un brouillon de relance, 150 mots au plus"),
        ("A", "Action", "Un verbe precis, une seule tache a la fois.", "Rediger le brouillon, sans l'envoyer"),
        ("I", "Illustrations", "Un exemple de ce qui est attendu ou refuse.", "Un brouillon valide, un cas de litige"),
        ("R", "Regles", "Contraintes, interdits, critere de reussite.", "Aucun montant invente, arret si litige"),
    ]
    d.texte(30, 48, "Cinq lettres, cinq questions, cinq lignes au brouillon",
            taille=15, gras=True, ancre="start")
    for i, (lettre, nom, question, exemple) in enumerate(lignes):
        y = 76 + i * 66
        d.boite(30, y, 56, 56, teinte="s1")
        d.texte(58, y + 36, lettre, taille=24, gras=True)
        d.boite(98, y, 420, 56, teinte="trait")
        d.texte(114, y + 24, nom, taille=13, gras=True, ancre="start")
        d.texte(114, y + 42, question, taille=10, couleur="encre2", ancre="start")
        d.boite(530, y, 360, 56, teinte="s3")
        d.texte(546, y + 34, exemple, taille=11, couleur="encre2", ancre="start")
    d.texte(460, 424,
            "Si vous ne savez pas repondre a l'une des cinq, le modele ne le saura pas davantage que vous.",
            taille=12, gras=True)
    return d


def chaine_de_prompts() -> Dessin:
    """Séance 3 : quatre prompts nets et quatre validations, au lieu d'un prompt qui s'allonge."""
    d = Dessin(940, 420, "Quatre prompts nets, quatre validations")
    etapes = [
        ("1 Extraire", "lister les exigences,", "sans commentaire", "une liste verifiable"),
        ("2 Analyser", "evaluer la couverture", "de chaque exigence", "une matrice d'ecarts"),
        ("3 Rediger", "produire le texte a partir", "de la matrice", "un texte ancre"),
        ("4 Reviser", "relire sous l'angle", "du destinataire", "un livrable relu"),
    ]
    for i, (titre, l1, l2, sortie) in enumerate(etapes):
        x = 30 + i * 228
        d.boite(x, 96, 200, 104, teinte="s1")
        d.texte(x + 100, 124, titre, taille=14, gras=True)
        d.texte(x + 100, 148, l1, taille=10, couleur="encre2")
        d.texte(x + 100, 164, l2, taille=10, couleur="encre2")
        d.boite(x, 240, 200, 50, teinte="s3", tirets=True)
        d.texte(x + 100, 262, "validation humaine", taille=10, gras=True)
        d.texte(x + 100, 280, sortie, taille=10, couleur="encre2")
        d.fleche(x + 100, 200, x + 100, 236, teinte="s3")
        if i < 3:
            d.fleche(x + 200, 265, x + 228, 265, teinte="attenue")
            d.fleche(x + 228, 150, x + 200, 150, teinte="attenue")
    d.texte(30, 50, "Quand un prompt echoue, decoupez : n'allongez pas",
            taille=15, gras=True, ancre="start")
    d.texte(30, 72, "une tache par prompt, un format de sortie par prompt, un point de validation par etape",
            taille=11, couleur="encre2", ancre="start")
    d.texte(470, 346, "Une erreur vue a l'etape 1 coute une reformulation ; vue a l'etape 4, elle a contamine le livrable.",
            taille=12, gras=True)
    d.texte(470, 372, "Une fois eprouvee, la chaine s'ecrit une fois, se rejoue, puis se code : c'est le graphe de la seance 10.",
            taille=11, couleur="encre2")
    return d


def rag_six_etapes() -> Dessin:
    """Séance 9 : de la question à la réponse sourcée, et ce que la méthode ne répare pas."""
    d = Dessin(940, 440, "De la question a la reponse sourcee")
    etapes = [
        ("1 Question", "<< quel est le delai", "de preavis ? >>"),
        ("2 Vectorisation", "la question devient", "un vecteur"),
        ("3 Recherche", "les passages proches", "sont retrouves"),
        ("4 Extraits", "trois a cinq passages,", "avec leur reference"),
        ("5 Prompt augmente", "question + extraits", "+ << reponds a partir de ceci >>"),
        ("6 Reponse sourcee", "ancree, citant", "le document et la page"),
    ]
    for i, (titre, l1, l2) in enumerate(etapes):
        x = 24 + (i % 3) * 306
        y = 84 + (i // 3) * 112
        teinte = "s3" if i == 5 else "s1"
        d.boite(x, y, 272, 86, teinte=teinte)
        d.texte(x + 136, y + 26, titre, taille=13, gras=True)
        d.texte(x + 136, y + 48, l1, taille=10, couleur="encre2")
        d.texte(x + 136, y + 64, l2, taille=10, couleur="encre2")
        if i % 3 < 2:
            d.fleche(x + 272, y + 43, x + 306, y + 43, teinte="attenue")
    d.fleche(160, 170, 160, 196, teinte="attenue")
    d.texte(24, 52, "Aucun entrainement : on change seulement ce que le modele a sous les yeux",
            taille=15, gras=True, ancre="start")
    d.boite(24, 320, 440, 96, teinte="bon", tirets=True)
    d.texte(244, 344, "Ce que la methode resout", taille=13, gras=True)
    d.lignes_de_texte(244, 366, ["repondre sur des documents prives ou recents",
                                 "citer une source verifiable, page par page",
                                 "mettre a jour la connaissance sans reentrainer"], taille=10)
    d.boite(490, 320, 426, 96, teinte="critique", tirets=True)
    d.texte(703, 344, "Ce qu'elle ne repare pas", taille=13, gras=True)
    d.lignes_de_texte(703, 366, ["une base documentaire mal rangee ou perimee",
                                 "des documents scannes sans reconnaissance de texte",
                                 "une question dont la reponse n'existe nulle part"], taille=10)
    return d


FIGURES = {
    "famille-ia.svg": famille_ia,
    "plongements-geometrie.svg": plongements_geometrie,
    "architecture-transformeur.svg": architecture_transformeur,
    "methode-clair.svg": methode_clair,
    "chaine-de-prompts.svg": chaine_de_prompts,
    "rag-six-etapes.svg": rag_six_etapes,
    "port-et-adaptateurs.svg": port_et_adaptateurs,
    "ecosysteme-ouvert.svg": ecosysteme_ouvert,
    "pipeline-deploiement.svg": pipeline_deploiement,
    "exploitation-agent.svg": exploitation_agent,
    "cinq-implementations.svg": cinq_implementations,
    "graphe-langgraph.svg": graphe_langgraph,
    "trois-memoires.svg": trois_memoires,
    "pipeline-rag.svg": pipeline_rag,
    "decoupage-documents.svg": decoupage_documents,
    "description-outil.svg": description_outil,
    "techniques-prompting.svg": techniques_prompting,
    "frontiere-donnee-consigne.svg": frontiere_donnee_consigne,
    "jetons-decoupage.svg": jetons_decoupage,
    "temperature-echantillonnage.svg": temperature_echantillonnage,
    "trois-temps-entrainement.svg": trois_temps_entrainement,
    "memoire-modeles-locaux.svg": memoire_modeles_locaux,
    "frise-agentique.svg": frise_agentique,
    "anatomie-llm.svg": anatomie_llm,
    "familles-modeles.svg": familles_modeles,
    "anatomie-prompt.svg": anatomie_prompt,
    "boucle-agent.svg": boucle_agent,
    "appel-outil.svg": appel_outil,
    "quatre-familles.svg": quatre_familles,
    "etat-reprise.svg": etat_reprise,
    "chaine-mcp.svg": chaine_mcp,
    "topologies-multi-agents.svg": topologies_multi_agents,
    "patterns-orchestration.svg": patterns_orchestration,
    "echelle-risque.svg": echelle_risque,
    "cout-par-etapes.svg": cout_par_etapes,
}
