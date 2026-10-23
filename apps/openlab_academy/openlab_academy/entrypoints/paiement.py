"""Points d'accroche de l'inscription (refus des inscriptions tardives ou sans tarif, ouverture du dossier ; rien
pour un parcours gratuit) et de l'enregistrement d'un parcours (dispense des dossiers d'un parcours devenu gratuit),
assemblage du paiement en ligne CinetPay (réglages, liens de retour et de notification) et tâche quotidienne des
rappels (revérification des paiements en attente, puis rappels J-7, J-3, J-1 sur trois canaux)."""
import datetime
from urllib.parse import urlencode, urlsplit

import frappe
from frappe.email.doctype.email_account.email_account import EmailAccount
from frappe.utils import getdate, nowdate, now_datetime
from rq.timeouts import JobTimeoutException

from openlab_academy.application.paiements import (
    AccorderDelai, ChoisirMode, ConfirmerPaiement, DossierAbsent, EnregistrerVirement, InitierPaiement,
    InscriptionTardive, OuvrirDossier, PaiementIndisponible, ReverifierPaiements, TarifAbsent)
from openlab_academy.application.parcours_gratuits import DispenseReservee, DispenserParcoursGratuit, etat_gratuit
from openlab_academy.application.ports_paiement import FiltresTableau
from openlab_academy.application.rappels import EnvoyerRappels
from openlab_academy.application.tableaux_paiement import Fiche, Intendance, Resume, vue_apprenant
from openlab_academy.domain.dossier_paiement import Statut
from openlab_academy.entrypoints.lms import ROLES_NON_BLOQUES
from openlab_academy.infrastructure.canaux import CanalEmail, CanalSms, CanalWhatsApp
from openlab_academy.infrastructure.cinetpay import PasserelleCinetPay
from openlab_academy.infrastructure.depot_dossiers_frappe import (
    DepotDossiersFrappe, InscriptionsFrappe, PagesPaiementFrappe, ParcoursGratuitsFrappe, ReglagesPaiementFrappe,
    TarifsFrappe)
from openlab_academy.infrastructure.journal_paiement_frappe import journaliser
from openlab_academy.infrastructure.rappels_frappe import DepotRappelsFrappe, RegistreRappelsFrappe
from openlab_academy.infrastructure.tableaux_paiement_frappe import TableauxPaiementFrappe

REGLAGES = "Reglages Paiement OpenLab"
API = "/api/method/openlab_academy.entrypoints.paiement_api"


def aujourd_hui() -> datetime.date:
    return datetime.date.today()


def _ouvrir() -> OuvrirDossier:
    return OuvrirDossier(DepotDossiersFrappe(), TarifsFrappe(), ReglagesPaiementFrappe(), aujourd_hui,
                         ParcoursGratuitsFrappe())


def _cohorte(doc):
    """(cours, début, fin) de la cohorte ; None pour un rôle exempté ou une cohorte sans parcours."""
    if ROLES_NON_BLOQUES & set(frappe.get_roles(doc.member)):
        return None
    cours = frappe.db.get_value("Batch Course", {"parent": doc.batch}, "course", order_by="idx")
    if not cours:
        return None
    lot = frappe.db.get_value("LMS Batch", doc.batch, ["start_date", "end_date"], as_dict=True)
    return cours, getdate(lot.start_date), getdate(lot.end_date)


def avant_inscription(doc, method=None) -> None:
    lot = _cohorte(doc)
    if lot is None:
        return
    try:
        _ouvrir().verifier(lot[0], lot[1])
    except (InscriptionTardive, TarifAbsent) as e:
        frappe.throw(str(e), exc=frappe.ValidationError)


def apres_inscription(doc, method=None) -> None:
    lot = _cohorte(doc)
    if lot is not None:
        _ouvrir().executer(doc.member, lot[0], doc.batch, lot[1], lot[2])


ADMINISTRATEUR = "System Manager"


def parcours_enregistre(doc, method=None) -> None:
    """Parcours enregistré : s'il est gratuit, ses dossiers qui ont encore quelque chose à payer sont dispensés
    (journal, auteur = la session), par l'administrateur seulement (sinon l'enregistrement entier est refusé), et
    l'auteur en est informé."""
    utilisateur = frappe.session.user
    try:
        bilan = DispenserParcoursGratuit(DepotDossiersFrappe(), journaliser, ParcoursGratuitsFrappe(), TarifsFrappe(),
                                         jour_courant).executer(utilisateur, doc.name,
                                                                ADMINISTRATEUR in frappe.get_roles(utilisateur))
    except DispenseReservee as e:
        frappe.throw(str(e), frappe.PermissionError)
    messages = []
    if bilan.dispenses:
        messages.append(f"Parcours devenu gratuit : {bilan.dispenses} dossier(s) de paiement dispensé(s), visibles "
                        "dans l'historique de l'intendance.")
    if bilan.tarif_ignore:
        messages.append("Le tarif de ce parcours est conservé mais ne s'applique plus tant qu'il est gratuit.")
    if messages:
        frappe.msgprint(" ".join(messages), alert=True)


# --- paiement en ligne -----------------------------------------------------------------------------------
def passerelle() -> PasserelleCinetPay:
    """Passerelle CinetPay des réglages ; les clés sont lues déchiffrées, sans jamais quitter l'adaptateur."""
    r = frappe.get_single(REGLAGES)
    return PasserelleCinetPay(r.cinetpay_site_id or "", r.get_password("cinetpay_api_key", raise_exception=False) or "",
                              r.get_password("cinetpay_secret", raise_exception=False) or "")


def liens(cours: str) -> tuple[str, str]:
    """(URL de retour, URL de notification) sur l'adresse publique réglée ; indisponible si elle est invalide."""
    base = (frappe.db.get_single_value(REGLAGES, "cinetpay_url_notification_base") or "").strip().rstrip("/")
    parties = urlsplit(base)
    if (parties.scheme not in ("http", "https") or not parties.hostname or "@" in parties.netloc
            or parties.query or parties.fragment):
        raise PaiementIndisponible("Le paiement en ligne n'est pas disponible pour le moment.")
    return (f"{base}{API}.retour_cinetpay?{urlencode({'cours': cours})}", f"{base}{API}.notification_cinetpay")


def initier_paiement(apprenant: str, cours: str) -> str:
    """URL de la page de paiement CinetPay de la part due de la prochaine échéance (celle d'un paiement en attente
    récent au même montant si elle est encore retenue)."""
    return InitierPaiement(DepotDossiersFrappe(), passerelle(), now_datetime, liens,
                           PagesPaiementFrappe()).executer(apprenant, cours)


def paiement_en_ligne(cours: str) -> bool:
    """Vrai si CinetPay est configuré (clés et adresse publique valides)."""
    try:
        liens(cours)
    except PaiementIndisponible:
        return False
    return passerelle().disponible()


def confirmer_paiement(transaction: str, p: PasserelleCinetPay | None = None) -> None:
    ConfirmerPaiement(DepotDossiersFrappe(), p or passerelle(), journaliser,
                      PagesPaiementFrappe()).executer(transaction)


def reconcilier_paiements(apprenant: str, cours: str) -> None:
    ConfirmerPaiement(DepotDossiersFrappe(), passerelle(), journaliser,
                      PagesPaiementFrappe()).reconcilier(apprenant, cours)


# --- virements et délais (intendant, administrateur) -----------------------------------------------------
def jour_courant() -> datetime.date:
    """Date du jour du site (Abidjan = UTC) ; injectée dans les cas d'usage, jamais lue par eux."""
    return getdate(nowdate())


def enregistrer_virement(acteur: str, dossier: str, montant: int, reference: str, date_paiement: datetime.date,
                         motif: str = "") -> None:
    EnregistrerVirement(DepotDossiersFrappe(), journaliser, jour_courant).executer(
        acteur, dossier, montant, reference, date_paiement, motif)


def accorder_delai(acteur: str, dossier: str, jusqu_au: datetime.date, motif: str) -> None:
    AccorderDelai(DepotDossiersFrappe(), journaliser, jour_courant).executer(acteur, dossier, jusqu_au, motif)


# --- lectures et choix de l'apprenant (toujours son propre dossier) ; tableaux de l'intendance -------------
def _titre(cours: str) -> str:
    return frappe.db.get_value("LMS Course", cours, "title") or cours


def mon_dossier(apprenant: str, cours: str) -> dict:
    """Parcours gratuit suivi par l'apprenant : un état calme, même si un dossier (dispensé) existe d'avant la
    gratuité. Sinon son dossier, ou DossierAbsent."""
    if gratuit := etat_gratuit(ParcoursGratuitsFrappe(), InscriptionsFrappe(), apprenant, cours, lambda: _titre(cours)):
        return gratuit
    d = DepotDossiersFrappe().charger(apprenant, cours)
    if d is None:
        raise DossierAbsent("Aucun dossier de paiement pour ce parcours.")
    titre = _titre(cours)
    instructions = frappe.db.get_single_value("Reglages Paiement OpenLab", "instructions_virement")
    return vue_apprenant(d, titre, jour_courant(), paiement_en_ligne(cours), instructions)


def choisir_mode(apprenant: str, cours: str, mode: str, telephone: str) -> None:
    """Le jour d'échéance vient des réglages (10 par défaut)."""
    ChoisirMode(DepotDossiersFrappe(), journaliser, jour_courant,
                ReglagesPaiementFrappe().charger().jour_echeance).executer(apprenant, cours, mode, telephone)


def intendance(filtres: FiltresTableau, statut: Statut | None) -> dict:
    return Intendance(TableauxPaiementFrappe(), jour_courant).executer(filtres, statut)


def fiche(dossier: str) -> dict:
    return Fiche(DepotDossiersFrappe(), TableauxPaiementFrappe(), jour_courant).executer(dossier)


def resume() -> dict:
    return Resume(TableauxPaiementFrappe(), jour_courant).executer()


# --- tâche quotidienne : revérification des paiements en attente, rappels ----------------------------------
POINT_RAPPEL = "openlab_rappel"


def _alerte(titre: str, detail: str) -> None:
    frappe.log_error(titre, detail)


FATALES = (JobTimeoutException,)  # délai de la tâche dépassé : jamais avalé, RQ doit l'arrêter


def _transaction(action):
    """Une étape par transaction, validée aussitôt (planification d'un dossier, réservation d'un envoi, envoi et
    statut, contrôle d'un paiement) : une erreur n'annule que ses écritures (toute la transaction en cours si le
    point de sauvegarde est perdu, après un interblocage) puis remonte."""
    frappe.db.savepoint(POINT_RAPPEL)
    try:
        resultat = action()
    except Exception:
        try:
            frappe.db.rollback(save_point=POINT_RAPPEL)
        except Exception:
            frappe.db.rollback()
        raise
    frappe.db.commit()
    return resultat


def canaux() -> tuple:
    """E-mail, SMS, WhatsApp ; les secrets sont lus déchiffrés et ne quittent que l'adaptateur."""
    r = frappe.get_single(REGLAGES)

    def secret(champ: str) -> str:
        return r.get_password(champ, raise_exception=False) or ""
    return (CanalEmail(frappe.sendmail, lambda: bool(EmailAccount.find_default_outgoing())),
            CanalSms(r.sms_url_jeton or "", r.sms_client_id or "", secret("sms_client_secret"), r.sms_expediteur or ""),
            CanalWhatsApp(r.whatsapp_phone_id or "", secret("whatsapp_jeton"), r.whatsapp_modele or ""))


def reverifier_paiements() -> int:
    """Paiements CinetPay en attente depuis moins de 7 jours, revérifiés via /v2/payment/check (notification perdue)."""
    p = passerelle()
    if not p.disponible():
        return 0
    depot = DepotDossiersFrappe()
    confirmer = ConfirmerPaiement(depot, p, journaliser, PagesPaiementFrappe())
    return ReverifierPaiements(depot, confirmer, now_datetime, alerte=_alerte,
                               unite=_transaction, fatales=FATALES).executer()


def envoyer_rappels() -> None:
    """Échéancier (08:00, Abidjan = UTC) : la file par défaut coupe à 300 s ; le travail part dans la file longue,
    une seule fois même si l'échéancier le redemande pendant qu'il tourne."""
    frappe.enqueue(f"{__name__}._executer_rappels", queue="long", timeout=3600, job_id="openlab_rappels",
                   deduplicate=True)


def _executer_rappels() -> int:
    """Revérifie les paiements en attente puis envoie les rappels dus ; renvoie le nombre de rappels envoyés."""
    try:
        reverifier_paiements()  # un paiement arrivé sans notification ne doit pas valoir de rappel
    except FATALES:
        raise
    except Exception as e:
        frappe.log_error("Paiements en ligne non revérifiés", type(e).__name__)
    return EnvoyerRappels(DepotRappelsFrappe(), canaux(), RegistreRappelsFrappe(), jour_courant,
                          delais=ReglagesPaiementFrappe().charger().delais_rappel, alerte=_alerte,
                          unite=_transaction, fatales=FATALES).executer()
