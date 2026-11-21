"""Second facteur d'authentification : quels rôles en portent un, et à quelle condition l'activer.

Aucune dépendance à Frappe. Les règles tiennent en deux idées, et la seconde est la seule qui
compte vraiment.

**Qui.** Un second facteur se demande aux rôles qui peuvent faire du mal : administrer la
plateforme, tenir la caisse. Il ne se demande pas aux apprenants, et ce n'est pas une question de
confort — c'est que le compte d'un apprenant n'ouvre rien d'autre que ses propres cours, alors que
l'exiger de tous ferait dépendre chaque inscription d'un téléphone et d'une application tierce.

**Quand.** Activer le second facteur sans que personne ne l'ait d'abord inscrit enferme tout le
monde dehors. Frappe, en méthode « OTP App », envoie le code d'inscription **par courriel** au
premier accès (`frappe/twofactor.py`) : sans compte d'envoi en service, ce courriel ne part jamais
et la porte reste close pour toujours. L'ordre est donc inscrire, vérifier, puis activer — et cette
règle est tenue ici plutôt que confiée à la mémoire de qui lancera la commande.
"""
from dataclasses import dataclass

# Le rôle des apprenants, qu'on refuse de soumettre au second facteur : voir l'en-tête.
ROLE_APPRENANT = "LMS Student"
# Rôles auxquels il est demandé par défaut, à la première installation.
ROLES_PAR_DEFAUT = ("System Manager",)
METHODES = ("OTP App", "Email")
METHODE_PAR_DEFAUT = "OTP App"


class SecondFacteurInvalide(ValueError):
    """La configuration demandée mettrait la plateforme hors d'accès, ou ne veut rien dire."""


@dataclass(frozen=True)
class Reglage:
    """Ce qui est demandé : l'état voulu, la méthode, et les rôles concernés."""

    actif: bool
    methode: str
    roles: tuple[str, ...]


def methode_valide(methode: str) -> str:
    propre = (methode or "").strip() or METHODE_PAR_DEFAUT
    if propre not in METHODES:
        raise SecondFacteurInvalide(
            f"méthode « {propre} » inconnue (attendu : {', '.join(METHODES)})")
    return propre


def roles_demandes(brut: str, connus: tuple[str, ...]) -> tuple[str, ...]:
    """Les rôles lus dans le réglage, un par ligne, dédoublonnés et dans l'ordre de saisie.

    Un rôle inconnu est refusé plutôt qu'ignoré : silencieusement ignoré, il donnerait le sentiment
    d'une protection posée alors que rien ne l'est — une faute de frappe suffirait.
    """
    lus, vus = [], set()
    for ligne in (brut or "").splitlines():
        role = ligne.strip()
        if not role or role in vus:
            continue
        if role not in connus:
            raise SecondFacteurInvalide(f"rôle « {role} » inconnu")
        if role == ROLE_APPRENANT:
            raise SecondFacteurInvalide(
                f"le second facteur ne se demande pas au rôle « {ROLE_APPRENANT} » : "
                "il bloquerait chaque apprenant sur un téléphone, sans rien protéger de plus")
        lus.append(role)
        vus.add(role)
    return tuple(lus)


def exiger_un_porteur(reglage: Reglage, inscrits: tuple[str, ...]) -> None:
    """Refuse d'activer tant que personne n'a terminé son inscription.

    `inscrits` liste les comptes qui portent déjà un second facteur vérifié et qui tiennent l'un
    des rôles demandés. Vide, l'activation fermerait la porte derrière elle.
    """
    if not reglage.actif:
        return
    if not reglage.roles:
        raise SecondFacteurInvalide(
            "aucun rôle ne porte le second facteur : l'activer ne protégerait rien")
    if not inscrits:
        raise SecondFacteurInvalide(
            "personne n'a encore inscrit de second facteur pour les rôles demandés. "
            "Inscrivez-en un d'abord : une fois le second facteur actif, le code d'inscription "
            "part par courriel, et sans compte d'envoi en service la porte reste close.")
