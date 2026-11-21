"""Lecture partagée par les pages publiques : les parcours visibles, avec leur état d'inscription.

Un seul module pour l'accueil, le catalogue et la page d'un parcours, parce que les trois posent la même
question et doivent y répondre pareil. Une page qui annoncerait « ouvert » là où une autre dit « complet »
est pire qu'une page absente.

**Le masquage de la phase de lancement ne s'applique plus ici**, à dessein : le site est une vitrine,
et l'existence comme le programme des parcours à venir sont l'argument de vente. Un catalogue de neuf
entrées dont huit sont cachées se lit comme un catalogue d'une entrée. Le masquage, lui, continue de
s'appliquer dans le LMS pour l'apprenant connecté — c'est la façade publique, et elle seule, qui s'en
affranchit. Le raisonnement complet est dans `site_api.parcours_du_catalogue`.

`published` reste l'interrupteur : c'est le seul moyen de retirer une page du site, et
`lancement.retirer_parcours_echus` s'en sert chaque nuit.
"""
import frappe

from openlab_academy.entrypoints import site_api

CHAMP_GRATUIT = "parcours_gratuit"


def _usage():
    return site_api._usage()


def parcours_visibles(limite: int | None = None) -> list:
    """Tout le catalogue public : les parcours publiés, les plus récents d'abord."""
    cours = frappe.get_all(
        "LMS Course", {"published": 1},
        ["name", "title", "short_introduction", "image", "category", CHAMP_GRATUIT],
        order_by="creation desc", ignore_permissions=True)
    return cours[:limite] if limite else cours


def avec_offre(cours: list) -> list:
    """Chaque parcours, augmenté de son état d'inscription, de son prix et de sa prochaine session."""
    usage = _usage()
    apprenant = site_api._apprenant()
    enrichis = []
    for parcours in cours:
        offre = usage.offre(parcours.name, apprenant).en_dict()
        enrichis.append({**parcours, "offre": offre, "lien": lien_de(parcours.name)})
    return enrichis


def lien_de(nom: str) -> str:
    """Le lien public d'un parcours. Un seul segment : le nom ne peut pas sortir du préfixe."""
    from urllib.parse import quote
    return "/parcours/" + quote(nom, safe="")


def montant_lisible(montant) -> str:
    """« 250000 » devient « 250 000 F CFA ». L'espace est insécable : un prix ne se coupe pas en fin de
    ligne."""
    if not montant:
        return ""
    return f"{int(montant):,}".replace(",", " ") + " F CFA"


def chiffres(cours: list) -> dict:
    """Ce que l'accueil annonce. Compté, jamais écrit à la main : un chiffre faux sur une page d'accueil
    se voit, et ne se rattrape pas."""
    noms = [c.name for c in cours]
    if not noms:
        return {"parcours": 0, "seances": 0, "gratuits": 0}
    chapitres = frappe.get_all("Course Chapter", {"course": ["in", noms]}, pluck="name",
                               ignore_permissions=True)
    seances = frappe.db.count("Course Lesson", {"chapter": ["in", chapitres]}) if chapitres else 0
    return {
        "parcours": len(noms),
        "seances": seances,
        "gratuits": sum(1 for c in cours if c.get(CHAMP_GRATUIT)),
    }
