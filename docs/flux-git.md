# Flux Git et chaîne d'intégration

## Les deux branches durables

| Branche | Rôle | Alimentée par |
|---|---|---|
| `main` | état livré : rien n'y entre qui n'ait passé tests unitaires, tests d'intégration sur un site Frappe réel, barrière de couverture de 99 %, analyse de sécurité et garde-fou d'architecture | uniquement des PR venues de `develop`, fusionnées automatiquement quand tous les contrôles sont verts |
| `develop` | intégration courante | PR des branches de travail ; réalignée sur `main` après chaque livraison |

Toute branche de travail **part de `develop`** et y retourne par PR :

```
git switch develop && git pull
git switch -c feat/mon-sujet
```

## Chaîne d'intégration

1. **`ci.yml`** — sur les PR vers `develop` et sur les push de `develop` et de `main`. Une PR
   `develop` → `main` ne rejoue pas les jobs lourds : elle porte l'arbre que la CI de `develop` vient de
   valider, seul le gardien de flux s'y exécute, et la fusion dans `main` déclenche sa propre CI
   complète. Jobs :
   - `frontend` : ESLint, Prettier, `vue-tsc`, tests avec seuils de couverture, build ;
   - `backend` : site Frappe réel sur les références épinglées, suite complète, **couverture ≥ 99 %** ;
   - `securite` : Semgrep (Python, JavaScript, secrets), Gitleaks sur l'historique — version figée, avec une
     exception à deux conditions pour les identifiants inventés des tests de canaux (`.gitleaks.toml`) — et
     `npm audit --omit=dev --audit-level=high` sur le front. Le backend n'a aucune dépendance Python propre.
     Restent quatre avis **modérés** non bloquants, hérités de `frappe-ui` (XSS d'Apache ECharts) : aucun
     correctif n'existe sans sortir de la version de `frappe-ui` qu'impose le LMS ;
   - `gardien` : une PR vers `main` qui ne vient pas de `develop` est refusée.
2. **`promotion.yml`** — déclenché par la **réussite de la CI sur `develop`**, pas par le push : il vérifie que
   `develop` n'a pas bougé depuis la validation, ouvre ou met à jour la PR « Promotion vers main », puis la
   fusionne. Le commit promu est exactement celui que la CI vient de valider ; aucun test n'est court-circuité.
   L'auto-merge de GitHub n'est pas utilisable ici : il exige des contrôles requis, donc une protection de
   branche, indisponible sur ce plan. Un workflow `workflow_run` n'étant pris en compte que dans sa version
   présente sur `main`, la **première** promotion se lance à la main (`workflow_dispatch`).
3. **`release.yml`** — appelé par la promotion (`workflow_call`), et déclenché par un push sur `main`
   quand la fusion a été faite à la main : étiquette `v<version>` lue dans
   `openlab_academy/__init__.py` (`__version__`) et publie la release, puis ouvre la PR de **réalignement de
   `develop` sur `main`**, sans laquelle les commits de fusion feraient diverger les deux branches.

### Ce que GITHUB_TOKEN ne déclenche pas

Un push, ou une fusion, effectué avec `GITHUB_TOKEN` ne crée **aucun** événement de workflow : c'est le
garde-fou anti-récursion de GitHub. Deux conséquences, assumées :

- la fusion automatique dans `main` ne rejoue ni la CI de `main`, ni la release par l'événement `push` — d'où
  l'appel direct de `release.yml` par la promotion. L'arbre livré est celui que la CI de `develop` vient de
  valider, et la promotion vérifie que la branche n'a pas bougé entre-temps ;
- les contrôles de la PR de promotion, ouverte par Actions, restent en attente d'approbation
  (`action_required`). Le job `gardien` garde donc son sens pour une PR **humaine** vers `main`.

Le déploiement n'est pas dans la chaîne : aucune cible de production n'est encore câblée pour l'Academy. La
livraison s'arrête à l'étiquette de version, qui désignera l'artefact à déployer.

## Garde-fous locaux

GitHub **n'autorise pas** la protection de branche ni les rulesets sur un dépôt privé en plan gratuit
(réponse `403 — Upgrade to GitHub Pro`). La règle « `main` ne reçoit que des PR » repose donc sur le job
`gardien` et sur un hook local à installer une fois par clone :

```
git config core.hooksPath .githooks
```

`.githooks/pre-push` refuse tout push direct sur `main` et `develop`. Un contournement reste possible et
assumé (`PUSH_DIRECT=1 git push …`) : sans plan payant, la règle est dissuasive, pas infranchissable.

## Réglages du dépôt exigés par la chaîne

- **Allow GitHub Actions to create and approve pull requests** : activé, sinon `promotion.yml` ne peut pas
  ouvrir la PR.
- **Allow auto-merge** : refusé par GitHub sur ce dépôt (`allow_auto_merge` reste à `false` après appel de
  l'API) ; la promotion ne s'y appuie donc pas.
- **Automatically delete head branches** : activé, confort seulement.
