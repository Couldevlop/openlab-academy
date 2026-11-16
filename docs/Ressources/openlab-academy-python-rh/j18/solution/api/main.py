"""L'API RH : la couche HTTP, autour du cœur."""
from fastapi import FastAPI, HTTPException, status

from api.sorties import SalarieDetail, SalarieResume
from rh.depot import DepotEffectif
from rh.entrees import SalarieEntrant
from rh.erreurs import DejaPris, Introuvable
from rh.exemple import FICHES

app = FastAPI(title="API RH")
depot = DepotEffectif(FICHES)


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
