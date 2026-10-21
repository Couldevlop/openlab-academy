"""Essai manuel de la pré-correction sur le vrai service d'IA (hors suite de tests, rien n'est enregistré).

URL, modèles, clé et délai sont lus dans la console « Reglages Evaluation OpenLab ». Lancement :

    bench --site lms.localhost execute openlab_academy.tests.integration_ia.executer --kwargs "{'nombre': 10}"

Pour chacune des N dernières copies ayant un contenu, une à la fois : durée de l'appel, jetons du prompt et de la
réponse (champ `usage` renvoyé par le service), réponse tronquée (`finish_reason`), proposition interprétée (ou
raison de l'échec) et écart en niveaux avec la dernière correction du formateur, si elle existe. Termine par une
synthèse. Sert à mesurer le modèle sur des copies réelles avant de le retenir.
"""
import time
from statistics import fmean
from unittest import mock

import frappe
import requests

from openlab_academy.application.corriger import derniere
from openlab_academy.domain.copie import Source
from openlab_academy.domain.garde_fous_ia import construire_messages, detecter_injection, interpreter
from openlab_academy.infrastructure import reglages_evaluation_frappe
from openlab_academy.infrastructure.correcteur_ia import CorrecteurCompatibleOpenAI
from openlab_academy.infrastructure.depot_copies_frappe import COPIE, DepotCopiesFrappe


def _appeler(correcteur: CorrecteurCompatibleOpenAI, messages: list[dict], modele: str) -> tuple[str, dict]:
    """Appel par l'adaptateur réel ; la réponse HTTP brute est seulement observée, pour en lire `usage`."""
    vues = []
    envoyer = requests.post

    def observer(*args, **kwargs):
        reponse = envoyer(*args, **kwargs)
        vues.append(reponse)
        return reponse

    with mock.patch("requests.post", side_effect=observer):
        brut = correcteur.proposer(messages, modele)
    try:
        donnees = vues[-1].json()
    except (IndexError, ValueError):
        donnees = {}
    usage = donnees.get("usage") or {}
    fin = ((donnees.get("choices") or [{}])[0] or {}).get("finish_reason")
    return brut, {"prompt": usage.get("prompt_tokens"), "reponse": usage.get("completion_tokens"), "fin": fin}


def executer(nombre: int = 10) -> None:
    ia = reglages_evaluation_frappe.charger().ia
    correcteur = CorrecteurCompatibleOpenAI(ia.url, reglages_evaluation_frappe.cle_ia(), ia.delai_minutes * 60)
    depot = DepotCopiesFrappe()
    copies = frappe.get_all(COPIE, {"contenu": ["is", "set"]}, pluck="name", order_by="creation desc",
                            limit=int(nombre))
    print(f"Service : {ia.url} — {len(copies)} copie(s)")
    durees, prompts, ecarts, echecs, a_revoir = [], [], [], 0, 0
    for copie_id in copies:
        contenu, texte = depot.contenu(copie_id), depot.texte_lisible(copie_id)
        modele = ia.modele_code if contenu.rendu_par_lien else ia.modele_texte
        if detecter_injection(texte, ia.tournures_injection):
            print(f"\n{copie_id} : copie signalée (tentative d'instruction à l'IA), non envoyée")
            continue
        grille = depot.grille(copie_id)
        messages = construire_messages(grille, depot.consigne(depot.copie(copie_id).exercice), texte)
        debut = time.monotonic()
        try:
            brut, jetons = _appeler(correcteur, messages, modele)
            duree = time.monotonic() - debut
            proposition = interpreter(brut, grille, texte)
        except Exception as erreur:
            echecs += 1
            print(f"\n{copie_id} ({modele}) : échec après {time.monotonic() - debut:.1f} s — {erreur}")
            continue
        durees.append(duree)
        if jetons["prompt"]:
            prompts.append(jetons["prompt"])
        print(f"\n{copie_id} ({modele}) : {duree:.1f} s, confiance {proposition.confiance}, "
              f"jetons prompt {jetons['prompt']} / réponse {jetons['reponse']}, fin {jetons['fin']}")
        formateur = derniere(depot.propositions(copie_id), Source.FORMATEUR)
        for code, niveau in proposition.niveaux.items():
            humain = formateur.niveaux.get(code) if formateur else None
            ecart = "" if humain is None else f" (formateur {humain}, écart {abs(niveau - humain)})"
            if humain is not None:
                ecarts.append(abs(niveau - humain))
            print(f"  {code} = niveau {niveau}{ecart} : {proposition.commentaires.get(code, '')}")
            print(f"    citation : {proposition.citations.get(code, '')!r}")
        for code in set(proposition.commentaires) - set(proposition.niveaux):
            a_revoir += 1
            print(f"  {code} : {proposition.commentaires[code]}")
            print(f"    citation rejetée : {proposition.citations.get(code, '')!r}")
    print(f"\nSynthèse : {len(durees)} proposition(s), {echecs} échec(s), {a_revoir} critère(s) à revoir")
    if durees:
        print(f"  durée moyenne {fmean(durees):.1f} s (min {min(durees):.1f}, max {max(durees):.1f})")
    if prompts:
        print(f"  jetons du prompt : moyenne {fmean(prompts):.0f}, max {max(prompts)}")
    if ecarts:
        print(f"  écart IA/formateur : moyenne {fmean(ecarts):.2f} niveau sur {len(ecarts)} critère(s), "
              f"{sum(e > 1 for e in ecarts)} écart(s) de plus d'un niveau")
