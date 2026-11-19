# Lab de la séance 09 — journalisation et SIEM

Une agence de transfert d'argent d'Abidjan vous confie ses journaux de la nuit du 14 mars. Elle ne
sait pas encore qu'elle a été attaquée. Vous avez quatre sources, aucune alerte, et la soirée.

Votre travail tient en trois gestes, dans cet ordre : **collecter**, **normaliser**, **détecter**.

## Les journaux

| Fichier | Source | Ce qu'il journalise |
|---|---|---|
| `journaux/web-portail.log` | Portail client | Chaque requête : date, adresse, méthode, chemin, code, octets |
| `journaux/passerelle-ssh.log` | Passerelle d'administration | Chaque connexion : date, adresse, compte, résultat |
| `journaux/pare-feu.csv` | Pare-feu en sortie | Chaque flux sortant : date, source, destination, port, octets |
| `journaux/annuaire-windows.csv` | Annuaire Windows | Ouvertures de session (4624) et attributions de privilèges (4672) |

Quatre formats, quatre vocabulaires. Tant qu'ils restent ainsi, aucune question ne peut leur être
posée en même temps — et une intrusion se lit précisément dans le croisement.

## Ce que vous avez à écrire

1. `normaliser.py` → `lire_annuaire`. Trois lecteurs sont déjà écrits : suivez-les.
2. `detecter.py` → les trois règles : `force_brute`, `fichier_depose`, `exfiltration`.

```
python -m pytest        # rouge au départ : c'est voulu
python normaliser.py    # combien d'événements, par source
python detecter.py      # vos alertes
python verifier.py      # le code à joindre au livrable
```

Dans l'atelier du navigateur, les deux boutons font la même chose : **Lancer les tests** et
**Exécuter le fichier**. Rien à installer.

## Le piège

Une sauvegarde part chaque nuit à 01:05 et déplace 900 Mo — davantage que ce que l'attaquant
emporte. Une règle d'exfiltration écrite trop vite la signale toutes les nuits. Au bout d'une
semaine, l'analyste la désactive ; le jour de l'attaque, plus personne ne garde la porte. **Une
fausse alerte coûte aussi cher qu'une détection manquée**, et c'est tout l'objet de la séance.

## Le livrable

`verifier.py` atteste que vos règles ont trouvé l'incident, et rien d'autre. Le code qu'il affiche
va dans votre rendu, avec :

- la **chronologie** de l'intrusion, horodatée, du premier essai à la sortie des données ;
- ce que vous auriez **collecté en plus** pour la voir plus tôt, et pourquoi ;
- votre politique de **rétention** : quels journaux garder, combien de temps, et à quel coût.

## Avec un vrai SIEM

`local/` monte OpenSearch et son tableau de bord sur votre machine, chargés de vos propres
événements normalisés : `cd local && docker-compose up -d`, puis `http://localhost:5601`. Compter
3 Go de mémoire libre. Les cibles sont sur un réseau `internal`, sans aucune route vers Internet.

Le tableau de bord n'apprend rien de plus que vos règles — il montre autre chose : à quoi ressemble
cette même nuit vue par l'outil d'un SOC, et pourquoi un analyste y voit en dix secondes ce que
votre script met vingt lignes à dire.

## Cadre

Journaux entièrement fictifs. Les adresses, comptes et montants sont fabriqués pour l'exercice.
Toute pratique offensive, dans ce parcours, se fait sur les labs fournis ou sur un système couvert
par une autorisation écrite (loi ivoirienne n° 2013-451).

Le dossier `corrige/` contient les solutions de référence : à lire après avoir rendu les vôtres.
