"""Cas d'usage du paiement : ouverture du dossier à l'inscription, choix et changement de mode (faux ports)."""
import unittest
from dataclasses import replace
from datetime import date, datetime

from openlab_academy.application.paiements import (
    ChoisirMode, ConfirmerPaiement, DossierAbsent, InitierPaiement, InscriptionTardive, OuvrirDossier,
    PaiementIndisponible, RienADu, TarifAbsent, TelephoneInvalide, valider_telephone)
from openlab_academy.application.ports_paiement import (
    Client, DossierEnregistre, PaiementEnregistre, ReglagesPaiement, Verification)
from openlab_academy.domain.dossier_paiement import Dossier, Statut, statut
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

    def marquer_echoue(self, moyen, reference):
        p = self.paiements[(moyen, reference)]
        if p.statut == "en_attente":
            self.paiements[(moyen, reference)] = replace(p, statut="echoue")

    def fixer_delai(self, nom, d):
        pass


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


class TestChoisirMode(unittest.TestCase):
    def cas(self, depot, jour=10):
        self.journal = Journal()
        return ChoisirMode(depot, self.journal, lambda: date(2026, 11, 20), jour)

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
        self.assertEqual(echeances[0], Echeance(date(2026, 11, 20), 10000, "Déjà versé"))
        self.assertEqual(echeances[1].date_limite, date(2026, 12, 10))
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
