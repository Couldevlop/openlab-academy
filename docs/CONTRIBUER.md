# Contribuer à Openlab Academy

Point d'entrée du dépôt : ce qu'il faut savoir avant de toucher au projet. Le flux Git
et la chaîne d'intégration ont leur propre page, [flux-git.md](flux-git.md).

## Ce que contient le dépôt

| Chemin | Contenu |
| --- | --- |
| `apps/openlab_academy/openlab_academy/` | l'application Frappe : `domain/` (règles métier pures, qui ne connaissent pas Frappe), `application/` (cas d'usage), `entrypoints/` (points d'entrée appelés par Frappe), `infrastructure/` (SMS, WhatsApp, courriel, CinetPay), `www/` et `templates/` (pages servies), `data/parcours/*.yaml` (les parcours, source de vérité), `translations/`, `patches/`, `tests/` |
| `apps/openlab_academy/frontend/` | l'espace d'évaluation, Vue 3 et TypeScript strict, construit par Vite dans `openlab_academy/public/espace/` |
| `docker/` | la pile de démonstration (image, composition, nginx, scripts de test) |
| `poc/` | le banc de développement : bench Frappe, MariaDB, Redis |
| `docs/` | charte, spécifications (`specs/`), ressources pédagogiques (`Ressources/`), captures (`captures/`), supports (`supports/`) |
| `.github/` | chaîne d'intégration, et `scripts/audit_front.py` |

Les parcours ne se modifient pas dans l'interface : ils vivent dans
`data/parcours/*.yaml` et le crochet `after_migrate` les republie. Une séance dont la
case « Contenu retouché » est cochée est préservée.

## Lancer et tester

Les deux piles Docker ne tiennent **jamais ensemble** en mémoire sur ce poste : arrêter
l'une avant de lancer l'autre.

```bash
# banc de développement (port 8000)
cd poc && docker-compose -p openlab-academy up -d

# pile de démonstration (port 8080, hôte academy.localhost)
docker-compose -p ol-academy -f docker/docker-compose.yml build
docker-compose -p ol-academy -f docker/docker-compose.yml up -d
```

```bash
# suite complète du backend, couverture ≥ 99 % (banc de développement requis)
bash docker/dev-test.sh
# un seul module, quand la mémoire est juste — un à la fois. Le seuil de couverture ne s'applique
# pas à ce mode : un module seul n'exerce que quelques pour cent du code.
bash docker/dev-test.sh openlab_academy.tests.test_schema

# front
cd apps/openlab_academy/frontend && npm run lint && npm run typecheck && npm test && npm run build

# archives livrées : les cinq contrôles que la chaîne d'intégration applique. Toute archive se vérifie
# avant d'être reconstruite, et aucune ne se modifie à la main : elle se rend depuis sa source.
python docs/Ressources/construire_schemas.py --verifier
python docs/Ressources/construire_notebooks.py --verifier
python docs/Ressources/construire_labs.py --verifier --eprouver
python docs/Ressources/construire_archive_socle.py --verifier
python docs/Ressources/construire_depots_python.py --verifier
# les reconstruire : le même script sans --verifier
python docs/Ressources/construire_notebooks.py

# dépendances de production du front
python .github/scripts/audit_front.py apps/openlab_academy/frontend

# répartiteur des lots de tests : ses propres tests, et la table des coûts mesurés
python -m unittest discover -s .github/scripts -p "test_*.py"
# fondre une exécution de plus dans la table des coûts : elle garde leur moyenne, un seul
# relevé étant trop bruité (un module varie de moitié d'une exécution à l'autre)
gh run view <id> --log | python .github/scripts/lots_de_tests.py apps/openlab_academy/openlab_academy/tests --mesurer - --execution <id>
```

## Pièges

- **Le banc de développement n'a pas de volume pour `frappe-bench`.** Recréer le
  conteneur Frappe efface le bench entier. On le redémarre, on ne le recrée pas.
- **`docker-compose` v1** : pas de `name:`, pas de `profiles:`, pas de syntaxe propre à
  la v2 dans les fichiers de composition. Le nom de pile vient toujours de `-p`.
- **Mémoire**, encore : un `build` et un navigateur ouvert suffisent à faire tomber
  MariaDB. Le lancer au premier plan et attendre.
- **`poc/init.sh` doit rester en fins de ligne LF** et épinglé sur Python 3.12.15.
- Les tests qui touchent un site Frappe réel ne tournent pas hors conteneur.

## Conventions

- **Tests d'abord.** La chaîne refuse en dessous de 99 % de couverture sur le backend.
  En CI, la suite tourne en **trois lots parallèles** (`.github/scripts/lots_de_tests.py` ;
  le nombre de lots est tenu par `LOTS` dans `ci.yml`, et la répartition est lue sur le
  disque, donc un module ajouté entre dans un lot tout seul) ; la barrière de couverture
  s'applique sur leur cumul, dans un job dédié. En local, `dev-test.sh` lance tout d'un
  coup, sans découpage.
- **Sécurité et architecture au premier plan** : OWASP et architecture hexagonale sont
  des critères de revue, pas des ajouts. Le domaine ne connaît pas Frappe.
- **Commits en français**, sujet court sans accent, à l'impératif ou au constat
  (`fix(academy): le controle des archives compare ce qu'elles servent`), corps qui
  explique le pourquoi et ce que le lecteur ne devinerait pas. Un commit, un sujet.
- **Tout le texte vu par un apprenant est en français**, accents compris.
- Les illustrations sont libres de droits et créditées dans
  `data/ressources/CREDITS-ILLUSTRATIONS.md`.

## Secrets et fichiers locaux

Jamais versionnés, et absents d'un dépôt fraîchement cloné : `credentials-local.md`
(identifiants des comptes de test), `docker/secrets/` (mots de passe de la pile),
`.env` et dérivés. `.gitignore` les exclut, Gitleaks et Semgrep vérifient l'historique
à chaque PR. Un identifiant inventé pour un test se déclare dans `.gitleaks.toml`.

## Second facteur d'authentification

Il se règle dans **Réglages OpenLab Academy → Sécurité** : la case, la méthode, et les rôles
concernés, un par ligne. Le rôle des apprenants y est refusé — il les bloquerait tous sur un
téléphone sans rien protéger de plus.

L'ordre compte, et le code l'impose. En méthode « OTP App », Frappe envoie le code d'inscription
**par courriel** au tout premier accès ; sans compte d'envoi en service, ce courriel ne part jamais
et la porte reste close. On inscrit donc avant d'activer :

```bash
# 1. affiche le QR à photographier (le secret ne sort que là, dans votre terminal)
bench --site <site> execute openlab_academy.entrypoints.securite.inscrire_le_second_facteur   --kwargs "{'utilisateur': 'vous@exemple.ci'}"

# 2. vérifie un premier code, ce qui valide l'inscription
bench --site <site> execute openlab_academy.entrypoints.securite.confirmer_le_second_facteur   --kwargs "{'utilisateur': 'vous@exemple.ci', 'code': '123456'}"

# 3. active. Refusé tant que l'étape 2 n'a pas abouti pour au moins un compte actif
bench --site <site> execute openlab_academy.entrypoints.securite.activer_le_second_facteur

# en cas de besoin : rouvre la porte, en toute circonstance
bench --site <site> execute openlab_academy.entrypoints.securite.eteindre_le_second_facteur
```

Ces commandes ne sont pas exposées en API : le secret TOTP ne doit traverser ni une réponse HTTP,
ni les journaux d'un navigateur. Une migration n'active jamais le second facteur d'elle-même ; si
le réglage demandé n'est plus tenable, elle le laisse éteint et le dit.

## Publier

Le dépôt est autonome depuis le 18 novembre 2026 : un `git push` ordinaire suffit,
sans découpage. Toute branche part de `develop` et y retourne par PR ; le crochet
`pre-push` (`core.hooksPath` sur `.githooks`, à régler une fois par clone) refuse un
push direct sur `main` ou `develop` — contournement assumé et tracé :
`PUSH_DIRECT=1 git push`. La suite est décrite dans [flux-git.md](flux-git.md).
