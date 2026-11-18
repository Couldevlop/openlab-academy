# Bases de Python, jour après jour — conception

Date : 2026-11-14. **Nouveau parcours autonome et payant**, dans son propre fichier
`data/parcours/07-python-application-rh.yaml`. Le parcours « Développeur Python »
(`01-developpeur-python.yaml`, 12 modules, portfolio et capstone devant jury) reste intact : c'est le
cursus long, celui-ci est le cours intensif de 7 semaines qui mène à une application démontrable.

## Intention

Les bases de Python sont le sujet le plus couvert du web : documentation officielle, MOOC gratuits,
vidéos, exercices en ligne. Rédiger un cours de plus qui explique `if`, `for` et les listes n'a aucune
valeur. Ce cours ne gagne pas par le contenu, qui est connu, mais par **ce qu'il garantit** : à la fin
de chaque journée, l'apprenant a prouvé qu'il maîtrise ce qu'il vient d'apprendre, et il ne peut pas
avancer sans cette preuve.

Trois promesses tiennent cette différence :

1. **On ne passe pas sans avoir prouvé.** Chaque journée se ferme sur un challenge à réussir ; la
   journée suivante reste verrouillée tant qu'il n'est pas rendu.
2. **On ne commence pas sans avoir retenu.** Chaque journée s'ouvre sur un rappel de la veille, à
   valider avant que la leçon du jour s'ouvre. La répétition espacée est dans la structure, pas dans
   un conseil en bas de page.
3. **On travaille sur du vrai.** Tous les exercices tournent autour d'un même fil rouge concret
   plutôt que sur `foo` et `bar`.

## Objectifs

- À la fin des 15 premiers jours, l'apprenant écrit seul un programme Python d'une centaine de lignes,
  lisible, qui lit des données, les transforme, gère ses erreurs et se teste.
- À la fin des 35 jours, il peut **montrer** son application RH à quelqu'un : une API documentée, un
  écran de démonstration, puis une version administrable.
- Chaque leçon se clôt par une preuve exécutable, pas par un sentiment de compréhension.
- Le passage au bloc 2 du parcours (fichiers, erreurs, tests) se fait sans révision préalable.

## Non-objectifs

- Couvrir la totalité du langage : ni classes avancées, ni asynchrone, ni typage générique. Le bloc 1
  s'arrête aux fonctions et aux modules.
- Remplacer la documentation officielle : le cours y renvoie et apprend à la lire.
- Produire des vidéos : le contenu est écrit, illustré et exécutable.

## Anti-objectifs (ce qui ferait échouer le cours même s'il fonctionne)

- Un apprenant qui finit les 15 jours sans savoir écrire une fonction depuis une page blanche.
- Des quiz devinables sans avoir lu la leçon.
- Un verrou vécu comme une punition administrative plutôt que comme une preuve.
- Des exercices corrigés uniquement par un humain : la boucle de retour doit être immédiate.

## Contraintes décidées

| Point | Décision | Qui l'a décidée |
|---|---|---|
| Périmètre | Parcours autonome de 35 jours : bases du langage puis trois séances de frameworks | l'utilisateur |
| Preuve du challenge | chaque journée est livrée avec sa batterie de tests exécutable en local : rouge, puis vert, puis on rend | l'utilisateur |
| Frameworks | FastAPI, puis Streamlit, puis Django | FastAPI et Streamlit : l'utilisateur ; Django : le rédacteur, voir plus bas |
| Tarif | fixé par l'administrateur dans l'écran des tarifs, jamais dans le fichier de parcours | l'utilisateur |
| Rythme | 5 jours par semaine, 1 h 30 par jour (10 min rappel, 50 min leçon, 30 min challenge) | l'utilisateur |
| Volume | ~8 h par semaine, conforme au format déjà annoncé des deux parcours | existant |
| Modèle économique | Parcours payant : dossier, échéancier, blocage sur impayé | l'utilisateur |
| Accès | Inscription sur la période d'une cohorte, puis **accès libre dans la fenêtre** : aucun déverrouillage par date | l'utilisateur |
| Progression | Verrou pédagogique : rappel validé → leçon ouverte ; challenge rendu → journée suivante ouverte | l'utilisateur |
| Langue | Français ; contenu pédagogique hors `_()` | règle projet |

## Comment la progression est obtenue

Rien à développer : la plateforme sait déjà le faire.

- `enforce_lesson_completion` sur le parcours verrouille les leçons en séquence.
- Une leçon n'est « complète » que si son quiz est réussi et son devoir rendu
  (`enforce_quiz_completion`, `enforce_assignment_completion`).

Chaque journée se publie donc en **deux leçons** :

1. `J07 · Rappel` — une page courte (ce qu'il fallait retenir de J06, en cinq points) et un quiz de
   rappel à réussir. Tant qu'il échoue, la leçon du jour reste fermée.
2. `J07 · Leçon` — le cours du jour, ses astuces, puis le challenge en devoir. Tant qu'il n'est pas
   rendu, J08 reste fermée.

Deux réglages du parcours sont posés en conséquence : `delai_exercices_minutes: 0` (sinon les
exercices attendent une heure après l'ouverture de la leçon, ce qui casserait l'accès flexible) et un
nombre de tentatives de quiz généreux, la preuve visée étant la maîtrise, pas la note.

## Anatomie d'une journée

Chaque leçon du jour suit le même gabarit, ce qui rend le cours prévisible et rapide à parcourir :

1. **Ce que vous saurez faire ce soir** — une phrase, à l'infinitif, vérifiable.
2. **Le problème d'abord** — une situation du fil rouge que l'apprenant ne sait pas encore résoudre.
3. **La notion** — l'explication, courte, avec un schéma quand la notion est spatiale (mémoire,
   portée, mutabilité) et du code exécutable sinon.
4. **À la main** — l'apprenant tape, exécute, observe. Pas de copier-coller passif.
5. **L'astuce du jour** — une habitude de professionnel que les cours de base n'enseignent jamais
   (lire une trace d'erreur de bas en haut, nommer une variable par ce qu'elle contient, etc.).
6. **Le piège du jour** — l'erreur que presque tout le monde commet sur cette notion, montrée en vrai,
   avec son message d'erreur exact.
7. **Challenge** — l'épreuve à réussir pour ouvrir le lendemain, avec ses critères d'acceptation
   explicites.

## Le fil rouge : une application RH, construite du premier au dernier jour

L'apprenant construit **une application de gestion du personnel d'une PME ivoirienne**, en francs CFA :
un effectif (nom, poste, date d'embauche, salaire), les congés et les absences, le calcul d'un bulletin
simple, et les états que demande une direction (masse salariale, ancienneté, absences du mois).

Ce sujet a trois qualités que le cours exploite :

- il couvre toutes les notions du bloc 1 sans artifice — des nombres pour les salaires, des chaînes
  pour les noms, des dates pour l'ancienneté, des listes et des dictionnaires pour l'effectif, des
  conditions pour les règles de congés, des fonctions pour les calculs, des modules pour le rangement ;
- il a des **règles métier vraies**, donc des cas limites qui justifient les tests (un mois incomplet,
  une absence à cheval sur deux mois, une embauche en cours de mois) ;
- il se **montre** : à la fin, ce n'est pas un exercice, c'est une application qu'on ouvre devant
  quelqu'un.

Toutes les données sont fictives et générées pour le cours. Le cours dit explicitement pourquoi des
données RH réelles ne sortent jamais d'un poste de travail, et ce que la loi ivoirienne sur les données
personnelles impose à celui qui écrit ce genre d'outil.

## L'architecture s'enseigne dès le premier jour, sans le mot

La plupart des cours de base produisent un script où tout se mélange : la saisie, le calcul et
l'affichage dans la même fonction. L'apprenant perd ensuite des années à s'en défaire. Ici, les bonnes
habitudes sont installées dès la première semaine, par la pratique et sans vocabulaire d'architecte.

Quatre règles, introduites une par une et jamais relâchées :

1. **Ce qui calcule ne parle jamais à l'écran.** Dès que l'apprenant écrit sa première fonction
   (semaine 1), elle rend une valeur ; c'est l'appelant qui affiche. Un `print` dans un calcul est
   signalé comme une faute, pas comme un détail de style.
2. **Le cœur ne connaît ni fichier, ni réseau, ni framework.** Les règles RH (ancienneté, droit à
   congés, masse salariale) ne savent pas d'où viennent les données. On leur passe des données déjà
   lues (semaine 2), ce qui les rend testables sans rien monter.
3. **On valide aux frontières, pas au milieu.** Toute donnée qui entre est vérifiée une fois, à
   l'entrée, puis circule en confiance (semaine 3, avec Pydantic). Le cœur ne passe pas son temps à se
   demander si un salaire est négatif.
4. **Les dépendances pointent vers l'intérieur.** Le cœur ne cite personne ; ce sont les couches
   extérieures qui le citent. C'est ce qui rend possibles les trois habillages successifs.

Le mot « hexagonal » n'est prononcé qu'en semaine 4, quand l'apprenant branche FastAPI sur un cœur
qu'il n'a pas à modifier d'une ligne : il découvre alors qu'il pratiquait déjà cette architecture, et
le nom vient se poser sur une expérience plutôt que sur une théorie.

La sécurité suit le même chemin : on ne fait pas un chapitre « sécurité », on place l'habitude au
moment où elle a du sens — un secret jamais écrit dans le code (semaine 3), une donnée du client
jamais interpolée dans une requête (semaine 6), des données RH qui ne quittent pas le poste
(semaine 1), des droits vérifiés côté serveur et non dans l'écran (semaine 7).

## Les sept semaines

| Semaine | Séance | Journées | Ce qui est prouvé à la fin |
|---|---|---|---|
| 1 | 01 · Premiers pas | J01 à J05 | Installer, exécuter, calculer, décider, répéter |
| 2 | 02 · Structures de données | J06 à J10 | Ranger un effectif, le retrouver, le transformer |
| 3 | 03 · Fonctions, modules et validation | J11 à J15 | Découper en fonctions, organiser en modules, se tester, et refuser une donnée invalide à l'entrée (Pydantic) |
| 4 | 04 · FastAPI | J16 à J20 | L'application RH répond en API, documentée automatiquement |
| 5 | 05 · Streamlit | J21 à J25 | Un écran de démonstration qu'on montre à un tiers |
| 6-7 | 06 · Django | J26 à J35 | La version administrable : ORM, authentification, rôles, back-office |

Les trois premières semaines écrivent le cœur en Python pur, sans aucune dépendance : c'est lui qui
sera ensuite exposé en API, affiché par Streamlit, puis porté sur Django. L'apprenant voit ainsi la
même logique métier survivre à trois habillages différents, ce qui est la leçon d'architecture la plus
utile du parcours.

Le détail jour par jour est écrit dans le plan d'implémentation, pas ici.

## Comment un challenge se prouve

Le rendu d'un devoir ouvre la journée suivante dès la remise, et la chaîne de correction de la
plateforme est asynchrone : seule, elle ne tient pas la promesse « on ne passe pas sans avoir prouvé ».
Chaque journée est donc livrée avec **sa batterie de tests**, exécutable sur le poste de l'apprenant :

- l'énoncé du challenge et ses critères d'acceptation ;
- un fichier de tests qui échoue au départ ; l'apprenant le fait passer au vert ;
- une solution de référence, révélée seulement après le rendu.

L'apprenant voit donc rouge, travaille, voit vert, puis rend. La preuve est immédiate et objective ;
le formateur n'arbitre plus que ce que les tests ne savent pas juger (lisibilité, choix de conception).
C'est 35 harnais de tests à écrire en plus du texte : le plan d'implémentation doit les compter comme
une tâche à part entière de chaque journée, au même titre que la rédaction.

## Décisions techniques prises par le rédacteur

- **Réglages par parcours.** Le délai d'ouverture des exercices, le nombre de tentatives et le score
  minimum sont aujourd'hui des réglages uniques de la plateforme : les régler pour ce cours
  déréglerait le parcours agentique. Ils deviennent propres à chaque parcours ; c'est un lot de
  développement à faire avant la rédaction.
- **Deux leçons par journée.** Le schéma actuel associe un module à une leçon et lui crée d'office un
  livrable et une mise en situation. Une page de rappel n'en veut aucun : le schéma doit accepter une
  séance sans exercices. Second lot de développement préalable.
- **Prérequis enseignés au fil de l'eau.** Classes, exceptions, fichiers et SQL sont introduits là où
  le fil rouge les réclame, et non renvoyés à un autre parcours.
- **Systèmes et pile.** Windows, macOS et Linux sont donnés en une ligne chacun quand les commandes
  diffèrent. SQLite pour Django, pas de Docker : le parcours annonce « aucun prérequis » et doit le
  tenir.

## Ce qui est laissé au rédacteur

- Le découpage fin des quinze journées et le dosage de chaque notion.
- Le choix des schémas (figures SVG déterministes, comme pour le parcours agentique).
- Les énoncés de challenge et leurs critères d'acceptation.
- Le texte des rappels, sous contrainte : cinq points maximum, repris de la veille, jamais de notion
  nouvelle.

## Choix faits par le rédacteur, à corriger si besoin

- **Django comme troisième framework**, plutôt que Flask : une application RH a besoin
  d'authentification, de rôles, de migrations et d'un back-office, que Django fournit et que Flask
  oblige à recoder ; et après FastAPI, Flask n'enseigne presque rien de neuf, alors que Django
  introduit un autre modèle (ORM, MVT, batteries incluses).
- Durée portée à 35 jours (7 semaines, ~56 h) pour absorber les trois séances de frameworks.
- Tarif, durée de la fenêtre de cohorte et date d'ouverture : non fixés ici, ils relèvent de
  l'administrateur dans l'écran des tarifs.
- Prérequis affiché : aucun, le parcours démarre au niveau zéro (déjà annoncé dans le fichier).
- Un carnet d'exercices téléchargeable par semaine, construit par le même script déterministe que
  celui du parcours agentique.
