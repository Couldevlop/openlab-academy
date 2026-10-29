# OpenLab Academy — Parcours de lancement « IA agentique »

Date : 2026-10-29 · Dépôt : `Couldevlop/openlab-academy` (monorepo `D:\OPENLAB`, dossier `Openlab_Academy/`).

## 1. Intention

Lancer la plateforme avec un parcours court, gratuit et attractif, ouvert un mois seulement : « IA agentique :
comprendre, concevoir et maîtriser les agents IA ». Il doit attirer les vibe codeurs, développeurs et experts IA,
montrer la qualité de la plateforme (cohorte, exercices, correction) et créer un premier vivier d'apprenants.

## 2. Décisions de l'utilisateur

### Contenu (texte fourni par l'utilisateur, à reprendre fidèlement, orthographe corrigée)
- **Titre** : IA agentique : comprendre, concevoir et maîtriser les agents IA.
- **Accroche** : « Ne plus simplement utiliser des agents IA. Comprendre leur fonctionnement, maîtriser leurs outils et
  apprendre à les construire. »
- **Public** : vibe codeurs, développeurs, experts IA.
- **Objectifs** (à l'issue de la formation) :
  1. Expliquer la boucle d'exécution d'un agent et distinguer agent, chatbot, RAG et workflow.
  2. Concevoir un agent capable d'appeler des outils et de gérer ses erreurs.
  3. Orchestrer plusieurs étapes avec un framework adapté.
  4. Connecter un agent à des outils via MCP et comprendre les usages d'A2A.
  5. Tester, observer, sécuriser et maîtriser le coût d'exécution d'un agent.
- **Méthode** : démonstration en direct, exercices guidés, analyse des traces d'exécution, développement progressif et
  projet final.
- **Fil rouge** : un agent d'analyse documentaire et de recherche métier qui utilise des outils, vérifie ses résultats
  et produit une synthèse argumentée.
- **Sommaire / programme** (8 séances) :
  1. Comprendre l'anatomie d'un agent (Anatomie d'un agent IA)
  2. Construire un agent Python sans framework (Tool calling et boucle d'agent)
  3. Concevoir l'orchestration (Patterns d'orchestration)
  4. État, mémoire et reprise sur erreur
  5. Connecter les outils avec MCP et comprendre A2A (MCP et interopérabilité)
  6. Construire une collaboration multi-agents (Architectures multi-agents et A2A)
  7. Sécurité, évaluation et observabilité
  8. Projet final et revue technique
- **Prérequis** : savoir lire et modifier un programme Python simple (variables, fonctions, structures de données,
  exceptions) ; être à l'aise avec un terminal et l'installation de dépendances Python ; disposer d'un ordinateur
  permettant de développer, d'une connexion internet stable et d'un navigateur récent ; être prêt à utiliser un
  fournisseur de modèle IA ou une solution compatible, selon l'environnement pédagogique retenu.
- **Non requis au départ** : avoir déjà développé un système multi-agents ; maîtriser LangGraph ou MCP ; avoir
  entraîné un modèle de langage.

### Format et ouverture
- **Gratuit** (aucun tarif, échéancier, rappel ni blocage pour paiement).
- **Vidéos seulement, à son rythme** : aucune séance en direct, aucun groupe. Le cours est en vidéos déjà présentes ;
  l'apprenant se connecte quand il veut. Quiz, exercices et projet final se font en autonomie ; le projet final est
  rendu et corrigé sur la plateforme.
- **Ouvert un mois** : pendant ce mois, inscription libre et accès libre au parcours, à toute heure. **À la fin du
  mois, l'accès est fermé pour tous** (vidéos comprises) et le parcours quitte le catalogue ; la progression et le
  certificat restent dans le profil de l'apprenant.
- **Vidéos pas encore prêtes** : les leçons sont créées avec un emplacement vidéo, rempli plus tard depuis la console.
- **Parcours du lancement** : premier du catalogue et mis en avant sur l'accueil ; il devient le parcours pilote, à
  la place de « Fondamentaux de la Data Science ».
- **Phase de lancement (validé le 2026-10-29)** : toutes les autres formations restent sur la plateforme mais sont
  **cachées aux apprenants et aux visiteurs** pendant le lancement, car elles ne seront peut-être pas prêtes. Ce
  réglage s'active et se désactive **depuis l'interface d'administration**. Priorité du projet : le lancement passe
  avant le reste.

## 3. Choix faits par Claude (à contrôler)

- **Découpage** : séances 1 à 7 = 7 modules (leçon vidéo + texte, mise en situation, quiz) de 3 h ; séance 8 =
  capstone « Projet final et revue technique » de 3 h : le fil rouge complet, rendu sur la plateforme et corrigé
  (grille, correcteur), la « revue technique » étant le retour de correction. Charge : 24 h.
- **Pas de portfolio séparé** (`projets_par_portfolio: 0` dans le fichier du parcours) : le livrable de chaque module
  est l'étape correspondante du fil rouge.
- **Chaque module** : contenu, livrable (étape du fil rouge), mise en situation et quiz de 5 questions, écrits par Claude
  à partir du programme, au niveau du parcours AI Engineer existant.
- **Une seule cohorte**, « Promo 1 », dont les dates **sont** la fenêtre d'ouverture : début O, fin O + 1 mois
  calendaire. Elle sert au moteur d'évaluation (rendu et correction du projet final) ; elle n'a ni séance ni horaire.
  C'est la cohorte pilote ouverte à l'installation, et sur les sites existants par migration du réglage
  `parcours_pilote`.
- **Date d'ouverture O** : modifiable à chaud dans la console (dates de la cohorte). Valeur initiale : réglage
  `ouverture_lancement` de l'écran de réglages ; vide ou passée à l'installation → la date du jour. Changer les dates
  de la cohorte déplace la fenêtre ; aucune autre donnée ne la porte.
- **Fermeture** : hors fenêtre (avant O ou après la fin), l'inscription est refusée et toute page du parcours renvoie
  vers une page « Parcours fermé » (même mécanisme que le blocage pour paiement : redirection de page + refus de
  l'API et des permissions). Les rôles d'agents (administrateur, intendant, formateur, correcteur) ne sont jamais
  bloqués. Après la fin, la tâche planifiée quotidienne dépublie le parcours du catalogue ; certificats et
  progression restent visibles dans le profil.
- **Vidéos** : chaque leçon de module est créée avec un emplacement vidéo vide ; l'administrateur colle le lien ou
  dépose le fichier dans la console. Une leçon sans vidéo reste lisible (texte du module), sans erreur, et la
  republication du fichier de parcours n'efface jamais une vidéo ajoutée.
- **Mise en avant** : ordre du catalogue et de l'accueil piloté par le fichier du parcours, sans toucher au LMS.
- **Nouvelles clés du fichier de parcours**, valables pour tout parcours futur : `gratuit` (case « Parcours gratuit
  (MOOC) »), `acces_limite_a_la_cohorte` (fenêtre d'accès = dates de la cohorte), `mise_en_avant` ; plus
  `projets_par_portfolio` et `heures_par_module`, déjà gérés.
- **« Fondamentaux de la Data Science »** et les autres parcours restent en base ; leur cohorte existante ne change
  pas. Ils sont cachés tant que la phase de lancement est active (ci-dessous).
- **Phase de lancement** : dans l'écran de réglages de la plateforme (bureau `/app`, réservé à l'administrateur), une
  case « Phase de lancement » (cochée par défaut sur une nouvelle installation et à la migration) et une liste
  « Parcours visibles pendant le lancement » (par défaut : le parcours IA agentique). Case cochée : pour un apprenant
  ou un visiteur, tout autre parcours est absent du catalogue, de l'accueil et de la recherche, ne s'inscrit pas, et
  ses pages renvoient vers le catalogue (même mécanisme de redirection et de refus d'API que la fermeture). Les
  inscrits déjà présents dans un parcours caché le gardent caché eux aussi (rien n'est supprimé, aucune progression
  perdue). Les rôles d'agents voient tout. Case décochée : tout redevient comme aujourd'hui, sans autre action.

## 4. Périmètre

### Inclus
- Fichier `data/parcours/` du nouveau parcours, complet et validé par le domaine.
- Prise en charge des nouvelles clés (gratuit, accès limité à la cohorte, mise en avant) dans le domaine, la
  publication et l'ouverture de la cohorte.
- Inscription refusée et accès fermé hors fenêtre, page « Parcours fermé ».
- Retrait automatique du catalogue à la fin (tâche planifiée quotidienne existante ou nouvelle).
- Leçons avec emplacement vidéo, préservé à la republication.
- Parcours pilote changé sur les sites existants (migration de la valeur du réglage).
- Traduction : textes d'interface ajoutés en français dans `_()` (le plan bilingue les traduira) ; le contenu du
  parcours reste en français (règle de la V1 bilingue).

### Exclu
- Contenu des séances au-delà des fiches modules (supports, notebooks, vidéos).
- Séances en direct, groupes, créneaux.
- Tournage et mise en ligne des vidéos.
- Paiement : le parcours est gratuit.

### Anti-objectifs
- Un apprenant (non agent) qui voit une vidéo ou une leçon hors de la fenêtre, y compris par l'API.
- Une inscription acceptée hors fenêtre.
- Une vidéo ajoutée dans la console perdue à la republication du parcours.
- Une régression des parcours existants (payants, gratuits sans fenêtre, blocage pour paiement).

## 5. Contraintes

- Architecture hexagonale (domaine pur), sécurité OWASP au premier plan ; ne pas modifier `apps/lms` ni `apps/frappe`.
- TDD ; couverture back ≥ 99 % ; tests verts sur un site neuf (CI).
- Validation dans Chrome sur la pile locale : catalogue (premier, mis en avant), page du parcours, inscription,
  leçon avec et sans vidéo, rendu du projet final, fermeture (dates de la cohorte passées), retrait du catalogue.
- Travail mené en parallèle du plan bilingue, sur la même branche, commits séparés.

## 6. Laissé au builder

- Mécanisme exact d'ordre du catalogue et de mise en avant dans le LMS.
- Levier exact de dépublication et contenu de la page « Parcours fermé » (charte, lien vers le catalogue).
- Nom du champ de réglage de la date d'ouverture.
