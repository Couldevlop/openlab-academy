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
from frappe import _

from openlab_academy.entrypoints import site_api
from openlab_academy.infrastructure import domaines_frappe

CHAMP_GRATUIT = "parcours_gratuit"

# Les quatre états qu'une carte a le droit d'annoncer, et rien d'autre.
#
# « Fermé » a été écarté : pour un parcours dont la conception n'est pas terminée, le mot se lit
# comme un refus alors qu'il s'agit d'une préparation. Un visiteur qui lit « fermé » s'en va ; celui
# qui lit « en préparation » revient. Aucun de ces libellés n'annonce de date : nous n'en tenons
# aucune, et une date manquée coûte plus cher que l'absence de date.
PREPARATION, BIENTOT, OUVERTE, LIBRE = "preparation", "bientot", "ouverte", "libre"


def _usage():
    return site_api._usage()


def parcours_visibles(limite: int | None = None) -> list:
    """Tout le catalogue public : les parcours publiés, les plus récents d'abord."""
    cours = frappe.get_all(
        "LMS Course", {"published": 1},
        ["name", "title", "short_introduction", "image", "category", "upcoming", CHAMP_GRATUIT,
         domaines_frappe.CHAMP],
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


def etat_de(parcours: dict) -> str:
    """L'état honnête d'un parcours, parmi les quatre admis.

    L'ordre compte. « Accès libre » ne se dit que d'un parcours réellement ouvert : pendant une
    suspension, même un parcours gratuit n'accueille personne, et l'annoncer libre serait un
    mensonge que le visiteur découvrirait au clic suivant.
    """
    if parcours.get("upcoming"):
        return PREPARATION
    offre = parcours.get("offre") or {}
    if not offre.get("ouverte"):
        return BIENTOT
    return LIBRE if offre.get("gratuit") else OUVERTE


def libelle_etat(etat: str) -> str:
    return {
        PREPARATION: _("En préparation"),
        BIENTOT: _("Bientôt ouvert"),
        OUVERTE: _("Inscriptions ouvertes"),
        LIBRE: _("Accès libre"),
    }.get(etat, "")


def seances_par_parcours(noms: list) -> dict:
    """Le nombre de séances de chaque parcours, en deux requêtes pour tout le catalogue.

    Compté, jamais estimé : c'est le seul chiffre qui dit la taille d'un parcours sur une carte, et
    une carte qui ment sur la taille fait perdre son temps à celui qui clique.
    """
    if not noms:
        return {}
    chapitres = frappe.get_all("Course Chapter", {"course": ["in", noms]}, ["name", "course"],
                               ignore_permissions=True)
    if not chapitres:
        return {nom: 0 for nom in noms}
    parcours_du_chapitre = {c["name"]: c["course"] for c in chapitres}
    lecons = frappe.get_all("Course Lesson", {"chapter": ["in", list(parcours_du_chapitre)]},
                            pluck="chapter", ignore_permissions=True)
    compte = {nom: 0 for nom in noms}
    for chapitre in lecons:
        compte[parcours_du_chapitre[chapitre]] += 1
    return compte


# Ce qu'on peut faire aujourd'hui passe devant ce qu'on pourra faire un jour. Le catalogue n'a pas
# a classer par merite ni par date : il a a mettre en premier les parcours qu'un visiteur peut
# rejoindre, et a ne pas faire ouvrir la page par celui qui n'accueille personne.
RANG_DES_ETATS = {OUVERTE: 0, LIBRE: 1, BIENTOT: 2, PREPARATION: 3}


def par_etat(cartes: list) -> list:
    """Les cartes rangees par ce qu'on peut en faire, l'ordre d'origine tenant lieu de depart."""
    return sorted(cartes, key=lambda c: RANG_DES_ETATS.get(c["etat"], len(RANG_DES_ETATS)))


def pour_les_cartes(parcours: list) -> list:
    """Les parcours prêts à être posés sur des cartes : famille, teinte, état lisible, taille, prix.

    Tout est calculé ici plutôt que dans le gabarit : une page qui calcule est une page dont on ne
    peut pas éprouver les décisions.
    """
    familles = domaines_frappe.par_cle()
    seances = seances_par_parcours([p["name"] for p in parcours])
    cartes = []
    for p in parcours:
        famille = familles.get(p.get(domaines_frappe.CHAMP) or "")
        etat = etat_de(p)
        cartes.append({
            **p,
            "domaine_libelle": famille.libelle if famille else "",
            "domaine_teinte": famille.teinte if famille else "",
            "etat": etat,
            "etat_libelle": libelle_etat(etat),
            "seances": seances.get(p["name"], 0),
            "prix": montant_lisible((p.get("offre") or {}).get("montant")),
        })
    return cartes


def familles_du_catalogue(cartes: list) -> list:
    """Les familles réellement présentes, avec leur teinte et leur compte.

    Seulement celles qui ont au moins un parcours : un filtre qui ne filtre rien est un bouton qui
    déçoit. L'ordre est celui choisi dans l'administration, pas l'ordre alphabétique.
    """
    comptes: dict[str, int] = {}
    for carte in cartes:
        libelle = carte.get("domaine_libelle")
        if libelle:
            comptes[libelle] = comptes.get(libelle, 0) + 1
    return [{"libelle": d.libelle, "teinte": d.teinte, "compte": comptes[d.libelle]}
            for d in domaines_frappe.tous() if d.libelle in comptes]
