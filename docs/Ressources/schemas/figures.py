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


FIGURES = {
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
