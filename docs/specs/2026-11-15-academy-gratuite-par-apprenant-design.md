# Offrir un parcours à un apprenant, et revenir en arrière — conception

**Besoin** : depuis la fiche d'un parcours, l'administrateur bascule un apprenant de payant à gratuit en un clic,
et de gratuit à payant aussi facilement. L'apprenant **s'inscrit quand même** : l'inscription reste le point où
la donnée est collectée et gérée ; c'est le paiement qui saute, pas le dossier.

## Ce qui existe déjà

- `Parcours gratuit (MOOC)` : une case sur le parcours, donc tout ou rien, pour **tout le monde**
  (`depot_dossiers_frappe.CHAMP_GRATUIT`, `application/parcours_gratuits.py`).
- La **dispense** d'un dossier de paiement : il ne bloque plus, ne reçoit plus de rappel, reste visible dans
  l'intendance, et le journal garde qui a dispensé, quand et pourquoi (`DispenserParcoursGratuit`).
- L'inscription directe à un parcours payant hors cohorte est refusée
  (`application/inscriptions.verifier_inscription_directe`) : sans dossier, personne ne serait jamais bloqué.

La gratuité par apprenant se greffe sur ces trois pièces : elle lève le refus d'inscription pour la personne
visée, et fait naître son dossier déjà dispensé.

## Modèle

Doctype `Gratuite Apprenant OpenLab`, une ligne par couple (apprenant, parcours) :

| champ | rôle |
|---|---|
| `apprenant` | Link `User` |
| `parcours` | Link `LMS Course` |
| `accordee_le` / `accordee_par` | quand, et par qui |
| `motif` | texte libre : bourse, partenariat, geste commercial |

Ligne présente = parcours offert à cette personne. Ligne retirée = parcours payant pour elle.

## Règles

1. **Inscription** — un apprenant à qui le parcours est offert peut s'inscrire lui-même, hors cohorte. Les
   refus de fenêtre (parcours fermé) et de lancement (parcours caché) restent, eux : la gratuité touche au
   prix, jamais au calendrier.
2. **Dossier** — son inscription crée un dossier comme pour tout le monde (tarif du jour figé, échéancier
   calculé), **dispensé dans la foulée**, motif « parcours offert ». L'intendance voit donc la personne, son
   parcours, ce que le parcours aurait coûté, qui l'a offert et quand. Rien ne bloque, aucun rappel ne part.
3. **Retrait** — la gratuité retirée, le dossier redevient dû tel qu'il est (échéances d'origine, éventuellement
   en retard) et le blocage reprend ses droits. Une ligne de journal le dit, avec son auteur.
4. **Ce qui a été payé reste payé** : offrir un parcours à quelqu'un qui a déjà réglé une partie ne rembourse
   rien ; le reste dû tombe, le règlement reste au dossier.
5. **Réservé à l'administrateur et à l'intendant**, comme la dispense d'un parcours devenu gratuit.
6. Un parcours déjà gratuit pour tous (MOOC) rend la gratuité par apprenant sans objet : l'écran le dit au lieu
   de proposer la bascule.

## Écran

Fiche du parcours (bureau), bouton **« Inscrits et gratuités »** : un tableau des inscrits, une ligne par
personne, l'état (payant, offert, soldé) et un interrupteur. Un champ « Offrir à… » cherche un apprenant pas
encore inscrit, pour lui ouvrir le parcours avant qu'il s'inscrive.

## Découpage

1. Domaine et cas d'usage : `AccorderGratuite`, `RetirerGratuite`, port `Gratuites`, journalisation, droits.
2. Inscription : `verifier_inscription_directe` tient compte de la gratuité accordée.
3. Dossier : ouverture d'un dossier offert (dispensé à la création) pour une inscription directe comme pour une
   cohorte.
4. Infrastructure Frappe : doctype, dépôt, droits.
5. Écran : bouton, tableau des inscrits, interrupteur, recherche d'apprenant.
6. Recette navigateur : offrir, s'inscrire sans payer, vérifier l'intendance, retirer, vérifier le blocage.
