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

1. **`ci.yml`** — sur toute PR vers `develop` ou `main`, et sur push de ces branches :
   - `frontend` : ESLint, Prettier, `vue-tsc`, tests avec seuils de couverture, build ;
   - `backend` : site Frappe réel sur les références épinglées, suite complète, **couverture ≥ 99 %** ;
   - `securite` : Semgrep (Python, JavaScript, secrets), Gitleaks sur l'historique, `npm audit` des
     dépendances de production du front. Le backend n'a aucune dépendance Python propre ;
   - `gardien` : une PR vers `main` qui ne vient pas de `develop` est refusée.
2. **`promotion.yml`** — à chaque push sur `develop` : ouvre, ou met à jour, la PR « Promotion vers main » et
   active l'auto-merge. GitHub ne fusionne que lorsque les contrôles du point 1 sont tous verts ; aucun test
   n'est court-circuité.
3. **`release.yml`** — après la fusion dans `main` : étiquette `v<version>` lue dans
   `openlab_academy/__init__.py` (`__version__`) et publie la release, puis ouvre la PR de **réalignement de
   `develop` sur `main`**, sans laquelle les commits de fusion feraient diverger les deux branches.

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

- **Allow auto-merge** : activé, sinon la PR de promotion reste ouverte sans fusionner.
- **Allow GitHub Actions to create and approve pull requests** : activé, sinon `promotion.yml` ne peut pas
  ouvrir la PR.
- **Automatically delete head branches** : activé, confort seulement.
