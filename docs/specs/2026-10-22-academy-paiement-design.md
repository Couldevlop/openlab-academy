# OpenLab Academy — Sous-projet 2 : paiement des parcours (CinetPay, XOF)

Date : 2026-10-22 · Dépôt : `Couldevlop/openlab-academy` (publié depuis le monorepo `D:\OPENLAB`, dossier
`Openlab_Academy/`) · Suite du socle (sous-projet 1) et du moteur d'évaluation.

## 1. Intention

Les parcours deviennent payants. Un apprenant ivoirien choisit à l'inscription comment il paie (en une fois, en deux
tranches ou au mois), est prévenu avant chaque échéance par e-mail, SMS et WhatsApp, et perd l'accès aux contenus s'il
laisse passer une échéance, jusqu'à ce qu'il paie. Un intendant (économe) suit tous les paiements et encaisse les
virements ; l'administration en voit le résumé. L'objectif est un encaissement régulier sans relance manuelle, avec une
trace de chaque geste humain sur l'argent.

## 2. Décisions de l'utilisateur

### Prix
- Chaque parcours (LMS Course) a **trois prix globaux en XOF** (montant total du parcours) : « une fois », « deux
  tranches », « mensuel », plus des **frais d'inscription**. Ils sont saisis dans la console par l'**intendant ou
  l'administrateur**. Les prix sont décidés hors de la plateforme ; aucun calcul de remise.
  Ordre attendu : une fois < deux tranches < mensuel.

### Inscription
- L'apprenant choisit son **mode de paiement** à l'inscription et donne son **numéro de téléphone** (rappels SMS et
  WhatsApp).
- Il paie à l'inscription les **frais d'inscription**, **déduits du prix global** de son mode. Ce paiement ouvre
  l'accès au parcours.
- **Inscription tardive** permise jusqu'à **deux mois après le début** de la cohorte, plus au-delà.

### Échéancier (validé)
Toutes les échéances tombent **le 10 du mois** ; le reste dû = prix global du mode − frais d'inscription.
- **Une fois** : tout le reste le **10 du mois suivant l'inscription**.
- **Deux tranches** : la moitié du reste le 10 du mois suivant l'inscription, l'autre moitié le **10 du mois de
  mi-parcours** (milieu de la cohorte).
- **Mensuel** : le reste en parts égales, le 10 de chaque mois, du mois suivant l'inscription jusqu'au mois de fin de
  la cohorte. Exemple : inscrit le 15 → première mensualité au plus tard le 10 du mois suivant.

### Changement de mode
- Possible à tout moment, **sans pénalité** : ce qui est payé reste acquis ; le reste dû devient le prix du nouveau mode
  moins le déjà-versé, réparti sur les échéances **à venir** du nouveau mode. Exemple : deux mensualités payées puis
  passage en « une fois » → prix « une fois » − déjà versé, dû à la prochaine échéance.

### Rappels
- **7 jours, 3 jours et 1 jour** avant chaque échéance, par **e-mail, SMS et WhatsApp**.

### Blocage
- Échéance passée sans paiement → **le parcours concerné est bloqué** : l'apprenant peut toujours se connecter mais
  toute page de **ce parcours** le redirige vers la page de paiement. **Un autre parcours à jour reste ouvert.**
- Déblocage : paiement CinetPay confirmé, ou virement enregistré.

### Moyens de paiement
- **CinetPay** (en ligne) et **virement** (enregistré à la main). **Pas d'espèces.**

### Fournisseurs à venir
- OpenLab a un numéro ; les comptes WhatsApp Business / Facebook seront rattachés plus tard. Les API SMS, WhatsApp et
  le compte marchand CinetPay **viendront** : **tout prévoir maintenant**, les clés se saisissent dans la console
  quand elles existent.

### Rôles
- **Intendant** (économe) : nouveau rôle. **Vue à 360°** des paiements, encours, retards, comptes bloqués.
  Il **enregistre** (virements, délais, déblocages, prix) **au même titre que l'administrateur**.
- **Traçabilité** : pour l'intendant comme pour l'administrateur, **trace de ce que chacun fait**.
- **Administration** : **vue plus résumée**.
- Maquettes validées sur le fond (cf. §6) ; **le design doit être plus soigné** que les maquettes de principe.

### Choix du rédacteur (à vérifier à la lecture)
- **Frais d'inscription par parcours**, saisis avec les trois prix.
- **Prix figés à l'inscription** : un changement de prix vaut pour les nouveaux inscrits ; un changement de mode d'un
  inscrit utilise les prix figés à son inscription.
- **Débloquer = accorder un délai** : une seule action, qui exige une nouvelle date limite pour l'échéance impayée,
  journalisée (auteur, date, motif). Sans date, la tâche planifiée rebloquerait aussitôt.
- **Mi-parcours** : si le 10 du mois de mi-parcours ne tombe pas après la première tranche (inscription tardive),
  la seconde tranche est due le 10 du mois qui suit la première.
- **Mensuel** : au moins une mensualité ; parts entières en XOF, le reste de la division sur la dernière.
- **Inscriptions existantes** au déploiement : dispensées de paiement (aucune cohorte payante en production).
- **Inscription LMS** (`LMS Batch Enrollment`) créée à l'inscription ; l'accès reste redirigé vers le paiement tant que
  les frais d'inscription ne sont pas réglés. Le paiement natif de LMS n'est pas utilisé.
- **Équipe** (correcteurs, intendant, administrateur) : jamais bloquée.

## 3. Objectifs

1. Prix globaux par parcours et par mode, et frais d'inscription, dans la console.
2. Choix du mode et du téléphone à l'inscription, paiement des frais d'inscription ; mode modifiable ensuite.
3. Échéancier calculé, recalculé au changement de mode, dans la règle ci-dessus.
4. Paiement en ligne CinetPay avec confirmation serveur (notification de paiement vérifiée, jamais la seule redirection
   du navigateur).
5. Rappels J-7, J-3, J-1 sur trois canaux, chaque canal actif seulement s'il est configuré.
6. Blocage automatique, par parcours, à l'échéance dépassée ; redirection vers la page de paiement ; déblocage automatique au paiement.
7. Enregistrement manuel des virements, délais et déblocages par l'intendant ou l'administrateur, journalisés.
8. Vue intendant (détaillée, filtres, export) et résumé administrateur.

## 4. Non-objectifs

- Espèces.
- Remboursements, avoirs, factures normalisées (comptabilité hors plateforme).
- Calcul automatique des prix ou remises.
- Paiement des labs ou d'autres services que les parcours.

## 5. Anti-objectifs (échec même si « ça marche »)

- Un apprenant à jour bloqué à tort (horloge, fuseau, notification CinetPay tardive) : en cas de doute, ne pas bloquer.
- Un paiement validé sur la seule foi du retour navigateur, ou une notification CinetPay non vérifiée.
- Un geste humain sur l'argent (virement, délai, déblocage, prix) sans trace de son auteur.
- Un canal non configuré qui fait échouer les rappels des autres canaux.
- Des secrets (clés CinetPay, SMS, WhatsApp) en clair dans le code, les journaux ou l'API.

## 6. Écrans (maquettes de principe validées sur le fond)

- **Intendant — vue complète** : filtres (parcours, cohorte, mode, statut, période), export Excel ; indicateurs
  (encaissé, encours à échoir, en retard, comptes bloqués) ; liste des apprenants (parcours et mode, payé / total,
  prochaine échéance, statut : à jour, rappel envoyé, bloqué, soldé). Fiche apprenant : échéancier, paiements (CinetPay
  ou virement + référence), rappels envoyés par canal, **journal des actions (qui, quoi, quand)**. Actions :
  enregistrer un virement, accorder un délai, débloquer.
- **Administrateur — résumé** : encaissé du mois (évolution), taux de recouvrement, retards dont bloqués ; tableau par
  parcours (inscrits, encaissé, reste dû) ; répartition des modes ; dernières actions de l'équipe ; accès aux prix et à
  l'enregistrement d'un virement.
- **Apprenant** : choix du mode, téléphone et paiement des frais à l'inscription ; page « Mes paiements » (échéancier, payer, changer de
  mode) ; page de paiement vers laquelle il est redirigé s'il est bloqué.
- **Design** : plus soigné que les maquettes, dans l'habillage OpenLab existant (`public/css/openlab.css`) et la pile
  des écrans d'évaluation (Vue 3 + frappe-ui, `/espace`).

## 7. Contraintes

- Frappe v15 + LMS + app `openlab_academy`, sans fork de LMS. Parcours = `LMS Course`, cohorte = `LMS Batch`
  (début, fin), inscription = `LMS Batch Enrollment`.
- Architecture du dépôt : domaine pur (`domain/`), cas d'usage (`application/`), adaptateurs Frappe et externes
  (`infrastructure/`), points d'entrée (`entrypoints/`) ; tests TDD, couverture back ≥ 99 % (CI), front TS strict.
- Les tests doivent passer sur un **site neuf** (CI GitHub Actions).
- Sécurité : OWASP au premier plan ; secrets en champs Password de la console ; vérification de la notification
  CinetPay (signature / revérification du statut côté CinetPay) ; idempotence des notifications reçues plusieurs fois.
- Fuseau : Abidjan (UTC, sans heure d'été) pour échéances et blocage.
- Aucune trace d'outillage dans le code, les commits ou les fichiers.

## 8. Laissé au constructeur

- Modèle de données (DocTypes d'échéancier, paiements, journal), nommage, migrations.
- Ports et adaptateurs : passerelle de paiement (CinetPay, sandbox), canaux de notification (e-mail Frappe, SMS,
  WhatsApp Business Cloud API), chacun désactivé proprement tant qu'il n'est pas configuré.
- Mécanisme de redirection des comptes bloqués (hook de requête Frappe), avec exceptions (page de paiement,
  déconnexion, API de paiement, ressources statiques).
- Planification (tâche Frappe) des rappels et du blocage, idempotente.
- Arrondis XOF (entiers), répartition d'un reste non divisible.
