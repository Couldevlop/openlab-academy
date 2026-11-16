"""L'API RH : la couche HTTP, autour du cœur.

Créez l'application, le dépôt, et les deux routes de lecture de l'énoncé.
"""
from fastapi import FastAPI

from rh.depot import DepotEffectif
from rh.exemple import FICHES

app = FastAPI(title="API RH")
depot = DepotEffectif(FICHES)
