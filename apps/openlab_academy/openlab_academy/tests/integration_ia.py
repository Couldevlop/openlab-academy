"""Essai manuel de la pré-correction sur le vrai service d'IA (hors suite de tests, rien n'est enregistré).

URL, modèles, clé et délai sont lus dans la console « Reglages Evaluation OpenLab ». Lancement :

    bench --site lms.localhost execute openlab_academy.tests.integration_ia.executer --kwargs "{'nombre': 10}"

Affiche, pour chacune des N dernières copies ayant un contenu, la durée de l'appel et la proposition interprétée
(ou la raison de l'échec). Sert à mesurer le modèle sur des copies réelles avant de le retenir.
"""
import time

import frappe

from openlab_academy.domain.garde_fous_ia import construire_messages, detecter_injection, interpreter
from openlab_academy.infrastructure import reglages_evaluation_frappe
from openlab_academy.infrastructure.correcteur_ia import CorrecteurCompatibleOpenAI
from openlab_academy.infrastructure.depot_copies_frappe import COPIE, DepotCopiesFrappe


def executer(nombre: int = 10) -> None:
    ia = reglages_evaluation_frappe.charger().ia
    correcteur = CorrecteurCompatibleOpenAI(ia.url, reglages_evaluation_frappe.cle_ia(), ia.delai_minutes * 60)
    depot = DepotCopiesFrappe()
    copies = frappe.get_all(COPIE, {"contenu": ["is", "set"]}, pluck="name", order_by="creation desc",
                            limit=int(nombre))
    print(f"Service : {ia.url} — {len(copies)} copie(s)")
    for copie_id in copies:
        contenu = depot.contenu(copie_id)
        modele = ia.modele_code if contenu.rendu_par_lien else ia.modele_texte
        if detecter_injection(contenu.texte, ia.tournures_injection):
            print(f"\n{copie_id} : copie signalée (tentative d'instruction à l'IA), non envoyée")
            continue
        grille = depot.grille(copie_id)
        messages = construire_messages(grille, depot.consigne(depot.copie(copie_id).exercice), contenu.texte)
        debut = time.monotonic()
        try:
            proposition = interpreter(correcteur.proposer(messages, modele), grille, contenu.texte)
        except Exception as erreur:
            print(f"\n{copie_id} ({modele}) : échec après {time.monotonic() - debut:.1f} s — {erreur}")
            continue
        print(f"\n{copie_id} ({modele}) : {time.monotonic() - debut:.1f} s, confiance {proposition.confiance}")
        for code, niveau in proposition.niveaux.items():
            print(f"  {code} = niveau {niveau} : {proposition.commentaires.get(code, '')}")
            print(f"    citation : {proposition.citations.get(code, '')!r}")
        for code in set(proposition.commentaires) - set(proposition.niveaux):
            print(f"  {code} : {proposition.commentaires[code]}")
