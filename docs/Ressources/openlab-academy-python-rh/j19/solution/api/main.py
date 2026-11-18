"""L'API RH : la couche HTTP, autour du cœur."""
import logging
from datetime import date

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.responses import JSONResponse

from api.sorties import SalarieDetail, SalarieResume
from rh.calculs import droit_aux_conges
from rh.depot import DepotEffectif
from rh.entrees import SalarieEntrant
from rh.erreurs import DejaPris, DonneeInvalide, Introuvable
from rh.exemple import FICHES

app = FastAPI(title="API RH")
depot = DepotEffectif(FICHES)
journal = logging.getLogger("api")


@app.exception_handler(DonneeInvalide)
def donnee_invalide(requete: Request, erreur: DonneeInvalide):
    """Traduit une erreur métier en 400, avec le message destiné à l'utilisateur."""
    return JSONResponse(status_code=400, content={"detail": str(erreur)})


@app.exception_handler(Exception)
def panne_interne(requete: Request, erreur: Exception):
    """Journalise la panne côté serveur et ne rend au client qu'un message neutre."""
    journal.exception("panne sur %s %s", requete.method, requete.url.path)
    return JSONResponse(status_code=500, content={"detail": "Erreur interne."})


@app.get("/sante")
def sante():
    """Dit si l'application répond."""
    return {"etat": "ok"}


@app.get("/salaries", response_model=list[SalarieResume])
def lister_salaries():
    """Rend la liste des fiches, sans les salaires."""
    return depot.lister()


@app.get("/salaries/{matricule}", response_model=SalarieDetail)
def lire_salarie(matricule: str):
    """Rend le détail d'un salarié, ou 404 s'il n'existe pas."""
    try:
        return depot.lire(matricule)
    except Introuvable as erreur:
        raise HTTPException(status_code=404, detail=str(erreur)) from erreur


@app.post("/salaries", response_model=SalarieDetail, status_code=status.HTTP_201_CREATED)
def ajouter_salarie(entrant: SalarieEntrant):
    """Ajoute un salarié, ou 409 si le matricule est déjà pris."""
    fiche = entrant.model_dump()
    fiche["date_embauche"] = fiche["date_embauche"].isoformat()
    try:
        return depot.ajouter(fiche)
    except DejaPris as erreur:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(erreur)) from erreur


@app.get("/salaries/{matricule}/conges")
def conges_du_salarie(matricule: str):
    """Dit si le droit aux congés est ouvert, ou 400 si la fiche est inexploitable."""
    fiche = _fiche(matricule)
    try:
        mois = _mois_anciennete(fiche["date_embauche"])
    except ValueError as erreur:
        raise DonneeInvalide(
            f"Date d'embauche illisible pour le matricule {matricule}.") from erreur
    return {"matricule": matricule, "mois_anciennete": mois,
            "droit_ouvert": droit_aux_conges(mois)}


def _fiche(matricule):
    """Rend la fiche demandée, ou lève une 404."""
    try:
        return depot.lire(matricule)
    except Introuvable as erreur:
        raise HTTPException(status_code=404, detail=str(erreur)) from erreur


def _mois_anciennete(date_embauche):
    """Rend l'ancienneté en mois révolus à la date du jour."""
    embauche = date.fromisoformat(date_embauche)
    aujourdhui = date.today()
    mois = (aujourdhui.year - embauche.year) * 12 + aujourdhui.month - embauche.month
    if aujourdhui.day < embauche.day:
        mois -= 1
    return mois
