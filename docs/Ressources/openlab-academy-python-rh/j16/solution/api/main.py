"""L'API RH : la couche HTTP, autour du cœur."""
from fastapi import FastAPI

from rh.depot import DepotEffectif
from rh.exemple import FICHES

app = FastAPI(title="API RH")
depot = DepotEffectif(FICHES)


@app.get("/sante")
def sante():
    """Dit si l'application répond."""
    return {"etat": "ok"}


@app.get("/salaries")
def lister_salaries():
    """Rend la liste des fiches, triée par matricule."""
    return depot.lister()
