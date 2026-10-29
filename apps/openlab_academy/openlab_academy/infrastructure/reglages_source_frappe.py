"""Adaptateur : écran « Reglages OpenLab Academy » (DocType single) <-> value object Reglages du domaine."""
import frappe
from frappe.utils import getdate

from openlab_academy.domain.lancement import PhaseLancement
from openlab_academy.domain.reglages import JOURS, CritereBareme, Reglages, Rythme

DOCTYPE = "Reglages OpenLab Academy"
PLATEFORME_DEFAUT = {"nom_plateforme": "OpenLab Academy", "logo": "/assets/openlab_academy/images/logo.svg",
                     "langue": "fr", "devise": "XOF"}


def _hhmm(valeur) -> str:
    """Les champs Time arrivent en « HH:MM:SS » ou en timedelta ; le domaine attend « HH:MM »."""
    texte = str(valeur or "")
    heures, minutes = texte.split(":")[:2]
    return f"{int(heures):02d}:{minutes}"


def _est_initialise(doc) -> bool:
    return bool(doc.get("rythmes"))


def vers_domaine(doc) -> Reglages:
    return Reglages(
        projets_par_portfolio=int(doc.projets_par_portfolio or 0),
        heures_par_module=int(doc.heures_par_module or 0),
        delai_ouverture_semaines=int(doc.delai_ouverture_semaines or 0),
        jour_ouverture=[j.capitalize() for j in JOURS].index(doc.jour_ouverture or "Lundi"),
        questions_par_quiz=int(doc.questions_par_quiz or 0), tentatives_max=int(doc.tentatives_max or 0),
        score_min=int(doc.score_min or 0), delai_exercices_minutes=int(doc.delai_exercices_minutes or 0),
        bareme=tuple(CritereBareme(c.nom, int(c.poids or 0)) for c in doc.bareme),
        exigences_communes=tuple(e.texte for e in doc.exigences),
        rythmes=tuple(Rythme(r.code or "", r.libelle or "", tuple(int(r.get(j) or 0) for j in JOURS))
                      for r in doc.rythmes),
        heure_debut=_hhmm(doc.heure_debut), heure_fin=_hhmm(doc.heure_fin), fuseau=doc.fuseau or "",
        parcours_pilote=doc.parcours_pilote or "", formateur=doc.formateur or "",
        places_par_cohorte=int(doc.places_par_cohorte or 0),
        ouverture_lancement=getdate(doc.ouverture_lancement) if doc.ouverture_lancement else None,
    )


def charger() -> Reglages:
    doc = frappe.get_single(DOCTYPE)
    return vers_domaine(doc) if _est_initialise(doc) else Reglages()


def phase_lancement() -> PhaseLancement:
    """Phase de lancement lue sur le document single en cache (invalidé à l'enregistrement)."""
    doc = frappe.get_cached_doc(DOCTYPE)
    return PhaseLancement(bool(doc.get("phase_lancement")),
                          frozenset(l.cours for l in doc.get("parcours_lancement") or [] if l.cours))


def plateforme() -> dict:
    doc = frappe.get_single(DOCTYPE)
    return {cle: doc.get(cle) or defaut for cle, defaut in PLATEFORME_DEFAUT.items()}


def initialiser() -> None:
    """Remplit l'écran avec les valeurs par défaut, sans jamais écraser des réglages existants."""
    doc = frappe.get_single(DOCTYPE)
    if _est_initialise(doc):
        return
    d = Reglages()
    doc.update({
        "projets_par_portfolio": d.projets_par_portfolio, "heures_par_module": d.heures_par_module,
        "delai_ouverture_semaines": d.delai_ouverture_semaines, "jour_ouverture": JOURS[d.jour_ouverture].capitalize(),
        "questions_par_quiz": d.questions_par_quiz, "tentatives_max": d.tentatives_max, "score_min": d.score_min,
        "delai_exercices_minutes": d.delai_exercices_minutes,
        "heure_debut": f"{d.heure_debut}:00", "heure_fin": f"{d.heure_fin}:00", "fuseau": d.fuseau,
        "parcours_pilote": d.parcours_pilote, "formateur": d.formateur, "places_par_cohorte": d.places_par_cohorte,
        "phase_lancement": 1, **PLATEFORME_DEFAUT,
    })
    doc.set("bareme", [{"nom": c.nom, "poids": c.poids} for c in d.bareme])
    doc.set("exigences", [{"texte": e} for e in d.exigences_communes])
    doc.set("rythmes", [{"code": r.code, "libelle": r.libelle, **dict(r.semaine)} for r in d.rythmes])
    doc.save(ignore_permissions=True)
