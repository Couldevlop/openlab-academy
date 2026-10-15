# OpenLab Academy — Réglages paramétrables : plan d'implémentation

Spec : `2026-10-15-academy-socle-design.md` §9. Exécution native, TDD, couverture ≥ 99 %, tests sécurité OWASP.
Plan volontairement condensé (préférence utilisateur : économie de tokens) ; chaque tâche = tests rouges → code → vert → commit.

1. **Domaine `Reglages` + `Rythme` données** (`domain/reglages.py`) — tests : défauts = valeurs actuelles ; barème ≠ 100,
   rythme 0 h, codes en double, aucun rythme, fin ≤ début, projets ≤ 0, heures module ≤ 0 → `ReglagesInvalides` ;
   `rythme(code)` inconnu → erreur ; `descriptif` et `heures` calculés.
2. **Parcours et cohorte paramétrés** — `Parcours.projets_attendus/heures_par_module` ; `duree_semaines(heures)` ;
   `Cohorte.pilote(parcours, debut, rythme, reglages)` ; `OuvrirCohorte(depot, reglages)` (début = jour d'ouverture
   après délai) ; suppression des constantes en dur.
3. **YAML : `parametres:` + réglages injectés** (`charger_dossier(dossier, reglages)`) — clé inconnue refusée,
   surcharge appliquée, défauts sinon.
4. **Rendu paramétré** (`editorjs`) — exigences et barème lus dans `Reglages` ; durée module affichée.
5. **DocType single + tables enfants** + contrôleur validant via le domaine ; permissions System Manager seules ;
   adaptateur `SourceReglagesFrappe` (`charger`, `initialiser`) ; patch d'initialisation ; tests d'intégration
   (lecture, validation refusée, 403 apprenant en lecture/écriture via API).
6. **Points d'entrée** — seed, cohorte, install, réglages plateforme (nom, logo, langue, devise) lisent les réglages ;
   `ouvrir_pilote(rythme=<code>)` accepte tout code configuré.
7. **Vérification réelle** — banc de dev : modifier un réglage dans l'écran, republier, constater l'effet ; suite complète.
