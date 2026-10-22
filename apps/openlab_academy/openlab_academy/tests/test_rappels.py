"""Cas d'usage des rappels J-7, J-3, J-1 (faux ports) : un envoi par dossier, échéance, délai et canal ; un canal en
erreur n'arrête ni les autres canaux ni les autres apprenants ; relance des échecs ; revérification des paiements."""
import unittest
from datetime import date, datetime, timedelta

from openlab_academy.application.paiements import PaiementIndisponible, ReverifierPaiements
from openlab_academy.application.rappels import (
    DestinataireInjoignable, Destinataire, DossierARappeler, EnvoiImpossible, EnvoyerRappels, message_rappel, quand)
from openlab_academy.domain.dossier_paiement import Dossier
from openlab_academy.domain.echeancier import Echeance

J0 = date(2026, 11, 3)
LIMITE = date(2026, 11, 10)
AYA = Destinataire("aya@x.ci", "+2250700000000", "Aya Kouassi")


def dossier_a_rappeler(nom="D1", paye=0, dispense=False, delai=None, echeances=None, destinataire=AYA):
    echeances = echeances or (Echeance(date(2026, 10, 22), 10000, "Frais d'inscription"),
                              Echeance(LIMITE, 50000, "Mensualité 1"), Echeance(date(2026, 12, 10), 50000, "Mensualité 2"))
    return DossierARappeler(nom, "parcours-ia", "Parcours IA", destinataire,
                            Dossier(echeances, paye, delai, dispense, frais_inscription=10000),
                            "https://academy.ci/espace/paiement/parcours-ia")


class Depot:
    def __init__(self, *dossiers):
        self.dossiers = {d.nom: d for d in dossiers}

    def noms(self):
        return tuple(self.dossiers)

    def charger(self, nom):
        d = self.dossiers.get(nom)
        if isinstance(d, Exception):
            raise d
        return d


class Registre:
    def __init__(self):
        self.lignes = {}
        self.reservations = []

    def etats(self, dossier):
        return {(dl, j, c): s for (d, dl, j, c), s in self.lignes.items() if d == dossier}

    def reserver(self, dossier, date_limite, jours, canal):
        cle = (dossier, date_limite, jours, canal)
        self.reservations.append(cle)
        if self.lignes.get(cle) == "envoye":
            return False
        self.lignes.setdefault(cle, "echec")
        return True

    def consigner(self, dossier, date_limite, jours, canal, statut):
        self.lignes[(dossier, date_limite, jours, canal)] = statut


class Canal:
    def __init__(self, nom, disponible=True, erreur=None):
        self.nom, self._disponible, self.erreur = nom, disponible, erreur
        self.envois = []

    def disponible(self):
        return self._disponible

    def envoyer(self, destinataire, message):
        if self.erreur:
            raise self.erreur
        self.envois.append((destinataire, message))


def canaux(**autres):
    return [autres.get("email", Canal("email")), autres.get("sms", Canal("sms")),
            autres.get("whatsapp", Canal("whatsapp"))]


class Alertes(list):
    def __call__(self, titre, detail):
        self.append((titre, detail))


def cas(depot, chaines, registre, jour, **options):
    alertes = options.pop("alerte", Alertes())
    return EnvoyerRappels(depot, chaines, registre, lambda: jour, alerte=alertes, **options), alertes


class TestMessage(unittest.TestCase):
    def test_texte_exact(self):
        m = message_rappel("Parcours IA", 52500, LIMITE, "https://academy.ci/espace/paiement/parcours-ia", "Aya")
        self.assertEqual(m.texte, "Rappel OpenLab Academy : 52 500 FCFA à régler au plus tard le 10/11/2026 pour le "
                                  "parcours Parcours IA. Payer : https://academy.ci/espace/paiement/parcours-ia")
        self.assertEqual(m.sujet, "Rappel de paiement : Parcours IA")
        self.assertEqual(m.parametres, ("Aya", "52 500", "10/11/2026"))
        self.assertEqual((m.titre, m.lien, m.quand), ("Parcours IA", "https://academy.ci/espace/paiement/parcours-ia", ""))
        self.assertEqual(message_rappel("P", 5, LIMITE, "u", "", jours=3).quand, "J-3")

    def test_quand(self):
        self.assertEqual([quand(j) for j in (7, 3, 1, 0)], ["J-7", "J-3", "J-1", "jour J"])

    def test_nom_absent_remplace(self):
        self.assertEqual(message_rappel("P", 5, LIMITE, "u", "").parametres[0], "apprenant")


class TestEnvoyerRappels(unittest.TestCase):
    def test_j7_j3_j1_une_fois_chacun_meme_si_la_tache_tourne_deux_fois(self):
        depot, registre, chaines = Depot(dossier_a_rappeler(paye=10000)), Registre(), canaux()
        for jour in (J0, J0, date(2026, 11, 7), date(2026, 11, 7), date(2026, 11, 9), date(2026, 11, 9)):
            cas(depot, chaines, registre, jour)[0].executer()
        for c in chaines:
            self.assertEqual(len(c.envois), 3, c.nom)
        self.assertEqual(sorted(j for (_, _, j, _), s in registre.lignes.items() if s == "envoye"),
                         [1, 1, 1, 3, 3, 3, 7, 7, 7])
        dest, message = chaines[0].envois[0]
        self.assertEqual(dest, AYA)
        self.assertIn("50 000 FCFA à régler au plus tard le 10/11/2026 pour le parcours Parcours IA", message.texte)
        self.assertEqual((message.titre, message.lien, message.quand),
                         ("Parcours IA", "https://academy.ci/espace/paiement/parcours-ia", "J-7"))
        self.assertEqual([m.quand for _, m in chaines[0].envois], ["J-7", "J-3", "J-1"])

    def test_nombre_envoye_et_jours_sans_rappel(self):
        depot = Depot(dossier_a_rappeler(paye=10000))
        self.assertEqual(cas(depot, canaux(), Registre(), J0)[0].executer(), 3)
        self.assertEqual(cas(depot, canaux(), Registre(), date(2026, 11, 4))[0].executer(), 0)

    def test_sms_en_erreur_email_et_whatsapp_partent(self):
        sms = Canal("sms", erreur=EnvoiImpossible("SMS : réponse HTTP 500"))
        chaines, registre = canaux(sms=sms), Registre()
        envoye, alertes = cas(Depot(dossier_a_rappeler(paye=10000)), chaines, registre, J0)
        self.assertEqual(envoye.executer(), 2)
        self.assertEqual(len(chaines[0].envois) + len(chaines[2].envois), 2)
        self.assertEqual(registre.lignes[("D1", LIMITE, 7, "sms")], "echec")
        self.assertEqual(registre.lignes[("D1", LIMITE, 7, "email")], "envoye")
        self.assertEqual(alertes, [("Rappel de paiement non envoyé", "sms, dossier D1 : SMS : réponse HTTP 500")])

    def test_erreur_inattendue_consignee_par_son_type_seulement(self):
        whatsapp = Canal("whatsapp", erreur=RuntimeError("jeton=EAAG-secret +2250700000000"))
        envoye, alertes = cas(Depot(dossier_a_rappeler(paye=10000)), canaux(whatsapp=whatsapp), Registre(), J0)
        envoye.executer()
        self.assertEqual(alertes, [("Rappel de paiement non envoyé", "whatsapp, dossier D1 : RuntimeError")])

    def test_canal_non_configure_ignore_puis_envoye_s_il_est_configure_le_jour_meme(self):
        sms, registre = Canal("sms", disponible=False), Registre()
        depot = Depot(dossier_a_rappeler(paye=10000))
        envoye, alertes = cas(depot, canaux(sms=sms), registre, J0)
        self.assertEqual(envoye.executer(), 2)
        self.assertEqual(registre.lignes[("D1", LIMITE, 7, "sms")], "ignore")
        self.assertNotIn(("D1", LIMITE, 7, "sms"), registre.reservations)
        self.assertEqual(alertes, [])
        ecrits = []
        registre.consigner = lambda *a: ecrits.append(a)
        self.assertEqual(cas(depot, canaux(sms=sms), registre, J0)[0].executer(), 0)  # second passage du jour
        self.assertEqual(ecrits, [])
        del registre.consigner
        sms._disponible = True
        self.assertEqual(cas(depot, canaux(sms=sms), registre, J0)[0].executer(), 1)
        self.assertEqual(registre.lignes[("D1", LIMITE, 7, "sms")], "envoye")
        self.assertEqual(cas(depot, canaux(sms=sms), registre, date(2026, 11, 4))[0].executer(), 0)

    def test_destinataire_sans_numero_ignore(self):
        sms = Canal("sms", erreur=DestinataireInjoignable("pas de numéro"))
        registre = Registre()
        envoye, alertes = cas(Depot(dossier_a_rappeler(paye=10000)), canaux(sms=sms), registre, J0)
        self.assertEqual(envoye.executer(), 2)
        self.assertEqual(registre.lignes[("D1", LIMITE, 7, "sms")], "ignore")
        self.assertEqual(alertes, [])

    def test_reservation_refusee_rien_n_est_envoye(self):
        class Occupe(Registre):
            def reserver(self, *cle):
                return False
        chaines = canaux()
        self.assertEqual(cas(Depot(dossier_a_rappeler(paye=10000)), chaines, Occupe(), J0)[0].executer(), 0)
        self.assertEqual([c.envois for c in chaines], [[], [], []])

    def test_echec_relance_le_lendemain_tant_que_l_echeance_reste_due(self):
        sms, registre = Canal("sms", erreur=EnvoiImpossible("SMS injoignable")), Registre()
        depot = Depot(dossier_a_rappeler(paye=10000))
        cas(depot, canaux(sms=sms), registre, J0)[0].executer()
        sms.erreur = None
        self.assertEqual(cas(depot, canaux(sms=sms), registre, date(2026, 11, 4))[0].executer(), 1)
        self.assertEqual(registre.lignes[("D1", LIMITE, 7, "sms")], "envoye")
        self.assertIn("50 000 FCFA", sms.envois[0][1].texte)
        self.assertEqual(sms.envois[0][1].quand, "J-6")  # relancé : jours réellement restants
        self.assertEqual(cas(depot, canaux(sms=sms), registre, date(2026, 11, 5))[0].executer(), 0)

    def test_echec_non_relance_si_paye_echu_ou_remplace(self):
        sms, registre = Canal("sms", erreur=EnvoiImpossible("SMS injoignable")), Registre()
        cas(Depot(dossier_a_rappeler(paye=10000)), canaux(sms=sms), registre, J0)[0].executer()
        sms.erreur = None
        # payé entre-temps : plus rien à rappeler
        self.assertEqual(cas(Depot(dossier_a_rappeler(paye=60000)), canaux(sms=sms), registre,
                             date(2026, 11, 4))[0].executer(), 0)
        # échéance passée
        self.assertEqual(cas(Depot(dossier_a_rappeler(paye=10000)), canaux(sms=sms), registre,
                             date(2026, 11, 11))[0].executer(), 0)
        # le rappel J-3 du jour remplace la relance du J-7 (un seul SMS ce jour-là)
        self.assertEqual(cas(Depot(dossier_a_rappeler(paye=10000)), canaux(sms=sms), registre,
                             date(2026, 11, 7))[0].executer(), 3)
        self.assertEqual(len(sms.envois), 1)
        self.assertEqual(registre.lignes[("D1", LIMITE, 7, "sms")], "echec")
        # un rappel plus récent existe déjà : le J-7 en échec n'est plus relancé
        self.assertEqual(cas(Depot(dossier_a_rappeler(paye=10000)), canaux(sms=sms), registre,
                             date(2026, 11, 8))[0].executer(), 0)

    def test_echec_d_un_canal_retire_non_relance(self):
        registre = Registre()
        registre.consigner("D1", LIMITE, 7, "fax", "echec")
        self.assertEqual(cas(Depot(dossier_a_rappeler(paye=10000)), canaux(), registre,
                             date(2026, 11, 4))[0].executer(), 0)

    def test_echeances_du_meme_jour_cumulees(self):
        echeances = (Echeance(LIMITE, 10000, "Frais d'inscription"), Echeance(LIMITE, 50000, "Mensualité 1"))
        chaines = canaux()
        cas(Depot(dossier_a_rappeler(echeances=echeances)), chaines, Registre(), J0)[0].executer()
        self.assertEqual(len(chaines[0].envois), 1)
        self.assertIn("60 000 FCFA", chaines[0].envois[0][1].texte)

    def test_dispense_et_solde_sans_rappel_delai_selon_le_domaine(self):
        chaines = canaux()
        depot = Depot(dossier_a_rappeler("D1", dispense=True), dossier_a_rappeler("D2", paye=110000),
                      dossier_a_rappeler("D3", paye=10000, delai=date(2026, 12, 31)))
        self.assertEqual(cas(depot, chaines, Registre(), J0)[0].executer(), 3)  # rappels_dus ignore le délai
        self.assertEqual(len(chaines[0].envois), 1)

    def test_montant_restant_de_l_echeance(self):
        chaines = canaux()
        cas(Depot(dossier_a_rappeler(paye=30000)), chaines, Registre(), J0)[0].executer()
        self.assertIn("30 000 FCFA", chaines[0].envois[0][1].texte)

    def test_delais_regles(self):
        chaines = canaux()
        envoye = cas(Depot(dossier_a_rappeler(paye=10000)), chaines, Registre(), date(2026, 11, 5), delais=(5,))[0]
        self.assertEqual(envoye.executer(), 3)

    def test_un_dossier_en_erreur_n_arrete_pas_les_autres(self):
        depot = Depot(dossier_a_rappeler("D1", paye=10000), dossier_a_rappeler("D3", paye=10000))
        depot.dossiers["D2"] = KeyError("panne")
        depot.dossiers = {k: depot.dossiers[k] for k in ("D1", "D2", "D3")}
        envoye, alertes = cas(depot, canaux(), Registre(), J0)
        self.assertEqual(envoye.executer(), 6)
        self.assertEqual(alertes, [("Rappels de paiement : dossier non traité", "dossier D2 : KeyError")])

    def test_dossier_disparu_ignore(self):
        depot = Depot(dossier_a_rappeler(paye=10000))
        depot.dossiers["D0"] = None
        self.assertEqual(cas(depot, canaux(), Registre(), J0)[0].executer(), 3)

    def test_reservation_validee_avant_l_envoi_statut_valide_apres(self):
        journal = []

        class RegistreTrace(Registre):
            def reserver(self, *cle):
                journal.append(("reserver", cle[3]))
                return super().reserver(*cle)

            def consigner(self, *cle):
                journal.append(("consigner", cle[3], cle[4]))
                super().consigner(*cle)

        class CanalTrace(Canal):
            def envoyer(self, destinataire, message):
                journal.append(("envoi", self.nom))
                super().envoyer(destinataire, message)

        def unite(action):
            journal.append("debut")
            resultat = action()
            journal.append("valide")
            return resultat
        chaines = [CanalTrace("email"), CanalTrace("sms", erreur=EnvoiImpossible("x"))]
        cas(Depot(dossier_a_rappeler("D1", paye=10000)), chaines, RegistreTrace(), J0, unite=unite)[0].executer()
        self.assertEqual(journal, [
            "debut", "valide",  # planification du dossier
            "debut", ("reserver", "email"), "valide", "debut", ("envoi", "email"), ("consigner", "email", "envoye"),
            "valide",
            "debut", ("reserver", "sms"), "valide", "debut", ("envoi", "sms"),  # échec : la réservation reste `echec`
        ])

    def test_echec_de_l_unite_d_envoi_annule_et_reste_en_echec(self):
        def unite(action):
            return action()
        registre = Registre()
        registre_consigner = registre.consigner

        def consigner(*cle):
            if cle[4] == "envoye":
                raise RuntimeError("base indisponible")
            registre_consigner(*cle)
        registre.consigner = consigner
        envoye, alertes = cas(Depot(dossier_a_rappeler(paye=10000)), canaux(), registre, J0, unite=unite)
        self.assertEqual(envoye.executer(), 0)
        self.assertEqual(set(registre.lignes.values()), {"echec"})
        self.assertEqual(alertes[0], ("Rappel de paiement non envoyé", "email, dossier D1 : RuntimeError"))

    def test_erreur_fatale_jamais_avalee(self):
        class Fatale(Exception):
            pass
        en_panne = Depot()
        en_panne.dossiers["D1"] = Fatale()
        for depot, chaines in ((Depot(dossier_a_rappeler(paye=10000)), canaux(sms=Canal("sms", erreur=Fatale()))),
                               (en_panne, canaux())):
            with self.subTest(), self.assertRaises(Fatale):
                cas(depot, chaines, Registre(), J0, fatales=(Fatale,))[0].executer()

    def test_alerte_par_defaut_silencieuse(self):
        sms = Canal("sms", erreur=EnvoiImpossible("x"))
        envoye = EnvoyerRappels(Depot(dossier_a_rappeler(paye=10000)), canaux(sms=sms), Registre(), lambda: J0)
        self.assertEqual(envoye.executer(), 2)


class Confirmer:
    def __init__(self, erreurs=None):
        self.erreurs = erreurs or {}
        self.vus = []

    def executer(self, reference):
        self.vus.append(reference)
        if reference in self.erreurs:
            raise self.erreurs[reference]


class DepotAttente:
    def __init__(self, references):
        self.references = references
        self.demandes = []

    def paiements_en_attente_depuis(self, moyen, depuis):
        self.demandes.append((moyen, depuis))
        return self.references


class TestReverifierPaiements(unittest.TestCase):
    MAINTENANT = datetime(2026, 11, 3, 8, 0)

    def test_paiements_recents_revérifies_chacun_independamment(self):
        depot = DepotAttente(("R1", "R2", "R3"))
        confirmer = Confirmer({"R2": RuntimeError("apikey=secret")})
        alertes = Alertes()
        n = ReverifierPaiements(depot, confirmer, lambda: self.MAINTENANT, alerte=alertes).executer()
        self.assertEqual(n, 3)
        self.assertEqual(confirmer.vus, ["R1", "R2", "R3"])
        self.assertEqual(depot.demandes, [("cinetpay", self.MAINTENANT - timedelta(days=7))])
        self.assertEqual(alertes, [("Paiement en ligne non revérifié", "transaction 'R2' : RuntimeError")])

    def test_passerelle_injoignable_arrete_le_passage(self):
        confirmer = Confirmer({"R2": PaiementIndisponible("CinetPay injoignable (Timeout)")})
        alertes = Alertes()
        n = ReverifierPaiements(DepotAttente(("R1", "R2", "R3", "R4")), confirmer, lambda: self.MAINTENANT,
                                alerte=alertes).executer()
        self.assertEqual((n, confirmer.vus), (2, ["R1", "R2"]))
        self.assertEqual(alertes, [("Paiement en ligne non revérifié",
                                    "transaction 'R2' : CinetPay injoignable (Timeout) ; passage interrompu")])

    def test_erreur_fatale_jamais_avalee(self):
        class Fatale(Exception):
            pass
        with self.assertRaises(Fatale):
            ReverifierPaiements(DepotAttente(("R1",)), Confirmer({"R1": Fatale()}), lambda: self.MAINTENANT,
                                fatales=(Fatale,)).executer()

    def test_unite_et_alerte_par_defaut(self):
        unites = []

        def unite(action):
            unites.append(action)
            return action()
        confirmer = Confirmer({"R1": RuntimeError()})
        ReverifierPaiements(DepotAttente(("R1",)), confirmer, lambda: self.MAINTENANT, unite=unite).executer()
        ReverifierPaiements(DepotAttente(("R1",)), confirmer, lambda: self.MAINTENANT).executer()
        self.assertEqual((len(unites), confirmer.vus), (1, ["R1", "R1"]))


if __name__ == "__main__":
    unittest.main()
