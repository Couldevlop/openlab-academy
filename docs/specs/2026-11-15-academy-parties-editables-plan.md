# Chaque partie d'une séance dans son propre éditeur — plan d'implémentation

> Exécution : une tâche à la fois, test rouge avant le code, un commit par tâche.

**But** : rendre chaque rubrique d'une séance autonome. L'administrateur ouvre une partie, la retouche dans un
éditeur riche déjà rempli, enregistre, et la leçon change pour l'apprenant sans republier le parcours et sans
toucher aux autres parties. Le fichier de parcours ne sert plus qu'au premier remplissage et à la remise à
zéro d'une partie jamais retouchée.

**Arbitrages retenus** (validés) : édition dans le formulaire Frappe desk d'un doctype dédié ; grain = toutes
les rubriques de la séance (contenu du module, chaque section de cours, travaux pratiques, livrable, exercices,
mise en situation ; pour la leçon de projet : contexte, guide, objectifs, fonctionnalités, stack, critères,
exigences, livrables, barème).

**Pourquoi pas une leçon par partie** : Frappe LMS n'a que deux niveaux, chapitre > leçon, déjà pris par
chapitre > séance. Découper en leçons casserait la progression séquentielle et le suivi d'avancement.

## Modèle

Doctype `Partie Lecon OpenLab`, une ligne par rubrique :

| champ | rôle |
|---|---|
| `lecon` | Link `Course Lesson` |
| `cle` | identité stable de la rubrique dans la leçon (`contenu`, `section-3`, `tp`, `livrable`…) |
| `rang` | ordre de lecture |
| `titre` | intitulé rendu en en-tête, vide si la rubrique n'en porte pas |
| `contenu` | Text Editor : le corps, en HTML, pré-rempli à la publication |
| `blocs` | JSON en lecture seule : les blocs EditorJS issus du fichier |
| `contenu_modifie_en_ligne` | Check : cette partie a été retouchée dans l'application |

**Deux représentations, jamais d'aller-retour destructeur** : tant qu'une partie n'est pas retouchée,
l'assemblage de la leçon utilise `blocs` (fidélité exacte : langage d'un extrait, légende et cadre d'une
figure, en-têtes d'un tableau, blocs `quiz` et `assignment`). Dès qu'elle est retouchée, l'assemblage convertit
`contenu`. La conversion n'est donc nécessaire que dans le sens HTML → blocs ; `blocs` → HTML ne sert qu'au
pré-remplissage de l'éditeur.

**Structure contre texte** : les blocs qui citent un exercice (`quiz`, `assignment`) et le lien d'archive
restent produits par la publication, dans leur rubrique. Une retouche porte sur le texte, jamais sur le
câblage des exercices, que la republication recrée.

**Précédence** : une leçon retouchée en entier dans l'éditeur du LMS (drapeau porté par `Course Lesson`,
mécanisme actuel de `retouches_frappe`) n'est plus assemblée depuis ses parties. Le drapeau de la leçon gagne ;
décoché, les parties reprennent la main.

## Lots

### Lot 1 — rendu par rubrique
`infrastructure/editorjs.py` : `rubriques_module(...)` et `rubriques_projet(...)` rendent une liste de
`Rubrique(cle, titre, blocs)`. `lecon_module` / `lecon_projet` deviennent l'assemblage de ces rubriques.
Aucun changement de sortie : les tests de rendu existants passent inchangés.

### Lot 2 — conversion HTML
`infrastructure/html_blocs.py` : `vers_html(blocs)` et `vers_blocs(html)`.
Liste blanche de balises (`h2`-`h4`, `p`, `ul`/`ol`, `table`, `pre`/`code`, `img`, `b`, `i`, `a`), adresses de
médias contrôlées comme aujourd'hui (fichiers privés du site seuls), tout le reste écarté. Tests : table,
code, liste imbriquée, image, injection (`<script>`, `javascript:`, `onerror`), aller-retour stable.

### Lot 3 — dépôt des parties
`openlab_academy/doctype/partie_lecon_openlab/` et `infrastructure/parties_frappe.py` :
`ecrire(lecon, rubriques)`, `assembler(lecon)`, `relever(cours)`, `reconduire(cours, relevees)`.
Appariement d'une republication : (titre de la leçon, `cle`). Droits : System Manager et Course Creator.

### Lot 4 — publication
`depot_frappe._lecon_module` / `_lecon_projet` écrivent les parties puis assemblent la leçon.
La republication conserve les parties retouchées, remplace les autres, et respecte la précédence du drapeau
de leçon.

### Lot 5 — édition en ligne
Hook `on_update` de `Partie Lecon OpenLab` : marque la partie et réassemble la leçon dans le contexte
`retouches_frappe.publication()`, pour que l'écriture de la leçon ne la marque pas elle-même.
Vue liste : `lecon`, `rang`, `titre`, `contenu_modifie_en_ligne`, triée par leçon puis rang.

### Lot 6 — parcours déjà publiés
`after_migrate` : crée les parties manquantes des leçons existantes depuis le fichier de parcours, sans
toucher à une leçon déjà retouchée en entier.

### Lot 7 — recette et documentation
Recette navigateur : retoucher une partie, vérifier la leçon côté apprenant, republier le parcours, vérifier
que la retouche survit et que les autres parties reviennent du fichier. Documentation dans
`docs/specs/2026-10-15-academy-socle-design.md`.

## Sécurité

- Tout contenu de partie est échappé ou passé par la liste blanche avant rendu (OWASP A03).
- Adresses de médias : seuls les fichiers privés du site, comme pour les figures et archives actuelles.
- Écriture d'une partie réservée aux rôles d'édition de cours ; lecture par le rendu de leçon seul.
- Le `blocs` en lecture seule interdit d'injecter un bloc arbitraire par le formulaire.
