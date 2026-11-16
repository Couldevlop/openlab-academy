"""Point d'entrée du programme."""
from rh.calculs import masse_salariale
from rh.etats import etat_par_poste

EFFECTIF = [
    {"nom": "Awa", "poste": "RH", "salaire_fcfa": 250000},
    {"nom": "Bakary", "poste": "Atelier", "salaire_fcfa": 180000},
]


def main():
    """Affiche l'état par poste d'un effectif d'exemple."""
    print(etat_par_poste(EFFECTIF))
    print(masse_salariale([fiche["salaire_fcfa"] for fiche in EFFECTIF]))


if __name__ == "__main__":
    main()
