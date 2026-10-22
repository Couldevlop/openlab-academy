"""Cas d'usage du paiement : ouverture du dossier à l'inscription, choix et changement de mode (faux ports)."""
import unittest
from dataclasses import replace
from datetime import date, datetime, timedelta

from openlab_academy.application.paiements import (
    AccorderDelai, ChoisirMode, ConfirmerPaiement, DossierAbsent, EnregistrerVirement, InitierPaiement,
    InscriptionTardive, OperationRefusee, OuvrirDossier, PaiementIndisponible, REUTILISATION, RienADu, TarifAbsent,
    TelephoneInvalide, montant_a_payer, valider_telephone)
from openlab_academy.application.ports_paiement import (
    Client, DossierEnregistre, PaiementEnregistre, ReferenceDejaEnregistree, ReglagesPaiement, Verification)
from openlab_academy.domain.dossier_paiement import Dossier, Statut, bloque, statut
from openlab_academy.domain.echeancier import Echeance, Mode, Tarif, TarifInvalide

TARIF = Tarif(10000, 100000, 110000, 120000)
DEBUT, FIN = date(2026, 11, 2), date(2027, 2, 22)
AUJOURDHUI = date(2026, 10, 22)


class Depot:
    def __init__(self):
        self.dossiers, self.payes, self.noms = {}, {}, 0
        self.remplacements, self.telephones = [], []
        self.paiements = {}

    def charger(self, apprenant, cours):
        return self.dossiers.get((apprenant, cours))

    def creer(self, d):
        self.noms += 1
        nom = f"D{self.noms}"
        self.payes.setdefault(nom, 0)
        self.dossiers[(d.apprenant, d.cours)] = DossierEnregistre(
            nom, d.apprenant, d.cours, d.mode, "", d.tarif, DEBUT, FIN,
            Dossier(d.echeances, 0, frais_inscription=d.tarif.frais_inscription), d.inscription)
        self.dernier = d
        return nom

    def remplacer_echeances(self, nom, mode, echeances):
        self.remplacements.append((nom, mode, echeances))

    def fixer_telephone(self, nom, telephone):
        self.telephones.append((nom, telephone))

    def paye(self, nom):
        return self.payes[nom] + sum(p.montant for p in self.paiements.values()
                                     if p.dossier == nom and p.statut == "confirme")

    def client(self, apprenant):
        return Client(nom="Kouassi", prenom="Aya", email=apprenant)

    def creer_paiement(self, dossier, montant, moyen, reference, statut):
        self.crees = getattr(self, "crees", {})
        nom = f"P{len(self.paiements) + 1}"
        self.paiements[(moyen, reference)] = PaiementEnregistre(nom, dossier, montant, statut)
        return nom

    def paiement(self, moyen, reference):
        return self.paiements.get((moyen, reference))

    def confirmer_paiement(self, moyen, reference, montant):
        p = self.paiements.get((moyen, reference))
        if p is None or p.statut == "confirme":
            return False
        self.paiements[(moyen, reference)] = replace(p, montant=montant, statut="confirme")
        return True

    def paiement_en_attente_recent(self, dossier, moyen, montant, depuis):
        self.recherches = getattr(self, "recherches", []) + [(dossier, moyen, montant, depuis)]
        return next((r for (m, r), p in reversed(self.paiements.items())
                     if m == moyen and p.dossier == dossier and p.montant == montant and p.statut == "en_attente"
                     and self.crees.get(r, MAINTENANT) >= depuis), None)

    def paiements_en_attente(self, dossier, moyen, limite):
        return tuple(r for (m, r), p in self.paiements.items()
                     if m == moyen and p.dossier == dossier and p.statut == "en_attente")[:limite]

    def marquer_echoue(self, moyen, reference):
        p = self.paiements[(moyen, reference)]
        if p.statut == "en_attente":
            self.paiements[(moyen, reference)] = replace(p, statut="echoue")

    def par_nom(self, nom):
        return next((d for d in self.dossiers.values() if d.nom == nom), None)

    def fixer_delai(self, nom, d):
        self.delais = getattr(self, "delais", []) + [(nom, d)]
        for cle, e in self.dossiers.items():
            if e.nom == nom:
                self.dossiers[cle] = replace(e, dossier=replace(e.dossier, delai_jusqu_au=d))

    def enregistrer_virement(self, dossier, montant, reference, date_paiement, auteur):
        if ("virement", reference) in self.paiements:
            raise ReferenceDejaEnregistree(reference)
        self.paiements[("virement", reference)] = PaiementEnregistre(f"P{len(self.paiements) + 1}", dossier, montant,
                                                                      "confirme")
        for cle, e in self.dossiers.items():
            if e.nom == dossier:
                self.dossiers[cle] = replace(e, dossier=replace(e.dossier, paye=e.dossier.paye + montant))
        self.virements = getattr(self, "virements", []) + [(dossier, montant, reference, date_paiement, auteur)]


class Tarifs:
    def __init__(self, tarif=TARIF):
        self.tarif = tarif

    def charger(self, cours):
        return self.tarif


class Reglages:
    def __init__(self, r=ReglagesPaiement()):
        self.r = r

    def charger(self):
        return self.r


def ouvrir(depot, tarif=TARIF, aujourd_hui=AUJOURDHUI, reglages=ReglagesPaiement()):
    return OuvrirDossier(depot, Tarifs(tarif), Reglages(reglages), lambda: aujourd_hui)


class TestOuvrirDossier(unittest.TestCase):
    def test_cree_un_dossier_aux_prix_figes_avec_la_seule_echeance_des_frais(self):
        depot = Depot()
        nom = ouvrir(depot).executer("a@x.ci", "C", "B1", DEBUT, FIN)
        d = depot.dernier
        self.assertEqual((nom, d.mode, d.tarif, d.inscription, d.cohorte), ("D1", Mode.UNE_FOIS, TARIF, AUJOURDHUI, "B1"))
        self.assertEqual(d.echeances, (Echeance(AUJOURDHUI, 10000, "Frais d'inscription"),))

    def test_dossier_existant_renvoye_sans_changement(self):
        depot = Depot()
        cas = ouvrir(depot)
        premier = cas.executer("a@x.ci", "C", "B1", DEBUT, FIN)
        self.assertEqual(cas.executer("a@x.ci", "C", "B2", DEBUT, FIN), premier)
        self.assertEqual(depot.noms, 1)

    def test_tarif_modifie_ensuite_sans_effet_sur_le_dossier(self):
        depot = Depot()
        ouvrir(depot).executer("a@x.ci", "C", "B1", DEBUT, FIN)
        ouvrir(depot, Tarif(20000, 200000, 210000, 220000)).executer("b@x.ci", "C", "B1", DEBUT, FIN)
        self.assertEqual(depot.dossiers[("a@x.ci", "C")].tarif, TARIF)

    def test_inscription_trop_tardive_refusee(self):
        with self.assertRaisesRegex(InscriptionTardive, "Les inscriptions à cette cohorte sont closes"):
            ouvrir(Depot(), aujourd_hui=date(2027, 1, 3)).executer("a@x.ci", "C", "B1", DEBUT, FIN)

    def test_derniere_journee_permise(self):
        ouvrir(Depot(), aujourd_hui=date(2027, 1, 2)).executer("a@x.ci", "C", "B1", DEBUT, FIN)

    def test_delai_de_grace_lu_dans_les_reglages(self):
        cas = ouvrir(Depot(), aujourd_hui=date(2027, 1, 3), reglages=ReglagesPaiement(10, 3))
        cas.executer("a@x.ci", "C", "B1", DEBUT, FIN)

    def test_parcours_sans_tarif_refuse(self):
        with self.assertRaisesRegex(TarifAbsent, "pas encore de tarif"):
            ouvrir(Depot(), tarif=None).executer("a@x.ci", "C", "B1", DEBUT, FIN)

    def test_tarif_invalide_refuse_avant_figement(self):
        depot = Depot()
        with self.assertRaises(TarifInvalide):
            ouvrir(depot, Tarif(10003, 100000, 110000, 120000)).executer("a@x.ci", "C", "B1", DEBUT, FIN)
        self.assertEqual(depot.noms, 0)


class Journal:
    def __init__(self):
        self.appels = []

    def __call__(self, dossier, acteur, action, avant, apres, motif=""):
        self.appels.append((dossier, acteur, action, avant, apres, motif))


def depot_ouvert(paye=0, mode=Mode.UNE_FOIS):
    depot = Depot()
    ouvrir(depot).executer("a@x.ci", "C", "B1", DEBUT, FIN)
    d = depot.dossiers[("a@x.ci", "C")]
    depot.dossiers[("a@x.ci", "C")] = replace(d, mode=mode, dossier=replace(d.dossier, paye=paye))
    return depot


def depot_en_retard():
    """Deux tranches, frais payés ; la tranche du 10/11 reste impayée (bloquée à partir du 11/11)."""
    depot = depot_ouvert(paye=10000, mode=Mode.DEUX_TRANCHES)
    d = depot.dossiers[("a@x.ci", "C")]
    echeances = (Echeance(AUJOURDHUI, 10000, "Frais d'inscription"), Echeance(date(2026, 11, 10), 50000, "Échéance"),
                 Echeance(date(2026, 12, 10), 50000, "Échéance"))
    depot.dossiers[("a@x.ci", "C")] = replace(d, dossier=replace(d.dossier, echeances=echeances))
    return depot


class TestChoisirMode(unittest.TestCase):
    def cas(self, depot, jour=10, aujourd_hui=AUJOURDHUI):
        self.journal = Journal()
        return ChoisirMode(depot, self.journal, lambda: aujourd_hui, jour)

    def test_rien_de_paye_conserve_la_ligne_des_frais_datee_a_l_inscription(self):
        depot = depot_ouvert()
        echeances = self.cas(depot).executer("a@x.ci", "C", "mensuel", "+225 07 00 00 00 00")
        self.assertEqual(echeances[0], Echeance(AUJOURDHUI, 10000, "Frais d'inscription"))
        self.assertEqual(sum(e.montant for e in echeances), 120000)
        self.assertEqual(depot.remplacements, [("D1", Mode.MENSUEL, echeances)])
        self.assertEqual(depot.telephones, [("D1", "+2250700000000")])

    def test_apres_un_paiement_le_calendrier_est_replanifie(self):
        depot = depot_ouvert(paye=10000)
        echeances = self.cas(depot).executer("a@x.ci", "C", "deux_tranches", "+2250700000000")
        self.assertEqual(echeances[0], Echeance(AUJOURDHUI, 10000, "Déjà versé"))
        self.assertEqual(echeances[1].date_limite, date(2026, 11, 10))
        self.assertEqual(sum(e.montant for e in echeances), 110000)

    def test_journal_acteur_et_avant_apres(self):
        depot = depot_ouvert()
        echeances = self.cas(depot).executer("a@x.ci", "C", "mensuel", "+2250700000000")
        (dossier, acteur, action, avant, apres, motif), = self.journal.appels
        self.assertEqual((dossier, acteur, action, motif), ("D1", "a@x.ci", "mode", ""))
        self.assertEqual(avant, {"mode": "une_fois", "echeances": [["2026-10-22", 10000, "Frais d'inscription"]]})
        self.assertEqual(apres["mode"], "mensuel")
        self.assertEqual(len(apres["echeances"]), len(echeances))

    def test_jour_d_echeance_regle(self):
        echeances = self.cas(depot_ouvert(), jour=5).executer("a@x.ci", "C", "deux_tranches", "+2250700000000")
        self.assertEqual({e.date_limite.day for e in echeances[1:]}, {5})

    def test_telephone_invalide_refuse_sans_rien_ecrire(self):
        depot = depot_ouvert()
        with self.assertRaisesRegex(TelephoneInvalide, "Numéro de téléphone invalide"):
            self.cas(depot).executer("a@x.ci", "C", "mensuel", "0700000000")
        self.assertEqual((depot.remplacements, self.journal.appels), ([], []))

    def test_meme_mode_ne_change_que_le_telephone(self):
        depot = depot_ouvert(paye=10000)
        avant = depot.dossiers[("a@x.ci", "C")].dossier.echeances
        echeances = self.cas(depot).executer("a@x.ci", "C", "une_fois", "+225 05 01 02 03 04")
        self.assertEqual(echeances, avant)
        self.assertEqual(depot.remplacements, [])
        self.assertEqual(depot.telephones, [("D1", "+2250501020304")])
        self.assertEqual(self.journal.appels, [])

    def test_meme_mode_en_retard_reste_bloque(self):
        """Échéance du 10/11 impayée le 20/11 : réenregistrer le même mode ne l'efface pas."""
        depot = depot_en_retard()
        d = depot.dossiers[("a@x.ci", "C")]
        self.assertTrue(bloque(d.dossier, date(2026, 11, 20)))
        echeances = self.cas(depot, aujourd_hui=date(2026, 11, 20)).executer("a@x.ci", "C", "deux_tranches",
                                                                            "+2250700000000")
        self.assertEqual(echeances, d.dossier.echeances)
        self.assertEqual(depot.remplacements, [])
        self.assertTrue(bloque(replace(d.dossier, echeances=echeances), date(2026, 11, 20)))

    def test_changement_de_mode_refuse_tant_qu_une_echeance_passee_est_impayee(self):
        for depot in (depot_en_retard(), depot_ouvert()):  # tranche du 10/11, ou frais du 22/10, impayés le 20/11
            with self.subTest(mode=depot.dossiers[("a@x.ci", "C")].mode):
                avant = depot.dossiers[("a@x.ci", "C")]
                with self.assertRaisesRegex(OperationRefusee, "^Réglez d'abord l'échéance en retard, ou contactez "
                                                              "l'intendance.$"):
                    self.cas(depot, aujourd_hui=date(2026, 11, 20)).executer("a@x.ci", "C", "mensuel",
                                                                            "+2250700000000")
                self.assertEqual((depot.remplacements, depot.telephones, self.journal.appels), ([], [], []))
                self.assertEqual(depot.dossiers[("a@x.ci", "C")], avant)

    def test_frais_du_jour_n_empechent_pas_de_choisir_son_mode(self):
        depot = depot_ouvert()
        echeances = self.cas(depot, aujourd_hui=AUJOURDHUI).executer("a@x.ci", "C", "mensuel", "+2250700000000")
        self.assertEqual(depot.remplacements, [("D1", Mode.MENSUEL, echeances)])

    def test_mode_inconnu_refuse(self):
        with self.assertRaises(ValueError):
            self.cas(depot_ouvert()).executer("a@x.ci", "C", "trimestriel", "+2250700000000")

    def test_dossier_absent(self):
        with self.assertRaises(DossierAbsent):
            self.cas(Depot()).executer("a@x.ci", "C", "mensuel", "+2250700000000")


class Passerelle:
    def __init__(self, disponible=True, verification=Verification("confirme", 10000), erreur=None):
        self._disponible = disponible
        self.verification = verification
        self.erreur = erreur
        self.initiations, self.verifications = [], []

    def disponible(self):
        return self._disponible

    def initier(self, transaction, montant, description, client, retour, notification):
        self.initiations.append((transaction, montant, description, client, retour, notification))
        if self.erreur:
            raise self.erreur
        return f"https://checkout.cinetpay.com/{transaction}"

    def verifier(self, transaction):
        self.verifications.append(transaction)
        if self.erreur:
            raise self.erreur
        return self.verification


MAINTENANT = datetime(2026, 10, 22, 9, 30, 15, 123456)
REFERENCE = "OLA-D1-20261022093015123456"


def liens(cours):
    return f"https://academy.ci/retour?cours={cours}", "https://academy.ci/notif"


def initier(depot, passerelle=None):
    return InitierPaiement(depot, passerelle or Passerelle(), lambda: MAINTENANT, liens)


def modifier(depot, **champs):
    d = depot.dossiers[("a@x.ci", "C")]
    depot.dossiers[("a@x.ci", "C")] = replace(d, dossier=replace(d.dossier, **champs))
    return depot


class TestInitierPaiement(unittest.TestCase):
    def test_frais_d_abord_paiement_en_attente_et_url(self):
        depot, passerelle = depot_ouvert(), Passerelle()
        url = initier(depot, passerelle).executer("a@x.ci", "C")
        self.assertEqual(url, f"https://checkout.cinetpay.com/{REFERENCE}")
        self.assertEqual(depot.paiements, {("cinetpay", REFERENCE): PaiementEnregistre("P1", "D1", 10000, "en_attente")})
        (transaction, montant, description, client, retour, notification), = passerelle.initiations
        self.assertEqual((transaction, montant), (REFERENCE, 10000))
        self.assertEqual(description, "C - Frais d'inscription")
        self.assertEqual(client, Client(nom="Kouassi", prenom="Aya", email="a@x.ci"))
        self.assertEqual((retour, notification), ("https://academy.ci/retour?cours=C", "https://academy.ci/notif"))

    def test_part_de_la_prochaine_echeance_arrondie_au_multiple_de_5_superieur(self):
        echeances = (Echeance(AUJOURDHUI, 10000, "Frais"), Echeance(date(2026, 11, 10), 50000, "Tranche 1"),
                     Echeance(date(2026, 12, 10), 50000, "Tranche 2"))
        depot = modifier(depot_ouvert(), echeances=echeances, paye=10003)
        passerelle = Passerelle()
        initier(depot, passerelle).executer("a@x.ci", "C")
        self.assertEqual(passerelle.initiations[0][1], 50000)  # reste 49 997 -> 50 000
        self.assertEqual(passerelle.initiations[0][2], "C - Tranche 1")

    def test_au_moins_les_frais_restants(self):
        echeances = (Echeance(AUJOURDHUI, 10000, "Frais"), Echeance(AUJOURDHUI, 5000, "Acompte"))
        depot = modifier(depot_ouvert(), echeances=echeances, paye=12000)
        modifier(depot, frais_inscription=20000)
        passerelle = Passerelle()
        initier(depot, passerelle).executer("a@x.ci", "C")
        self.assertEqual(passerelle.initiations[0][1], 8000)

    def test_frais_superieurs_au_calendrier(self):
        depot = modifier(depot_ouvert(), paye=10000, frais_inscription=20000)
        passerelle = Passerelle()
        initier(depot, passerelle).executer("a@x.ci", "C")
        self.assertEqual(passerelle.initiations[0][1:3], (10000, "C - Frais d'inscription"))

    def test_telephone_du_dossier_transmis(self):
        depot = depot_ouvert()
        depot.dossiers[("a@x.ci", "C")] = replace(depot.dossiers[("a@x.ci", "C")], telephone="+2250700000000")
        passerelle = Passerelle()
        initier(depot, passerelle).executer("a@x.ci", "C")
        self.assertEqual(passerelle.initiations[0][3].telephone, "+2250700000000")

    def test_passerelle_non_configuree(self):
        depot = depot_ouvert()
        with self.assertRaises(PaiementIndisponible):
            initier(depot, Passerelle(disponible=False)).executer("a@x.ci", "C")
        self.assertEqual(depot.paiements, {})

    def test_echec_de_l_initiation_marque_le_paiement_echoue(self):
        depot = depot_ouvert()
        with self.assertRaises(PaiementIndisponible):
            initier(depot, Passerelle(erreur=PaiementIndisponible("CinetPay injoignable"))).executer("a@x.ci", "C")
        self.assertEqual(depot.paiements[("cinetpay", REFERENCE)].statut, "echoue")

    def test_dossier_absent(self):
        with self.assertRaises(DossierAbsent):
            initier(Depot()).executer("a@x.ci", "C")

    def test_rien_a_payer(self):
        for depot in (modifier(depot_ouvert(), paye=10000), modifier(depot_ouvert(), dispense=True)):
            with self.subTest(), self.assertRaises(RienADu):
                initier(depot).executer("a@x.ci", "C")
            self.assertEqual(depot.paiements, {})


class Pages:
    """Mémoire des pages de paiement : référence -> URL."""

    def __init__(self):
        self.urls, self.retenues = {}, []

    def lire(self, reference):
        return self.urls.get(reference)

    def retenir(self, reference, url, secondes):
        self.urls[reference] = url
        self.retenues.append((reference, url, secondes))

    def oublier(self, reference):
        self.urls.pop(reference, None)


class TestReutilisation(unittest.TestCase):
    """Un double clic sur « Payer » ne crée pas une seconde transaction : la page CinetPay d'un paiement en attente
    récent (même dossier, même montant, moins de 30 minutes) est rendue telle que CinetPay l'a fournie."""

    def payer(self, depot, pages, passerelle, maintenant=MAINTENANT):
        return InitierPaiement(depot, passerelle, lambda: maintenant, liens, pages).executer("a@x.ci", "C")

    def test_fenetre_de_15_minutes(self):
        self.assertEqual(REUTILISATION, timedelta(minutes=15))

    def test_second_clic_rend_la_meme_page_sans_nouvelle_transaction(self):
        depot, pages, passerelle = depot_ouvert(), Pages(), Passerelle()
        premiere = self.payer(depot, pages, passerelle)
        seconde = self.payer(depot, pages, passerelle, MAINTENANT + timedelta(minutes=14))
        self.assertEqual(seconde, premiere)
        self.assertEqual(len(passerelle.initiations), 1)
        self.assertEqual(len(depot.paiements), 1)
        self.assertEqual(pages.retenues, [(REFERENCE, premiere, 900)])
        self.assertEqual(depot.recherches[-1], ("D1", "cinetpay", 10000, MAINTENANT - timedelta(minutes=1)))

    def test_paiement_trop_ancien_nouvelle_transaction(self):
        depot, pages, passerelle = depot_ouvert(), Pages(), Passerelle()
        self.payer(depot, pages, passerelle)
        depot.crees[REFERENCE] = MAINTENANT - timedelta(minutes=16)
        self.payer(depot, pages, passerelle, MAINTENANT + timedelta(seconds=1))
        self.assertEqual(len(passerelle.initiations), 2)

    def test_montant_different_ou_paiement_non_en_attente_nouvelle_transaction(self):
        depot, pages, passerelle = depot_ouvert(), Pages(), Passerelle()
        self.payer(depot, pages, passerelle)
        depot.marquer_echoue("cinetpay", REFERENCE)
        self.payer(depot, pages, passerelle, MAINTENANT + timedelta(seconds=1))
        modifier(depot, paye=5000)
        self.payer(depot, pages, passerelle, MAINTENANT + timedelta(seconds=2))
        self.assertEqual([i[1] for i in passerelle.initiations], [10000, 10000, 5000])

    def test_page_oubliee_nouvelle_transaction(self):
        depot, pages, passerelle = depot_ouvert(), Pages(), Passerelle()
        self.payer(depot, pages, passerelle)
        pages.urls.clear()
        self.payer(depot, pages, passerelle, MAINTENANT + timedelta(seconds=1))
        self.assertEqual(len(passerelle.initiations), 2)

    def test_echec_rien_retenu(self):
        depot, pages = depot_ouvert(), Pages()
        with self.assertRaises(PaiementIndisponible):
            self.payer(depot, pages, Passerelle(erreur=PaiementIndisponible("CinetPay injoignable")))
        self.assertEqual(pages.retenues, [])


class TestMontantAPayer(unittest.TestCase):
    def test_part_prochaine_au_moins_les_frais_restants_multiple_de_5(self):
        echeances = (Echeance(AUJOURDHUI, 10000, "Frais"), Echeance(date(2026, 11, 10), 50000, "Tranche 1"))
        self.assertEqual(montant_a_payer(Dossier(echeances, 10003, frais_inscription=10000)), 50000)
        self.assertEqual(montant_a_payer(Dossier(echeances, 0, frais_inscription=10000)), 10000)
        self.assertEqual(montant_a_payer(Dossier(echeances[:1], 10000, frais_inscription=20000)), 10000)
        self.assertEqual(montant_a_payer(Dossier(echeances, 60000, frais_inscription=10000)), 0)
        self.assertEqual(montant_a_payer(Dossier(echeances, 0, dispense=True, frais_inscription=10000)), 0)


class TestConfirmerPaiement(unittest.TestCase):
    def setUp(self):
        self.depot = depot_ouvert()
        self.depot.creer_paiement("D1", 10000, "cinetpay", REFERENCE, "en_attente")
        self.journal = Journal()

    def confirmer(self, passerelle):
        ConfirmerPaiement(self.depot, passerelle, self.journal).executer(REFERENCE)

    def test_confirme_et_journalise(self):
        self.confirmer(Passerelle())
        self.assertEqual(self.depot.paiement("cinetpay", REFERENCE).statut, "confirme")
        self.assertEqual(self.journal.appels, [("D1", "CinetPay", "paiement_confirme",
                                                {"statut": "en_attente", "paye": 0, "montant": 10000},
                                                {"statut": "confirme", "paye": 10000, "montant": 10000}, "")])

    def test_meme_notification_deux_fois_un_seul_paiement(self):
        passerelle = Passerelle()
        self.confirmer(passerelle)
        self.confirmer(passerelle)
        self.assertEqual(self.depot.paye("D1"), 10000)
        self.assertEqual(len(self.journal.appels), 1)
        self.assertEqual(passerelle.verifications, [REFERENCE])  # déjà confirmé : pas de second contrôle

    def test_course_perdue_rien_journalise(self):
        self.depot.confirmer_paiement = lambda *a: False  # une notification concurrente a confirmé avant
        self.confirmer(Passerelle())
        self.assertEqual(self.journal.appels, [])

    def test_montant_verifie_et_non_demande(self):
        echeances = (Echeance(AUJOURDHUI, 10000, "Frais"), Echeance(date(2026, 10, 10), 177500, "Solde"))
        modifier(self.depot, echeances=echeances)
        self.confirmer(Passerelle(verification=Verification("confirme", 100000)))
        self.assertEqual(self.depot.paiement("cinetpay", REFERENCE).montant, 100000)
        self.assertEqual(self.journal.appels[0][4]["montant"], 100000)
        d = self.depot.charger("a@x.ci", "C").dossier
        self.assertEqual(statut(replace(d, paye=self.depot.paye("D1")), AUJOURDHUI), Statut.EN_RETARD)

    def test_refuse_oublie_la_page_retenue(self):
        pages = Pages()
        pages.retenir(REFERENCE, "https://checkout.cinetpay.com/x", 900)
        ConfirmerPaiement(self.depot, Passerelle(verification=Verification("echoue", 0)), self.journal,
                          pages).executer(REFERENCE)
        self.assertIsNone(pages.lire(REFERENCE))

    def test_en_attente_garde_la_page_retenue(self):
        pages = Pages()
        pages.retenir(REFERENCE, "https://checkout.cinetpay.com/x", 900)
        ConfirmerPaiement(self.depot, Passerelle(verification=Verification("en_attente", 0)), self.journal,
                          pages).executer(REFERENCE)
        self.assertEqual(pages.lire(REFERENCE), "https://checkout.cinetpay.com/x")

    def test_refuse_marque_echoue_sans_journal(self):
        self.confirmer(Passerelle(verification=Verification("echoue", 0)))
        self.assertEqual(self.depot.paiement("cinetpay", REFERENCE).statut, "echoue")
        self.assertEqual((self.depot.paye("D1"), self.journal.appels), (0, []))

    def test_en_attente_ne_change_rien(self):
        self.confirmer(Passerelle(verification=Verification("en_attente", 0)))
        self.assertEqual(self.depot.paiement("cinetpay", REFERENCE).statut, "en_attente")

    def test_montant_nul_jamais_confirme(self):
        self.confirmer(Passerelle(verification=Verification("confirme", 0)))
        self.assertEqual(self.depot.paiement("cinetpay", REFERENCE).statut, "en_attente")
        self.assertEqual(self.journal.appels, [])

    def test_transaction_inconnue_ignoree(self):
        passerelle = Passerelle()
        ConfirmerPaiement(self.depot, passerelle, self.journal).executer("OLA-inconnue")
        self.assertEqual((passerelle.verifications, self.journal.appels), ([], []))


class TestReconcilier(unittest.TestCase):
    def test_reverifie_les_paiements_en_attente_du_parcours_dans_la_limite(self):
        depot, journal, passerelle = depot_ouvert(), Journal(), Passerelle()
        for i in range(3):
            depot.creer_paiement("D1", 10000, "cinetpay", f"R{i}", "en_attente")
        depot.creer_paiement("D1", 10000, "cinetpay", "R9", "echoue")
        depot.creer_paiement("D9", 10000, "cinetpay", "AUTRE", "en_attente")
        ConfirmerPaiement(depot, passerelle, journal).reconcilier("a@x.ci", "C", limite=2)
        self.assertEqual(passerelle.verifications, ["R0", "R1"])

    def test_sans_dossier_rien(self):
        passerelle = Passerelle()
        ConfirmerPaiement(Depot(), passerelle, Journal()).reconcilier("a@x.ci", "C")
        self.assertEqual(passerelle.verifications, [])


class TestTelephone(unittest.TestCase):
    def test_formats_acceptes(self):
        self.assertEqual(valider_telephone("+225 0700000000"), "+2250700000000")
        self.assertEqual(valider_telephone("+33 6 12 34 56 78"), "+33612345678")
        self.assertEqual(valider_telephone("+12345678"), "+12345678")

    def test_formats_refuses(self):
        for numero in ("", "0700000000", "+22507000000", "+225070000000000", "+1234567", "+1234567890123456",
                       "+225070000000a", "+33 abc"):
            with self.subTest(numero=numero), self.assertRaises(TelephoneInvalide):
                valider_telephone(numero)


def en_retard(paye=0):
    """Dossier dont les frais (10000) sont échus : bloqué tant que rien n'est payé."""
    return depot_ouvert(paye)


class TestEnregistrerVirement(unittest.TestCase):
    def cas(self, depot, aujourd_hui=AUJOURDHUI):
        self.journal = Journal()
        return EnregistrerVirement(depot, self.journal, lambda: aujourd_hui)

    def virer(self, depot=None, **champs):
        depot = depot or en_retard()
        args = {"acteur": "int@x.ci", "dossier": "D1", "montant": 10000, "reference": "VIR-1",
                "date_paiement": date(2026, 10, 20), "motif": "Virement reçu"} | champs
        self.cas(depot).executer(**args)
        return depot

    def test_virement_confirme_debloque_le_dossier_et_journalise_l_acteur(self):
        depot = en_retard()
        self.assertEqual(statut(depot.par_nom("D1").dossier, AUJOURDHUI), Statut.EN_RETARD)
        self.virer(depot, reference="  VIR-1  ")
        self.assertEqual(depot.virements, [("D1", 10000, "VIR-1", date(2026, 10, 20), "int@x.ci")])
        self.assertEqual(statut(depot.par_nom("D1").dossier, AUJOURDHUI), Statut.SOLDE)
        d, acteur, action, avant, apres, motif = self.journal.appels[0]
        self.assertEqual((d, acteur, action, motif), ("D1", "int@x.ci", "virement_enregistre", "Virement reçu"))
        self.assertEqual(avant, {"paye": 0, "statut": "en_retard"})
        self.assertEqual((apres["paye"], apres["statut"], apres["montant"], apres["reference"]),
                         (10000, "solde", 10000, "VIR-1"))

    def test_motif_obligatoire(self):
        for motif in ("", "   ", None):
            depot = en_retard()
            with self.subTest(motif=motif), self.assertRaisesRegex(OperationRefusee, "Le motif est obligatoire."):
                self.virer(depot, motif=motif)
            self.assertFalse(hasattr(depot, "virements"))
        self.virer(motif="  Relevé  ")
        self.assertEqual(self.journal.appels[0][5], "Relevé")

    def test_dossier_inconnu_ou_dispense_refuse(self):
        with self.assertRaises(DossierAbsent):
            self.virer(dossier="D9")
        depot = en_retard()
        depot.dossiers[("a@x.ci", "C")] = replace(depot.dossiers[("a@x.ci", "C")],
                                                  dossier=Dossier((), 0, dispense=True))
        with self.assertRaisesRegex(OperationRefusee, "dispensé"):
            self.virer(depot)
        self.assertFalse(hasattr(depot, "virements"))

    def test_montant_entier_positif_seulement(self):
        for montant in (0, -5, 10.0, 10000.5, "10000", True, None):
            with self.subTest(montant=montant), self.assertRaisesRegex(OperationRefusee, "montant"):
                self.virer(montant=montant)

    def test_reference_obligatoire_et_bornee(self):
        for ref in ("", "   ", None, 12, "x" * 141):
            with self.subTest(ref=ref), self.assertRaisesRegex(OperationRefusee, "référence"):
                self.virer(reference=ref)
        self.virer(reference="x" * 140)

    def test_reference_en_double_refusee_avec_message_clair(self):
        depot = self.virer()
        with self.assertRaisesRegex(OperationRefusee, "Cette référence de virement est déjà enregistrée."):
            self.virer(depot, reference=" VIR-1")
        self.assertEqual(len(depot.virements), 1)
        self.assertEqual(len(self.journal.appels), 0)

    def test_date_future_ou_invalide_refusee(self):
        for jour in (date(2026, 10, 23), "2026-10-20", None, datetime(2026, 10, 20, 8)):
            with self.subTest(jour=jour), self.assertRaisesRegex(OperationRefusee, "date"):
                self.virer(date_paiement=jour)
        self.virer(date_paiement=AUJOURDHUI)

    def test_motif_trop_long_refuse(self):
        with self.assertRaisesRegex(OperationRefusee, "motif"):
            self.virer(motif="m" * 501)
        with self.assertRaisesRegex(OperationRefusee, "motif"):
            self.virer(motif=3)


class TestAccorderDelai(unittest.TestCase):
    def cas(self, depot):
        self.journal = Journal()
        return AccorderDelai(depot, self.journal, lambda: AUJOURDHUI)

    def accorder(self, depot=None, **champs):
        depot = depot or en_retard()
        args = {"acteur": "adm@x.ci", "dossier": "D1", "jusqu_au": date(2026, 11, 5), "motif": "Salaire en retard"}
        self.cas(depot).executer(**(args | champs))
        return depot

    def test_delai_debloque_et_journalise_avant_apres(self):
        depot = self.accorder()
        self.assertEqual(depot.delais, [("D1", date(2026, 11, 5))])
        self.assertEqual(statut(depot.par_nom("D1").dossier, AUJOURDHUI), Statut.A_JOUR)
        d, acteur, action, avant, apres, motif = self.journal.appels[0]
        self.assertEqual((d, acteur, action, motif), ("D1", "adm@x.ci", "delai_accorde", "Salaire en retard"))
        self.assertEqual(avant, {"delai_jusqu_au": None, "statut": "en_retard"})
        self.assertEqual(apres, {"delai_jusqu_au": "2026-11-05", "statut": "a_jour"})

    def test_ancien_delai_conserve_dans_le_journal(self):
        depot = self.accorder()
        self.accorder(depot, jusqu_au=date(2026, 11, 20))
        self.assertEqual(self.journal.appels[0][3]["delai_jusqu_au"], "2026-11-05")

    def test_delai_non_futur_refuse(self):
        for jour in (AUJOURDHUI, date(2026, 10, 1), "2026-12-01", None, datetime(2026, 12, 1)):
            with self.subTest(jour=jour), self.assertRaisesRegex(OperationRefusee, "délai"):
                self.accorder(jusqu_au=jour)

    def test_motif_obligatoire(self):
        for motif in ("", "   ", None, "m" * 501):
            with self.subTest(motif=motif), self.assertRaisesRegex(OperationRefusee, "motif"):
                self.accorder(motif=motif)

    def test_dossier_inconnu_ou_dispense_refuse(self):
        with self.assertRaises(DossierAbsent):
            self.accorder(dossier="D9")
        depot = en_retard()
        depot.dossiers[("a@x.ci", "C")] = replace(depot.dossiers[("a@x.ci", "C")],
                                                  dossier=Dossier((), 0, dispense=True))
        with self.assertRaisesRegex(OperationRefusee, "dispensé"):
            self.accorder(depot)
        self.assertFalse(hasattr(depot, "delais"))
