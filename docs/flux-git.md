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
   `develop` → `main` n'y ouvre aucun run : elle porte l'arbre que la CI de `develop` vient de valider.
   Jobs :
   - `frontend` : ESLint, Prettier, `vue-tsc`, tests avec seuils de couverture, build ;
   - `backend` : site Frappe réel sur les références épinglées, suite complète, **couverture ≥ 99 %** ;
   - `securite` : Semgrep (Python, JavaScript, secrets), Gitleaks sur l'historique — version figée, avec une
     exception à deux conditions pour les identifiants inventés des tests de canaux (`.gitleaks.toml`) — et
     `.github/scripts/audit_front.py` sur le front — mêmes exigences que
     `npm audit --omit=dev --audit-level=high`, à ceci près qu'un avis de sévérité haute sans correctif
     publié en amont passe s'il est inscrit, justifié et daté dans `exceptions-audit.json`, et qu'il échoue
     de nouveau dès qu'un correctif sort ou que la date de revue tombe. Le backend n'a aucune dépendance Python propre.
     Restent quatre avis **modérés** non bloquants, hérités de `frappe-ui` (XSS d'Apache ECharts) : aucun
     correctif n'existe sans sortir de la version de `frappe-ui` qu'impose le LMS ;
1bis. **`gardien.yml`** — sur toute PR **humaine** vers `main` : refuse une source autre que `develop`.
   Sur la PR que la promotion ouvre avec GITHUB_TOKEN, il ne contrôle rien : GitHub crée une exécution
   qu'il ne distribue jamais, qui conclut « failure » sans aucun job. La croix rouge qui en découle ne dit
   rien de l'état du code. Pour cette PR-là, c'est `promotion.yml` qui relit la branche source avant de
   fusionner.
2. **`promotion.yml`** — déclenché par la **réussite de la CI sur `develop`**, pas par le push : il vérifie que
   `develop` n'a pas bougé depuis la validation, ouvre ou met à jour la PR « Promotion vers main », puis la
   fusionne. Le commit promu est exactement celui que la CI vient de valider ; aucun test n'est court-circuité.
   L'auto-merge de GitHub n'est pas utilisable ici, et pas pour la raison longtemps avancée : il exige des
   contrôles **requis** sur `main`, or aucune exécution de CI n'existe sur une PR `develop → main` (voir
   ci-dessous). Un workflow `workflow_run` n'étant pris en compte que dans sa version présente sur `main`,
   la **première** promotion se lance à la main (`workflow_dispatch`).
3. **`release.yml`** — appelé par la promotion (`workflow_call`), et déclenché par un push sur `main`
   quand la fusion a été faite à la main : étiquette `v<version>` lue dans
   `openlab_academy/__init__.py` (`__version__`) et publie la release, puis **réaligne `develop` sur `main`**,
   sans quoi les commits de fusion feraient diverger les deux branches. La promotion venant de fusionner
   `develop` dans `main`, `main` descend de `develop` : le retour est une **avance rapide**, poussée
   directement, sans PR. Si `develop` a avancé entre-temps, le réalignement est laissé à la livraison
   suivante (avertissement) plutôt que forcé.

### Ce que GITHUB_TOKEN ne déclenche pas

Un push, ou une fusion, effectué avec `GITHUB_TOKEN` ne crée **aucun** événement de workflow : c'est le
garde-fou anti-récursion de GitHub. Deux conséquences, assumées :

- la fusion automatique dans `main` ne rejoue ni la CI de `main`, ni la release par l'événement `push` — d'où
  l'appel direct de `release.yml` par la promotion. L'arbre livré est celui que la CI de `develop` vient de
  valider, et la promotion vérifie que la branche n'a pas bougé entre-temps ;
- les contrôles d'une PR ouverte par Actions restent en attente d'approbation (`action_required`), ce qui
  s'affiche comme un échec. C'est pourquoi `ci.yml` n'écoute plus les PR vers `main` : la PR de promotion
  n'ouvre plus de run de CI, et `gardien.yml` ne vise que la PR humaine.

Deux artefacts rouges en découlaient, sans rapport avec le code livré :

- la PR de réalignement `main` → `develop`, ouverte par Actions, déclenchait un run de CI bloqué en
  `action_required`. **Supprimé** : le réalignement est désormais une avance rapide poussée directement ;
- la PR de promotion `develop` → `main` crée un run de `Gardien` que la fusion immédiate conclut sans
  qu'aucun job n'ait démarré — il s'affiche en échec. Le filtre `pull_request` de GitHub ne porte que sur
  la branche **cible**, et l'état `action_required` est décidé avant toute condition `if:` : ce run ne peut
  pas être évité tant que la promotion passe par une PR. **À ignorer** : le contrôle qui compte est celui de
  la CI de `develop`, sur le même commit.

Le déploiement n'est pas dans la chaîne : aucune cible de production n'est encore câblée pour l'Academy. La
livraison s'arrête à l'étiquette de version, qui désignera l'artefact à déployer.

## Protection de `main`

Le dépôt est **public** depuis le 19 novembre 2026 : la protection de branche et les rulesets y sont
désormais disponibles, après avoir été refusés tant qu'il était privé en plan gratuit (`403 — Upgrade to
GitHub Pro`). Un ruleset est en place sur `main` depuis le 20 novembre 2026 :

| règle | effet |
| --- | --- |
| `pull_request` | `main` ne se modifie que par une PR fusionnée ; méthode `merge` seule, **0 approbation requise** |
| `non_fast_forward` | aucune réécriture d'historique |
| `deletion` | la branche ne peut pas être supprimée |

Deux choix demandent une explication, parce que l'un et l'autre paraissent trop permissifs.

**Zéro approbation requise.** La promotion ouvre sa PR et la fusionne avec `GITHUB_TOKEN`. Exiger une
approbation la bloquerait à chaque livraison, et le robot ne peut pas s'approuver lui-même. La règle
garde donc ce qu'elle peut : rien n'entre dans `main` hors d'une PR, et rien n'y réécrit l'histoire.

**Aucun contrôle requis.** C'est le piège de ce dépôt, et il faut le nommer : `ci.yml` ne se déclenche
que sur les PR vers `develop` et sur les push de `develop` et de `main`. Une PR `develop → main`
**n'ouvre aucune exécution** — c'est voulu, elle porte l'arbre que la CI de `develop` vient de valider.
Rendre ces contrôles requis sur `main` bloquerait donc chaque promotion pour toujours, en attente de
contrôles qui ne viennent jamais. Les rendre requis demanderait de faire tourner la CI sur les PR vers
`main`, soit une exécution complète de plus par livraison sur un arbre déjà validé.

Aucun ruleset ne peut non plus porter la règle de flux : ses conditions portent sur la branche *cible*,
jamais sur la branche source d'une PR. La règle « `main` ne reçoit que des PR venues de `develop` »
reste donc portée par `gardien` pour la PR humaine et par `promotion.yml` pour la sienne.

## Garde-fous locaux

Un hook local complète le ruleset, à installer une fois par clone :

```
git config core.hooksPath .githooks
```

`.githooks/pre-push` refuse tout push direct sur `main` et `develop`. Le contournement
(`PUSH_DIRECT=1 git push …`) reste possible et assumé : le hook est dissuasif. Sur `main`, il ne l'est
plus seul — le ruleset refuse le push côté serveur, contournement compris. Sur `develop`, il l'est
encore : aucun ruleset n'y est posé, parce que `release.yml` y pousse directement le réalignement de
`main` (`git push origin HEAD:refs/heads/develop`), ce qu'une exigence de PR interdirait.

## Réglages du dépôt exigés par la chaîne

- **Allow GitHub Actions to create and approve pull requests** : activé, sinon `promotion.yml` ne peut pas
  ouvrir la PR.
- **Allow auto-merge** : refusé par GitHub sur ce dépôt (`allow_auto_merge` reste à `false` après appel de
  l'API) ; la promotion ne s'y appuie donc pas.
- **Automatically delete head branches** : **désactivé**, et à laisser ainsi. La promotion relit la
  branche source de sa propre PR (`gh pr view --json headRefName`) et refuserait de fusionner si
  GitHub l'avait supprimée entre-temps ; une branche effacée emporte aussi la seule trace permettant
  de rejouer un lot de tests à l'identique. Relevé le 20 novembre 2026 : `delete_branch_on_merge: false`.

### Analyse de sécurité

- **Secret scanning** et **push protection** : activés le 19 novembre 2026, gratuits depuis le passage
  en public, et sans aucune alerte rétroactive sur les 342 commits de l'historique.
- **Alertes de vulnérabilité** et **mises à jour de sécurité Dependabot** : activées le 20 novembre 2026
  (`PUT /vulnerability-alerts` et `PUT /automated-security-fixes` ; le champ équivalent de
  `security_and_analysis` ne suffit pas).
- **Motifs non fournisseurs** et **vérification de validité** : **à activer à la main** dans
  `Settings → Code security`. L'API répond 200 à
  `PATCH /repos/… {"security_and_analysis":{"secret_scanning_non_provider_patterns":{"status":"enabled"}}}`
  puis les relit `disabled`, en appel groupé comme un par un. Les motifs non fournisseurs lèveront des
  faux positifs sur les identifiants inventés pour les tests, déjà exceptés dans `.gitleaks.toml`.
