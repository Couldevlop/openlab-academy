# Parcours Ingénieur Cybersécurité I et II — proposition de programme

Édition du 24 octobre 2026 · statut : **proposition à valider** par l'équipe pédagogique avant remplissage des
modèles `docs/modeles/04-cybersecurite-i.modele.yaml` et `05-cybersecurite-ii.modele.yaml`.

## 1. Ce que font les meilleures formations

| Référence | Ce qu'on en retient |
|---|---|
| **Carnegie Mellon — MS Information Security (INI)** | Tronc en quatre blocs : systèmes, réseaux, sécurité (cours obligatoire *Introduction to Information Security* + un cours au choix : cryptographie appliquée, code sécurisé, sécurité réseau…), et **management du risque** (modélisation du risque cyber, politique de sécurité). La sécurité s'appuie sur des fondations systèmes et réseaux solides, et la gestion du risque est obligatoire. |
| **Georgia Tech — OMS Cybersecurity** | Socle commun (*Introduction to Information Security* + *Information Security Policies and Strategies*), puis spécialisation (sécurité de l'information, systèmes cyber-physiques, politique) et un **practicum** final. Technique et gouvernance vont ensemble, et le diplôme se termine par un projet réel. |
| **Royal Holloway — MSc Information Security** (accrédité GCHQ) | Cœur obligatoire : *Security Management* et *Cryptography and Security Mechanisms*, puis sécurité réseau et sécurité des systèmes, options (tests de sécurité, forensique) et un **projet de 60 crédits**. La cryptographie et le management de la sécurité forment le tronc commun. |
| **ANSSI — label SecNumedu / SecNumedu‑FC** | Une formation continue labellisée consacre **au moins 70 % de ses heures à la cybersécurité** et suit un référentiel reconnu par l'ANSSI (ou mène à une certification inscrite au Répertoire spécifique de France Compétences). C'est la cible de reconnaissance pour notre marché francophone. |
| **ENISA — European Cybersecurity Skills Framework (ECSF)** | 12 profils métiers, chacun avec ses missions, tâches, compétences et connaissances. On cale chaque parcours sur des profils précis plutôt que sur une liste d'outils. |
| **NIST — NICE Framework (SP 800‑181) et CyBOK** | Vocabulaire commun des tâches et des connaissances ; sert à vérifier qu'aucun domaine du corpus n'est oublié (droit, facteurs humains, réseaux, logiciels, gestion des opérations). |

**Points communs** aux programmes réputés, repris ici :
1. des fondations systèmes, réseaux et cryptographie avant tout outil ;
2. la défense (détection, réponse) au même niveau que l'offensif ;
3. la gouvernance, le risque et le droit, traités comme un bloc à part entière ;
4. un projet final réel présenté devant un jury ;
5. l'offensif uniquement dans un cadre légal et autorisé.

## 2. Ce qui change par rapport au catalogue actuel

Le catalogue d'octobre liste 12 modules très orientés outils (Nmap, Wireshark, Burp Suite…), avec l'offensif dès la
semaine 4. Les programmes de référence enseignent les **notions** (l'outil devient un moyen de pratique) et placent la
gouvernance, la cryptographie et la sécurité applicative au cœur du programme. Proposition :

- **Parcours I « Fondations et défense »** : le métier d'analyste SOC / technicien sécurité, employable seul.
- **Parcours II « Sécurité offensive encadrée, cloud et gouvernance »** : testeur d'intrusion, architecte, futur RSSI.
- Les 12 modules du catalogue sont tous conservés, regroupés ou renommés en notions (correspondance au § 6).
- Calibrage inchangé (modèle en vigueur) : par parcours, 12 modules × 8 h + 10 projets × 15 h + capstone 60 h =
  **306 h**, soit 26 semaines en rythme standard (12 h) ; I + II ≈ un an.
- Contexte ivoirien et ouest-africain dans chaque projet : mobile money, banques UEMOA, opérateurs télécoms,
  administrations, PME.

## 3. Parcours Ingénieur Cybersécurité I — Fondations et défense

**Profils ECSF visés :** *Cyber Incident Responder* (niveau junior, analyste SOC), *Cybersecurity Implementer*.
**Prérequis :** aisance avec un ordinateur et la ligne de commande (chapitre 0 et Développeur Python recommandés).
**Préparation certifiante (en option, hors parcours) :** ISC2 CC, CompTIA Security+, puis CySA+.

### Bloc 1 — Fondations (S1–S4)

| # | Module | Notions | Livrable |
|---|---|---|---|
| 01 | Principes de sécurité et cadre légal | Confidentialité, intégrité, disponibilité ; menaces, vulnérabilités, risque ; modèle de menace ; éthique professionnelle ; droit ivoirien (loi n° 2013‑451 sur la cybercriminalité, loi n° 2013‑450 sur les données personnelles, rôle de l'ARTCI et du CI‑CERT), Convention de Malabo | Modèle de menace d'une agence de mobile money, avec obligations légales |
| 02 | Réseaux TCP/IP pour la sécurité | OSI et TCP/IP, adressage, routage, DNS, HTTP(S), TLS ; capture et lecture de trafic (Wireshark) ; segmentation | Schéma réseau d'une PME avec plan de segmentation justifié |
| 03 | Linux : administration et durcissement | Fichiers, droits, processus, services, journaux, SSH, pare-feu hôte ; référentiels CIS | Serveur durci et checklist vérifiable |
| 04 | Windows et Active Directory : les bases | Comptes, groupes, GPO, Kerberos et NTLM vus du défenseur, journaux d'événements, modèle à niveaux (tiering) | Revue de configuration d'un domaine de lab, écarts classés par gravité |

### Bloc 2 — Protection (S5–S8)

| # | Module | Notions | Livrable |
|---|---|---|---|
| 05 | Cryptographie appliquée | Chiffrement symétrique et asymétrique, hachage, signatures, PKI et certificats, TLS, gestion des clés et des secrets ; erreurs courantes | Audit de la configuration TLS et des certificats d'un service de lab |
| 06 | Identités et accès | Authentification forte, SSO (OIDC, SAML), moindre privilège, comptes à privilèges, revue des accès, cycle de vie des comptes | Politique d'accès et matrice des droits d'une PME |
| 07 | Sécurité réseau défensive | Pare-feu, segmentation, VPN, proxy, détection d'intrusion (Suricata), découverte autorisée du réseau (Nmap) dans le lab | Règles de filtrage et de détection testées sur le lab |
| 08 | Automatiser la sécurité (Python, Bash) | Scripts d'audit, analyse de journaux, appels d'API, outillage du défenseur | Outil d'analyse des connexions suspectes, testé |

### Bloc 3 — Détection et réponse (S9–S12)

| # | Module | Notions | Livrable |
|---|---|---|---|
| 09 | Journalisation et SIEM | Sources de journaux, collecte, normalisation, rétention ; SIEM open source auto-hébergé (Wazuh / Elastic), choix cohérent avec la souveraineté | Chaîne de collecte d'un SI de lab, tableau de bord |
| 10 | Détection et renseignement sur la menace | MITRE ATT&CK, règles de corrélation (Sigma), indicateurs de compromission, réduction des faux positifs | 10 règles de détection mappées sur ATT&CK, avec jeux d'essai |
| 11 | Réponse à incident et forensique de base | Cycle NIST SP 800‑61 (préparation, détection, confinement, éradication, retour à la normale, retour d'expérience), collecte de preuves, chronologie, communication de crise, notification à l'ARTCI | Playbook d'incident et exercice sur table |
| 12 | Gestion des vulnérabilités | Inventaire, scan autorisé (OpenVAS), score CVSS et EPSS, priorisation, correctifs, mesure | Plan de remédiation priorisé sur un parc de lab |

### Portfolio (10 projets de 15 h) et capstone

| Après | Projet | Niveau |
|---|---|---|
| 01 | Analyse de risques d'une agence de transfert d'argent (Abidjan) | guidé |
| 02 | Cartographie et segmentation du réseau d'une clinique | guidé |
| 03 | Durcissement du serveur web d'une mairie, avant/après mesuré | guidé |
| 05 | Mise en place d'une PKI interne pour une PME | semi-guidé |
| 06 | Authentification forte et revue des accès d'une coopérative agricole | semi-guidé |
| 07 | Détection d'intrusion réseau sur un lab d'opérateur télécom | semi-guidé |
| 08 | Outil de détection de fraude par connexion anormale (journaux mobile money) | semi-guidé |
| 09 | SIEM d'un cabinet comptable : collecte et tableau de bord | autonome |
| 10 | Chasse aux menaces dans des journaux fournis (scénario de rançongiciel) | autonome |
| 11 | Réponse à une compromission de messagerie, rapport et chronologie | autonome |

**Capstone I (60 h) — « Le SOC d'une fintech ivoirienne ».** Sur une infrastructure de lab fournie : collecte des
journaux, 10 règles de détection, traitement d'un incident simulé de bout en bout, plan de remédiation, puis
soutenance devant jury (synthèse pour la direction et détail technique).

## 4. Parcours Ingénieur Cybersécurité II — Sécurité offensive encadrée, cloud et gouvernance

**Profils ECSF visés :** *Penetration Tester*, *Cybersecurity Architect*, *Cyber Risk Manager* (vers *CISO*).
**Prérequis :** parcours I ou expérience équivalente validée par test d'entrée.
**Préparation certifiante (en option) :** CompTIA PenTest+ ou eJPT puis OSCP, ISO/IEC 27001 Lead Implementer, CCSK.

**Cadre légal permanent :** toute pratique offensive se fait sur les labs fournis, ou sur des systèmes couverts par une
autorisation écrite et une convention d'audit signée. Chaque technique offensive est enseignée **avec sa détection et
sa remédiation**.

### Bloc 1 — Sécurité applicative (S1–S4)

| # | Module | Notions | Livrable |
|---|---|---|---|
| 01 | Développement sécurisé | OWASP Top 10 et ASVS, modélisation des menaces (STRIDE), validation des entrées, gestion des sessions, revue de code | Revue de sécurité d'une application de lab, corrections proposées |
| 02 | Sécurité des API et du mobile | OWASP API Security Top 10, MASVS, jetons et autorisations, cas des applications de mobile money | Audit d'une API de paiement de lab, avec remédiations |
| 03 | Tests d'intrusion web | Méthode de test, proxy d'interception (Burp Suite), authentification et contrôle d'accès, preuves, remédiation | Rapport de test d'une application de lab |
| 04 | DevSecOps | Analyse statique et dynamique, dépendances et chaîne d'approvisionnement, secrets, durcissement de la CI | Pipeline CI avec contrôles de sécurité bloquants |

### Bloc 2 — Évaluation offensive encadrée (S5–S8)

| # | Module | Notions | Livrable |
|---|---|---|---|
| 05 | Méthodologie de l'audit | PTES et OSSTMM, cadrage, règles d'engagement, convention d'audit, gestion des preuves, déontologie | Convention d'audit et plan de test d'un client fictif |
| 06 | Audit d'infrastructure et d'Active Directory | Reconnaissance autorisée, chemins d'attaque AD vus par l'auditeur, élévation de privilèges en lab, durcissement correspondant | Rapport d'audit d'un domaine de lab, avec plan de durcissement |
| 07 | Purple team et émulation d'adversaire | Scénarios ATT&CK, mesure de la couverture de détection, amélioration continue avec l'équipe défense | Matrice de couverture avant/après sur le lab |
| 08 | Rapport et accompagnement de la remédiation | Synthèse pour la direction, détail technique, notation des risques, suivi des corrections, contre-audit | Rapport professionnel complet et plan de suivi |

### Bloc 3 — Cloud, architecture et gouvernance (S9–S12)

| # | Module | Notions | Livrable |
|---|---|---|---|
| 09 | Sécurité du cloud et des conteneurs | Responsabilité partagée, IAM cloud, réseau, secrets, Kubernetes, référentiels CIS, posture (CSPM) | Audit de configuration d'un environnement cloud et Kubernetes de lab |
| 10 | Architecture de sécurité et zero trust | Défense en profondeur, NIST SP 800‑207, segmentation, accès conditionnel, sauvegardes et résilience | Dossier d'architecture cible d'une banque régionale |
| 11 | Gouvernance, risque et conformité | ISO/IEC 27001 et 27005, EBIOS Risk Manager, NIST CSF 2.0, exigences sectorielles (banques UEMOA, opérateurs), protection des données | Analyse de risques EBIOS RM et déclaration d'applicabilité |
| 12 | Sécurité des systèmes d'IA | OWASP Top 10 pour les applications LLM, injection d'instructions, fuite de données, sécurisation d'un assistant interne (lien avec le parcours AI Engineer) | Revue de sécurité d'un assistant IA de lab, mesures appliquées |

### Portfolio (10 projets de 15 h) et capstone

| Après | Projet | Niveau |
|---|---|---|
| 01 | Revue de code sécurisée d'un portail de e-administration | guidé |
| 02 | Audit d'une API de paiement mobile, avec correctifs | guidé |
| 03 | Test d'intrusion web d'une boutique en ligne de lab | guidé |
| 04 | Chaîne CI sécurisée pour une startup ivoirienne | semi-guidé |
| 05 | Réponse à un appel d'offres d'audit : convention et méthodologie | semi-guidé |
| 06 | Audit d'un Active Directory de lab et plan de durcissement | semi-guidé |
| 07 | Exercice purple team : trois scénarios ATT&CK et mesure de détection | semi-guidé |
| 09 | Audit d'un cluster Kubernetes de lab | autonome |
| 10 | Architecture zero trust d'une microfinance | autonome |
| 11 | Dossier de conformité ISO 27001 d'un opérateur de paiement | autonome |

**Capstone II (60 h) — « Audit et transformation d'un établissement financier ».** Sur une infrastructure de lab :
audit autorisé (application, API, AD, cloud), détection des scénarios joués, plan de remédiation chiffré, analyse de
risques et feuille de route pour le comité de direction, soutenance devant jury.

## 5. Évaluation et reconnaissance

- Barème inchangé : livrables hebdomadaires 20 %, portfolio 40 %, capstone 40 %. Grilles et chaîne d'évaluation
  existantes : contrôles, pré-correction IA, pairs, formateur.
- Jury du capstone avec au moins un professionnel en poste (RSSI, SOC, cabinet d'audit).
- Viser le label **SecNumedu‑FC** : 100 % des heures en cybersécurité (au-delà des 70 % exigés). Il reste à aligner
  le parcours sur un référentiel reconnu par l'ANSSI, ou à faire inscrire la certification OpenLab au Répertoire
  spécifique (démarche à instruire).
- Correspondance ECSF publiée dans la fiche de chaque parcours, pour la lisibilité auprès des recruteurs, notamment
  en nearshore vers Sophia Antipolis.

## 6. Correspondance avec le catalogue actuel

| Catalogue (oct. 2026) | Proposition |
|---|---|
| 01 Réseaux TCP/IP | I‑02 |
| 02 Linux | I‑03 |
| 03 Python sécurité | I‑08 |
| 04 OWASP Top 10 | II‑01 et II‑03 |
| 05 Nmap | I‑07 et I‑12 (découverte et scan autorisés) |
| 06 Wireshark | I‑02 et I‑07 |
| 07 Burp Suite | II‑03 |
| 08 Pentest | II‑05, II‑06 et II‑08 |
| 09 Active Directory | I‑04 (défense) et II‑06 (audit) |
| 10 SIEM | I‑09 et I‑10 (Wazuh / Elastic auto-hébergés plutôt que Splunk, licence et souveraineté) |
| 11 Cloud Security | II‑09 |
| 12 Réponse à incident | I‑11 |
| *ajouts* | Principes et droit (I‑01), cryptographie (I‑05), identités (I‑06), vulnérabilités (I‑12), API et mobile (II‑02), DevSecOps (II‑04), purple team (II‑07), architecture (II‑10), GRC (II‑11), sécurité de l'IA (II‑12) |

## 7. Suite

1. Validation de cette proposition (structure, modules, projets) par l'équipe pédagogique.
2. Rédaction du contenu détaillé par l'équipe pédagogique (énoncés, labs, quiz, mises en situation) dans les deux
   modèles, puis publication : `bench --site <site> execute openlab_academy.entrypoints.seed.run`.
3. Mise à jour du catalogue public et de la fiche commerciale (profils ECSF, préparation certifiante).

## Sources

- [CMU INI — MS Information Security, curriculum MS36](https://www.cmu.edu/ini/academics/msis/curriculum_ms36.html)
- [Georgia Tech — Online Master of Science in Cybersecurity](https://pe.gatech.edu/degrees/cybersecurity)
- [Royal Holloway — MSc Information Security (fiche programme)](https://venue.royalholloway.ac.uk/media/18413/information-security-msc-1221.pdf)
- [ANSSI — Labellisation SecNumedu‑FC](https://cyber.gouv.fr/offre-de-service/formations-entrainement-et-decouverte-des-metiers/formations/formation-labellisees-par-lanssi/labellisation-secnumedu-fc/)
- [ENISA — European Cybersecurity Skills Framework](https://www.enisa.europa.eu/topics/cybersecurity-education/european-cybersecurity-skills-framework)
