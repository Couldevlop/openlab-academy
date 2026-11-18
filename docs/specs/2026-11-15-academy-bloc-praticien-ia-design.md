# Le Manuel du Praticien de l'IA, porté en bloc de parcours

Document de conception. Écrit le 15 novembre 2026.

## Intention

Transformer l'ouvrage « Le Manuel du Praticien de l'IA » (251 pages, 23 chapitres plus un
capstone) et son dépôt de code compagnon en un **bloc de cinq parcours** dans Openlab Academy,
suivis dans l'ordre, et clos par un projet capstone.

Le livre n'est pas encore commercialisé. Rien ne limite donc ce que les séances reprennent :
elles portent le texte, les exécutions à la main, les exercices corrigés et les projets, sans
avoir à ménager une édition papier déjà vendue.

## Ce qui existe déjà, et qui change tout

**Le livre.** Cinq parties, 23 chapitres plus le capstone, une structure de chapitre identique
d'un bout à l'autre, un fil rouge unique (le cacao ivoirien, la plateforme OpenCacao) et un
ancrage africain constant : coopérative de San-Pédro, woro-woro d'Abidjan, mobile money,
dispensaire rural. Quatre exigences revendiquées : démystifier par l'usage, exécuter chaque
formule à la main, dérouler chaque notion dans un cadre d'expérimentation, ancrer dans une
réalité africaine.

**Le dépôt de code.** `D:\OPENLAB\code_source_livre`, remote
`github.com/Couldevlop/code_source_livre_manuel_du_praticien`, achevé au commit `3c5b2d5` :

- 49 projets, 431 fichiers Python, 53 fichiers de tests, 48 fichiers d'explication ;
- chaque projet en couches, `domain` sans aucune entrée sortie, `infrastructure`,
  `application`, `presentation`, plus `config.py` surchargeable par l'environnement et un
  `__main__.py` lançable par `python -m projet_xxx` ;
- vraies données publiques (scikit-learn, OpenML) mises en cache sous `data/`, avec un repli
  synthétique explicitement étiqueté quand le réseau manque ;
- checklist OWASP par projet, graine fixée à 42, matplotlib en mode non interactif, sorties en
  français ;
- dépendances : **numpy, pandas, scikit-learn, matplotlib, et rien d'autre**. Aucun import de
  torch ni de TensorFlow dans le dépôt.

Ce dernier point est décisif pour une formation en ligne : tout s'exécute sur un ordinateur
portable ordinaire, sans carte graphique, sans compte chez un fournisseur, sans Colab.

## La structure du livre tombe dans le schéma de séance

Les rubriques de chapitre sont normalisées et se comptent sur l'ouvrage entier : feuille de
route (46), résultat exécuté (45), ce que ce projet démontre (45), l'idée à la main (24), le
code complet (44 blocs), point de vigilance (15), définition (12), exercices et corrections
(11 et 11), livrable du chapitre (10).

| Rubrique du livre | Clé de la séance |
|---|---|
| Feuille de route | `contenu` |
| L'idée à la main, exécution manuelle, définition | sections de `cours`, avec tableaux |
| Le code complet | `code:` dont le titre nomme le fichier du projet |
| Résultat exécuté | tableau de section |
| Ce que ce projet démontre | section de synthèse |
| Point de vigilance | section de pièges |
| Exercices et correction | `travaux_pratiques` et corrigé |
| Livrable du chapitre | `livrable` |
| Cadre d'expérimentation | mise en situation |

Le travail de rédaction est donc une **conversion**, pas une création : le texte existe, le code
existe et tourne, les exercices ont leur corrigé.

## Décisions

Prises par le propriétaire du projet :

1. **Cinq parcours**, calés sur les cinq parties, vendables et suivables séparément.
2. **Un seul bloc** les rassemble, dans l'ordre.
3. Les chapitres **18, 19 et 20** ne sont pas redéveloppés : ils renvoient au parcours
   « IA agentique », qui traite le même sujet en dix-huit séances.
4. Le livre n'étant pas commercialisé, les séances peuvent porter tout le contenu.

Prises par le rédacteur, à confirmer en relecture :

5. Le bloc s'appuie sur le doctype natif **`LMS Program`** du LMS, avec son indicateur
   `enforce_course_order` pour imposer l'ordre des parcours.
6. Une séance vaut un chapitre, trois heures. Les chapitres longs (13, 16, 17, 23, qui portent
   trois projets) sont découpés en deux séances.
7. Le chapitre 22, annoncé comme optionnel dans le livre, reste optionnel : séance de clôture du
   parcours III, sans verrou sur la suite.
8. Le capstone du bloc est le projet final du cinquième parcours, pas un parcours à lui seul.

## Le bloc

**Le Manuel du Praticien de l'IA**, ordre imposé.

| # | Parcours | Chapitres | Séances | Ce qu'on en sort |
|---|---|---|---|---|
| 1 | Fondations du deep learning, à la main | 1 à 4 | 4 | dériver, enchaîner, propager l'erreur, entraîner un réseau et le régulariser |
| 2 | Architectures spécialisées | 5 à 8 | 4 | préparer les données, convolutions, séquences et attention, modèles de langage |
| 3 | Apprentissage avancé et multimodal | 9 à 12, 22 | 5 | mise en pratique complète, renforcement, diffusion, multimodal, bio-inspiré en option |
| 4 | Transformers et modèles de langage | 13 à 16 | 6 | traduction par attention, prompting avancé, fine-tuning LoRA, servir un modèle |
| 5 | Industrialisation et terrain | 17, 21, 23 | 5 | RAG en profondeur, LLMOps, applications sectorielles, puis le capstone |

Soit **24 séances** et un capstone, environ 75 heures, sans compter le travail personnel.

Les parcours 1 et 2 n'exigent rien d'autre que de savoir lire du Python simple. Le parcours 5
indique en préambule que les agents sont traités à part, et renvoie au parcours « IA agentique »
pour les chapitres 18 à 20.

## Les chapitres rattachés à leur code

Chaque séance livre une archive construite depuis le dépôt compagnon, comme les carnets et les
dépôts du parcours agentique. Les noms ci-dessous sont les dossiers réels du dépôt.

### Parcours 1, Fondations du deep learning, à la main

| Séance | Chapitre | Projets du dépôt |
|---|---|---|
| 1 | 1, fondements mathématiques | `projet_immobilier_prix_appartement`, `projet_mobile_money_transaction_suspecte` |
| 2 | 2, principes du deep learning | `projet_credit_agricole_modele_revenu`, `projet_marche_surapprentissage` |
| 3 | 3, les réseaux neuronaux | `projet_anti_fraude_non_lineaire` |
| 4 | 4, entraîner des réseaux profonds | `projet_pme_adam_vs_descente`, `projet_scoring_regularisation` |

### Parcours 2, Architectures spécialisées

| Séance | Chapitre | Projets du dépôt |
|---|---|---|
| 1 | 5, personnalisation avec TensorFlow | `projet_annonces_pretraitement`, `projet_mobile_money_normalisation` |
| 2 | 6, les réseaux convolutifs | `projet_controle_qualite_detection_defaut`, `projet_facturation_lecture_compteur` |
| 3 | 7, récurrents et attention | `projet_energie_prevision_demande`, `projet_relation_client_sentiment` |
| 4 | 8, les modèles de langage | `projet_commerce_self_attention`, `projet_emploi_recherche_semantique` |

### Parcours 3, Apprentissage avancé et multimodal

| Séance | Chapitre | Projets du dépôt |
|---|---|---|
| 1 | 9, mettre en pratique | `projet_assurance_cout_sinistre`, `projet_sante_triage_patients` |
| 2 | 10, apprentissage par renforcement | `projet_logistique_livreur_trajet`, `projet_marketing_meilleure_promotion` |
| 3 | 11, modèles génératifs et diffusion | `projet_restauration_diffusion_signal` |
| 4 | 12, modèles multimodaux | `projet_e_commerce_alignement_image_texte`, `projet_tourisme_fusion_texte_chiffres` |
| 5 | 22, bio-inspiré, en option | `projet_chargement_algorithme_genetique`, `projet_fil_rouge_tournee_collecte` |

### Parcours 4, Transformers et modèles de langage

| Séance | Chapitre | Projets du dépôt |
|---|---|---|
| 1 et 2 | 13, NLP avec RNN et attention | `projet_traduction_attention_alignement`, `projet_e_administration_routage_demandes`, `projet_fil_rouge_conformite_eudr` |
| 3 | 14, prompt engineering avancé | `projet_fil_rouge_extraction_prompting` |
| 4 | 15, fine-tuning moderne | `projet_vision_classification_transfert`, `projet_metier_fine_tuning_lora` |
| 5 et 6 | 16, serving et exécution | `projet_api_traitement_en_lot`, `projet_deploiement_quantification`, `projet_fil_rouge_mise_en_production` |

### Parcours 5, Industrialisation et terrain

| Séance | Chapitre | Projets du dépôt |
|---|---|---|
| 1 et 2 | 17, RAG en profondeur | `projet_droit_du_travail_chunking`, `projet_mutuelle_retrieval`, `projet_fil_rouge_copilote_agentique` |
| 3 | 21, LLMOps | `projet_detection_derive_donnees`, `projet_evaluation_qualite_reponses` |
| 4 et 5 | 23, applications sectorielles | `projet_education_decrochage`, `projet_transport_prevision_demande`, `projet_fil_rouge_prioriser_usages` |
| capstone | 24, projet capstone | dépôt distinct, non inclus dans le dépôt compagnon |

Les chapitres 18, 19 et 20 et leurs sept projets (`projet_assistant_administratif_outils`,
`projet_copilote_agricole_planification`, `projet_logistique_react`,
`projet_support_graphe_etats`, `projet_fil_rouge_agent_langgraph_mcp`,
`projet_commerce_orchestrateur`, `projet_approvisionnement_appel_offres`,
`projet_fil_rouge_orchestration_agents`) ne sont pas portés : le parcours « IA agentique » les
couvre plus largement. Ils restent disponibles dans le dépôt pour qui veut les lire.

## Ce qu'il faut développer avant d'écrire

1. **Le support des blocs dans l'application.** Aujourd'hui `data/` ne connaît que `parcours/`,
   et aucun code ne touche `LMS Program`. Il faut : un fichier de description de bloc en YAML,
   l'objet de domaine correspondant, sa lecture validée, le dépôt Frappe qui le crée et le met à
   jour sans perdre les membres déjà inscrits, l'ordre imposé, et la visibilité ainsi que le
   tarif au niveau du bloc si le cursus se vend en plus des parcours à l'unité. Tests d'abord.
2. **Les réglages propres à chaque parcours**, déjà prévus pour le parcours Python : délai des
   exercices, tentatives, score minimal. Le bloc en a besoin pour que chaque parcours garde son
   rythme.
3. **La construction des archives depuis un second dépôt.** Le constructeur actuel extrait les
   fichiers des blocs de code du parcours. Ici, les projets existent déjà sur le disque : il faut
   une seconde source, qui empaquette un dossier de projet du dépôt compagnon avec son fichier
   d'explication et ses tests, de façon déterministe, et qui échoue si le projet a bougé.

## Ce qu'il faut produire par séance

- le texte du chapitre, découpé en sections, avec ses exécutions à la main en tableaux ;
- les blocs de code, titrés par le fichier réel du projet, repris du dépôt sans retouche, pour
  que le téléchargement et le cours ne divergent jamais ;
- une archive du ou des projets de la séance ;
- cinq questions de quiz, les exercices du livre en travail guidé, leur corrigé, le livrable ;
- les figures : les schémas du livre sont à refaire en SVG construits par le dépôt, comme ceux
  du parcours agentique, et une photographie d'ouverture par séance.

## Risques et points de vigilance

- **Le volume.** 24 séances à convertir, soit l'équivalent de plus d'un parcours agentique. Le
  découpage en cinq parcours permet de livrer et de vendre le premier sans attendre les autres.
- **La dérive entre le livre, le dépôt et le cours.** Un test doit vérifier que chaque bloc de
  code d'une séance est identique au fichier du dépôt compagnon dont il porte le nom.
- **Les données publiques.** Les chargeurs scikit-learn et OpenML passent par le réseau au
  premier appel. Le cours doit dire comment amorcer le cache, et le repli synthétique doit rester
  visiblement étiqueté, pour qu'un apprenant ne prenne jamais un résultat de repli pour un
  résultat réel.
- **Le niveau d'entrée.** Le parcours 1 suppose de savoir lire du Python. Le parcours
  « Bases de Python » en cours de conception est le prérequis naturel, et devrait être annoncé
  comme tel sur la fiche du bloc.
