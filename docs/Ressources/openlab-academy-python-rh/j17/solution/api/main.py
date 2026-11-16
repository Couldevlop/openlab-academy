"""L'API RH : la couche HTTP, autour du cœur."""
from fastapi import FastAPI, HTTPException

from api.sorties import SalarieDetail, SalarieResume
from rh.depot import DepotEffectif
from rh.erreurs import Introuvable
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
