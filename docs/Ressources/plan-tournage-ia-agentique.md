# Plan de tournage, parcours IA agentique

Ce document liste les capsules à tourner, séance par séance, et l'outillage gratuit qui permet de les
produire. Il est écrit pour être exécuté : chaque capsule porte une durée visée, une intention, ce qui
apparaît à l'écran et les points de passage obligés.

## Principes de tournage

**Une capsule, une idée.** Si vous ne pouvez pas résumer la capsule en une phrase, c'est qu'il y en a deux.
Une capsule de sept minutes qui traite deux sujets se revoit mal : l'apprenant qui cherche le second doit
retrouver l'instant où il commence.

**Le cours écrit fait foi.** Les leçons de la plateforme portent déjà le détail, les tableaux et le code.
La vidéo ne les récite pas : elle montre ce qu'un texte montre mal, c'est-à-dire un enchaînement qui se
déroule, une erreur qui apparaît, une décision qui se prend. Tout ce qui se lit mieux qu'il ne s'écoute
reste écrit.

**Le visage ne sert que trois fois.** Ouverture de séance, moment de mise en garde, conclusion. Le reste se
tourne en capture d'écran avec voix. Cela réduit le temps de tournage, allège le montage, et supprime la
contrainte de lumière.

**Pas de direct, pas de promesse de date.** Le parcours est annoncé à votre rythme. Une capsule qui cite une
date ou une version précise devra être retournée ; préférez « la version du dépôt que vous avez téléchargée ».

**Le son prime sur l'image.** Une capture d'écran correcte avec un son net passe ; une belle image avec un
son souffle ne passe pas. C'est le seul poste où dépenser, et il ne coûte rien de plus que du soin.

**Durée totale visée : 3 h 20 de vidéo** pour 24 h de formation, soit un rapport vidéo sur travail d'environ
un pour sept. Un parcours où l'on regarde plus qu'on ne pratique n'enseigne pas la construction d'agents.

## Les capsules, séance par séance

### Séance 1, anatomie d'un agent IA

| # | Capsule | Durée | À l'écran |
|---|---|---|---|
| 1.1 | Ce que vous allez construire en huit séances | 4 min | visage, puis la démonstration du dépôt qui tourne |
| 1.2 | Agent, chatbot, RAG, workflow : la question qui tranche | 6 min | schéma `quatre-familles`, animé par étapes |
| 1.3 | La même demande, traitée par les quatre | 7 min | terminal partagé, quatre exécutions en quatre temps |
| 1.4 | La boucle percevoir, raisonner, agir, observer | 6 min | schéma `boucle-agent`, puis le code de la boucle |
| 1.5 | Classer les actions par risque | 5 min | schéma `echelle-risque`, construit action par action |
| 1.6 | Écrire son cadrage, en direct | 8 min | éditeur, le fichier de cadrage rempli devant l'apprenant |

**1.1, intention :** donner envie et poser le contrat. Montrer le résultat final dès la première minute, puis
annoncer ce qui sera exigé. Points de passage : le fil rouge du recouvrement, les douze factures, la validation
humaine, le fait qu'aucun courriel ne part jamais, et le projet final noté.

**1.3, intention :** la capsule décisive de la séance. Quatre exécutions, même demande, quatre résultats. Le
spectateur doit voir le chatbot répondre sans lire les factures, le RAG citer une procédure, le workflow sortir
un résultat exact, et l'agent prendre une initiative que personne n'avait écrite. Terminer sur la phrase qui
compte : l'initiative est ce que l'on achète, et ce qui oblige à tracer.

**1.6, intention :** montrer qu'un cadrage s'écrit, et qu'il tient en une page. Remplir le fichier en commentant
chaque champ, en particulier la liste des actions interdites, que les débutants oublient.

### Séance 2, tool calling et boucle d'agent

| # | Capsule | Durée | À l'écran |
|---|---|---|---|
| 2.1 | Ce qu'un modèle voit d'un outil | 5 min | le contrat JSON, champ par champ |
| 2.2 | Installer le dépôt et faire passer les tests | 5 min | terminal, de zéro jusqu'au vert |
| 2.3 | Un appel tracé de bout en bout | 8 min | schéma `appel-outil` puis le journal réel |
| 2.4 | Les trois barrières au point d'appel | 6 min | code, exécuté avec des arguments fautifs |
| 2.5 | Ajouter un paramètre, les quatre gestes | 9 min | éditeur et terminal côte à côte, tests écrits avant |
| 2.6 | Quand le plafond d'étapes se déclenche | 4 min | une exécution qui boucle, et son journal |

**2.2, intention :** éliminer l'abandon. C'est la capsule la plus regardée du parcours, et celle qui décide de
qui continue. Montrez l'environnement virtuel, l'installation, les tests, la démonstration qui annonce cinq
factures et 7 730 000 F CFA. Montrez aussi un échec courant, la mauvaise version de Python, et sa correction.

**2.5, intention :** installer la discipline des tests. Écrire le test rouge en premier, à l'écran, avant la
moindre ligne d'implémentation. Ne coupez pas au montage le moment où le test échoue : c'est ce moment qui
enseigne.

**2.6, intention :** montrer que le plafond est un capteur. Fabriquez volontairement une erreur d'outil muette,
observez la répétition, puis corrigez le message d'erreur et montrez la boucle qui conclut en trois tours.

### Séance 3, patterns d'orchestration

| # | Capsule | Durée | À l'écran |
|---|---|---|---|
| 3.1 | Quatre patterns, quatre signes dans le besoin | 6 min | schéma `patterns-orchestration` |
| 3.2 | Le routage et la classe qui n'existe pas | 7 min | code, avec un modèle qui invente une classe |
| 3.3 | Paralléliser, et la fusion qui ment | 7 min | exécution avec un lot en échec, rapport faux puis corrigé |
| 3.4 | La boucle de réflexion et sa borne de progrès | 5 min | deux exécutions, avec et sans borne, coûts comparés |
| 3.5 | Composer trois patterns sur le fil rouge | 8 min | tableau blanc numérique, puis le code |
| 3.6 | Savoir dire « pas d'agent ici » | 4 min | visage, cas concret à l'appui |

**3.3, intention :** faire vivre une panne silencieuse. Montrez d'abord le rapport qui paraît complet et dont le
total est faux, laissez un temps de silence, puis révélez le lot manquant. C'est la capsule dont les apprenants
se souviennent.

**3.6, intention :** légitimer le refus. Capsule courte, face caméra, sur un cas réel où un workflow battait
l'agent. Elle vaut une séance entière de méthode.

### Séance 4, état, mémoire et reprise

| # | Capsule | Durée | À l'écran |
|---|---|---|---|
| 4.1 | Trois mémoires qu'on confond | 5 min | schéma dessiné en direct, trois colonnes |
| 4.2 | Écrire l'état avant d'agir | 6 min | code, puis coupure du processus au mauvais moment |
| 4.3 | La clé d'idempotence | 7 min | test écrit d'abord, deux appels, un seul effet |
| 4.4 | Interrompre et reprendre, en vrai | 8 min | terminal, `Ctrl+C` au milieu, relance, fichier d'état |
| 4.5 | Le contexte qui enfle, et comment le contenir | 6 min | compteur de jetons, trois techniques comparées |

**4.4, intention :** la démonstration que tout le monde attend. Coupez réellement le processus, montrez le
fichier d'état, relancez, et prouvez par le fichier de simulation qu'aucune ligne n'a été écrite deux fois.
Refaites ensuite la même manipulation avec une clé d'idempotence fautive, pour montrer le doublon apparaître.

### Séance 5, MCP et interopérabilité

| # | Capsule | Durée | À l'écran |
|---|---|---|---|
| 5.1 | Ce que MCP déplace, et pour qui | 5 min | schéma `chaine-mcp` |
| 5.2 | Publier un outil côté serveur | 7 min | éditeur, le même outil passé de l'agent au serveur |
| 5.3 | Connexion, découverte, appel, fermeture | 6 min | terminal, les quatre temps avec leurs journaux |
| 5.4 | Un outil distant est une frontière de confiance | 6 min | une description hostile publiée par un serveur de test |
| 5.5 | Outil local ou serveur : l'arbitrage chiffré | 5 min | tableau de comparaison, latence mesurée |

**5.4, intention :** montrer l'attaque avant d'enseigner la défense. Montez un serveur de test dont la
description d'outil contient une instruction, observez le comportement, puis appliquez la règle : une
description distante est une donnée.

### Séance 6, architectures multi-agents

| # | Capsule | Durée | À l'écran |
|---|---|---|---|
| 6.1 | Pourquoi plusieurs agents, et pourquoi rarement | 5 min | schéma `topologies-multi-agents` |
| 6.2 | Contrats de tâche et de rapport | 6 min | code, les deux structures écrites devant l'apprenant |
| 6.3 | Le superviseur qui arbitre vraiment | 7 min | exécution, un lot en échec qui remonte |
| 6.4 | Mesurer le surcoût d'une topologie | 7 min | deux exécutions chronométrées, trois chiffres comparés |
| 6.5 | Les trois pannes du multi-agents | 6 min | boucle entre pairs reproduite en direct |

**6.4, intention :** désamorcer la mode. Les chiffres doivent sortir devant l'apprenant, sur douze factures,
et montrer que la version multi-agents perd. Puis changer l'échelle et montrer l'inversion.

### Séance 7, sécurité, évaluation, observabilité

| # | Capsule | Durée | À l'écran |
|---|---|---|---|
| 7.1 | L'injection indirecte, expliquée à un non-spécialiste | 5 min | visage, puis la note hostile dans le jeu de données |
| 7.2 | Les trois défenses, dans le code | 8 min | les trois emplacements, montrés l'un après l'autre |
| 7.3 | Prouver qu'une note n'influence rien | 7 min | deux jeux de données, deux exécutions, diff vide |
| 7.4 | Tester des propriétés, pas des chaînes | 6 min | un test fragile, puis sa réécriture |
| 7.5 | Lire une trace, et ce qu'elle ne doit pas contenir | 6 min | journal réel, champs commentés |
| 7.6 | Budget et limites dures | 5 min | une exécution arrêtée par le budget |
| 7.7 | Le registre des risques résiduels | 5 min | document rempli en direct, trois lignes |

**7.3, intention :** la capsule la plus convaincante du parcours. Le `diff` vide à l'écran vaut toutes les
explications. Montrez ensuite une version volontairement vulnérable, où le `diff` n'est pas vide.

### Séance 8, projet final

| # | Capsule | Durée | À l'écran |
|---|---|---|---|
| 8.1 | L'énoncé, lu et commenté | 7 min | la page du capstone, critère par critère |
| 8.2 | Les cinq contrôles éliminatoires | 6 min | chacun vérifié en direct sur une copie d'exemple |
| 8.3 | Comment est corrigée votre copie | 5 min | la grille, poste par poste |
| 8.4 | Revue technique d'un projet rendu | 12 min | relecture commentée d'un projet complet |

**8.4, intention :** montrer la relecture d'un professionnel. C'est la capsule qui transforme un cours en
formation : l'apprenant voit comment son travail sera lu, et ce qu'un relecteur remarque en premier.

### Capsules transversales, tournées une fois

| # | Capsule | Durée | Usage |
|---|---|---|---|
| T.1 | Préparer son poste de travail | 6 min | avant la séance 1 |
| T.2 | Lire une trace d'exécution | 5 min | rappelée en séances 2, 4 et 7 |
| T.3 | Écrire un test avant le code | 5 min | rappelée en séances 2, 4 et 7 |
| T.4 | Rendre son travail sur la plateforme | 3 min | avant le premier livrable |

## Un script complet, comme modèle

Voici le script de la capsule 1.2, à lire tel quel. Les indications entre crochets ne se lisent pas.

> [écran : schéma `quatre-familles`, seule la colonne « Chatbot » visible]
>
> Quatre mots reviennent dans toutes les conversations sur l'IA, et ils désignent quatre choses différentes.
> Chatbot. RAG. Workflow. Agent. Les confondre coûte cher, dans les deux sens : on paie la complexité d'un
> agent pour un besoin qu'un workflow traitait mieux, ou bien on bricole un workflow là où il fallait un agent.
>
> Une seule question les départage, et je vais vous la donner tout de suite : qui choisit l'étape suivante.
>
> [apparition de la colonne « Chatbot »]
>
> Dans un chatbot, la question ne se pose pas. Vous écrivez, il répond. Un message, une réponse. Il ne lit
> rien d'autre que ce que vous lui donnez, et il n'agit sur rien.
>
> [apparition de la colonne « RAG »]
>
> Dans un RAG, le code impose toujours le même ordre : chercher dans vos documents, puis rédiger à partir de
> ce qui a été trouvé. Un seul passage. C'est le développeur qui a décidé de cet ordre, une fois pour toutes.
>
> [apparition de la colonne « Workflow »]
>
> Dans un workflow, c'est encore le développeur qui décide, mais sur plusieurs étapes. Extraire, calculer,
> rédiger. L'enchaînement est écrit à l'avance. Il est exact, reproductible, et il se teste. Retenez ce
> dernier point, on y reviendra souvent.
>
> [apparition de la colonne « Agent », puis de la flèche de retour]
>
> Dans un agent, le modèle décide à chaque tour. Il regarde où il en est, choisit l'action suivante, observe
> le résultat, et recommence. Personne n'a écrit cet enchaînement.
>
> [plein écran sur la flèche de retour]
>
> Cette flèche, c'est toute la différence. Et c'est aussi tout le problème : puisque personne n'a écrit
> l'enchaînement, personne ne sait d'avance combien de tours il prendra. D'où la deuxième question, qui est
> la suite logique de la première : combien de passages. Un, pour le RAG. Un nombre connu, pour le workflow.
> Un nombre variable pour l'agent, et c'est pour cela qu'il faudra le borner.
>
> Dans la prochaine capsule, nous prenons une seule demande, celle de la directrice financière de notre fil
> rouge, et nous la faisons traiter par les quatre. Vous allez voir les quatre réponses, et vous comprendrez
> en trois minutes ce qu'aucun tableau ne peut expliquer.

## Outils gratuits pour produire les capsules

### Capture d'écran et montage

**OBS Studio**, gratuit, Windows, macOS, Linux, sans compte ni filigrane. C'est l'outil de capture de
référence. Deux usages suffisent pour ce parcours : capture d'une fenêtre avec le micro, et scènes
préparées à l'avance pour basculer entre l'éditeur et le terminal sans toucher aux fenêtres pendant
l'enregistrement. Compter une demi-journée d'apprentissage, une fois pour toutes. Limite réelle : le montage
n'est pas son métier, il faut un second outil.

**Kdenlive**, gratuit, les trois systèmes. Montage complet : coupes, titres, incrustation de la webcam,
export. Suffisant pour tout ce parcours. Limite réelle : l'interface demande une semaine d'habitude, et il
vaut mieux enregistrer souvent, le programme ayant mauvaise réputation sur la stabilité en projet long.

**Shotcut**, gratuit, les trois systèmes. Plus simple que Kdenlive, un peu moins puissant. Si vous ne faites
que couper, assembler et ajouter un titre, c'est le meilleur rapport entre le temps d'apprentissage et le
résultat. C'est celui que je recommanderais pour commencer.

**DaVinci Resolve**, version gratuite, les trois systèmes. Qualité professionnelle, étalonnage et montage
audio inclus. Limites de la version gratuite, à connaître avant de s'engager : pas d'export au-delà du 4K
Ultra HD, certains effets réservés à la version payante, et une machine robuste exigée. À réserver si vous
visez une finition soignée et acceptez une courbe d'apprentissage de plusieurs semaines.

### Son

**Audacity**, gratuit, les trois systèmes. Réduction de bruit, normalisation, compression. Deux gestes
suffisent : capturer deux secondes de silence pour établir le profil de bruit, puis appliquer la réduction,
et normaliser à un niveau constant d'une capsule à l'autre.

**Matériel** : un micro-casque USB correct change tout, et coûte moins qu'une journée de montage. À défaut,
le micro d'un téléphone récent tenu à vingt centimètres bat le micro intégré d'un ordinateur portable.
Enregistrez dans une pièce meublée, jamais dans un local vide ou carrelé, et coupez la climatisation le
temps de la prise.

### Sous-titres

**Whisper d'OpenAI**, version libre exécutable sur votre machine, gratuite, sans envoi de vos fichiers à un
service. La transcription du français est bonne, les noms propres techniques demandent une relecture.
Produisez un fichier de sous-titres par capsule, relisez-le, et déposez-le avec la vidéo. Limite réelle :
une machine sans carte graphique transcrit lentement, comptez environ le temps réel de la vidéo.

**Sous-titres ou transcription ?** Faites les deux. Les sous-titres servent pendant la lecture ; la
transcription, déposée dans la leçon, sert à retrouver un passage et à rendre le cours consultable par
quelqu'un qui ne peut pas regarder une vidéo.

### Schémas et illustrations

Les neuf schémas du parcours sont déjà construits par le dépôt et exportables en SVG, en clair et en sombre.
Pour les animer par étapes dans une capsule, exportez une variante par étape et enchaînez-les au montage :
c'est plus simple et plus net qu'une animation, et cela reste reproductible.

Pour un croquis fait en direct devant l'apprenant, **Excalidraw** convient : gratuit, utilisable sans compte,
et son trait manuel se distingue nettement des schémas définitifs, ce qui aide le spectateur à comprendre
qu'il regarde un brouillon.

### Hébergement et diffusion

Les capsules se déposent sur la plateforme, leçon par leçon. Si vous les hébergez ailleurs, vérifiez trois
points avant de choisir : que la lecture ne soit pas précédée de publicité, que l'adresse reste valable sans
compte, et que vous puissiez remplacer un fichier sans changer l'adresse. Le troisième point est celui qu'on
oublie, et c'est celui qui coûte le plus cher quand une capsule doit être retournée.

## Ordre de tournage recommandé

Ne tournez pas dans l'ordre des séances. Tournez d'abord **2.2**, l'installation : c'est la capsule la plus
regardée, celle qui demande le plus de reprises, et celle dont la qualité décide du taux d'abandon. Vous
apprendrez l'outillage dessus.

Tournez ensuite les capsules de schéma, qui sont les plus faciles, afin de prendre le rythme : 1.2, 3.1, 5.1,
6.1. Puis les capsules de code, qui demandent une préparation du terminal et de l'éditeur. Gardez pour la fin
les capsules face caméra, 1.1, 3.6 et 8.4, qui se tournent bien quand le reste est déjà en boîte et que vous
savez exactement ce que l'apprenant aura vu avant.
