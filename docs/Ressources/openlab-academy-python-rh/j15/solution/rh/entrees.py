"""Le modèle d'entrée : ce que le monde extérieur a le droit d'envoyer."""
from datetime import date

from pydantic import BaseModel, Field, field_validator


class SalarieEntrant(BaseModel):
    """Une fiche venue de l'extérieur, avant d'entrer dans le cœur."""

    matricule: str = Field(min_length=1)
    nom: str = Field(min_length=1)
    poste: str = Field(min_length=1)
    date_embauche: date
    salaire_fcfa: int = Field(ge=0)

    @field_validator("date_embauche")
    @classmethod
    def pas_dans_le_futur(cls, valeur: date) -> date:
        """Refuse une embauche postérieure à aujourd'hui."""
        if valeur > date.today():
            raise ValueError("la date d'embauche ne peut pas être dans le futur")
        return valeur
