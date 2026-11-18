# Contenu riche du parcours IA agentique

Objectif : porter les huit séances au niveau d'un cours professionnel, avec schémas, tableaux, graphes et
extraits de code servis dans la leçon, puis livrer le plan de tournage des capsules vidéo et l'outillage
gratuit qui permet de les produire.

## Principes retenus

**Les illustrations sont du code, pas des pièces jointes.** Un schéma se décrit dans le YAML du parcours et
un script du dépôt le rend en SVG. La conséquence tient en trois points : le rendu est reproductible octet
pour octet, une correction se lit dans un diff, et rien ne dépend d'un outil extérieur ni d'un compte. C'est
la discipline déjà appliquée à l'archive du socle.

**Les médias suivent le contrôle d'accès des leçons.** Les SVG sont déposés en fichiers privés et servis par
`serve_resource`, comme l'archive : un visiteur hors inscription reçoit un refus, pas une image.

**Aucune trace de rédaction automatique.** Le tiret cadratin incise disparaît du contenu pédagogique au
profit de la ponctuation ordinaire : deux points, virgule, point-virgule, parenthèse, ou deux phrases. Un
test du dépôt refuse sa réapparition dans les données de parcours.

## Lots

### T1 — Nettoyage typographique

- [ ] Réécrire les incises au tiret cadratin des sept fichiers de parcours et des titres générés
      (`Livrable NN — titre`, `Capstone — titre`, `Promo 1 — parcours`, `Format : ~N h — 40 % théorie`).
- [ ] Test rouge d'abord : un test parcourt `data/parcours/*.yaml` et le rendu des leçons, et échoue sur
      toute occurrence du caractère.

### T2 — Blocs riches dans le rendu

- [ ] Étendre `infrastructure/editorjs.py` aux blocs que le LMS sait rendre : `table`, `image`, `codeBox`.
- [ ] Étendre le schéma YAML : `tableaux`, `schemas`, `code` au niveau du module, validés par
      `infrastructure/yaml_source.py` avec les mêmes refus explicites que l'existant.
- [ ] Échappement systématique, y compris dans les cellules de tableau et les légendes : aucun HTML actif.
- [ ] TDD sur chaque bloc, plus un test d'injection par bloc.

### T3 — Schémas et graphes

- [ ] `docs/Ressources/construire_schemas.py` : rendu SVG déterministe (pas d'horodatage, identifiants
      stables, ordre fixe), une fonction par famille de figure.
- [ ] Familles nécessaires au parcours : boucle d'agent, cycle d'un appel d'outil, comparaison des quatre
      familles de systèmes, machine à états avec reprise, topologies multi-agents, chaîne MCP, échelle de
      risque des actions, barres de coût et de latence par nombre d'étapes.
- [ ] Palette et règles de lisibilité tirées de la compétence `dataviz`, déclinée en clair et en sombre.
- [ ] Publication des SVG en fichiers privés par `infrastructure/ressources_frappe.py`, comme l'archive.

### T4 — Rédaction enrichie des huit séances

- [ ] Pour chaque séance : un schéma de tête, au moins un tableau de décision ou de comparaison, un extrait
      de code commenté, et les graphes là où un chiffre vaut mieux qu'une phrase.
- [ ] Le contenu pédagogique reste en français et hors `_()`.

### T5 — Capsules vidéo

- [ ] `docs/Ressources/plan-tournage-ia-agentique.md` : par séance, les capsules à tourner, leur durée,
      leur intention, ce qui est à l'écran et le texte parlé.
- [ ] Outillage gratuit de capture, de montage, de son et de sous-titrage, avec ce que chaque outil coûte
      en apprentissage et ses limites réelles.

### T6 — Recette

- [ ] Parcours des huit leçons dans le navigateur, inscrit et hors inscription.
- [ ] Affichage 375 px sur les leçons les plus chargées.
