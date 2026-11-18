"""Journée 02 : nombres, arrondis et montants en FCFA."""

ESPACE = "\u00a0"


def salaire_annuel(mensuel, primes):
    """Rend le coût annuel, en francs CFA, en nombre entier."""
    return round(mensuel * 12 + sum(primes))


def formater_fcfa(montant):
    """Rend le montant écrit avec des espaces comme séparateurs de milliers."""
    return f"{round(montant):,} FCFA".replace(",", ESPACE)
