"""Quand les inscriptions d'un parcours sont-elles ouvertes, et à quelle cohorte ?

La question que pose le site public, et la seule que le formulaire d'inscription a le droit de poser : le
visiteur choisit un parcours, jamais une cohorte. C'est le serveur qui désigne celle qui l'accueillera, et
qui refuse si aucune ne le peut — sans quoi un client bricolé s'inscrirait à une cohorte close, pleine, ou
appartenant à un autre parcours.

Rien ici ne touche la base : tout est décidé sur des valeurs.
"""
import datetime
import unittest

from openlab_academy.domain.echeancier import inscription_permise
from openlab_academy.domain.inscription_ouverte import (FERMEE_COMPLETE, FERMEE_PASSEE, FERMEE_RETIREE,
                                                        FERMEE_TARDIVE, OUVERTE, SUSPENDUE, Candidate,
                                                        Etat, cohorte_d_accueil, etat_de,
                                                        etat_du_parcours)

AUJOURD_HUI = datetime.date(2026, 11, 21)


def candidate(**remplacements) -> Candidate:
    valeurs = {
        "identifiant": "LOT-001",
        "titre": "Promo 1 — Fondamentaux",
        "debut": AUJOURD_HUI + datetime.timedelta(days=14),
        "fin": AUJOURD_HUI + datetime.timedelta(days=120),
        "places": 30,
        "inscrits": 4,
        "publiee": True,
        "libre": False,
    }
    valeurs.update(remplacements)
    return Candidate(**valeurs)


class TestLEtatDUneCohorte(unittest.TestCase):
    def test_une_cohorte_a_venir_avec_des_places_est_ouverte(self):
        self.assertEqual(etat_de(candidate(), AUJOURD_HUI), OUVERTE)

    def test_une_cohorte_non_publiee_n_existe_pas_pour_le_visiteur(self):
        """Non publiée = en préparation. La montrer reviendrait à annoncer une date qui peut encore
        changer."""
        self.assertEqual(etat_de(candidate(publiee=False), AUJOURD_HUI), FERMEE_RETIREE)

    def test_une_cohorte_pleine_est_fermee(self):
        self.assertEqual(etat_de(candidate(places=30, inscrits=30), AUJOURD_HUI), FERMEE_COMPLETE)

    def test_une_place_restante_suffit(self):
        self.assertEqual(etat_de(candidate(places=30, inscrits=29), AUJOURD_HUI), OUVERTE)

    def test_plus_d_inscrits_que_de_places_reste_ferme(self):
        """Un dépassement ne doit pas rouvrir les inscriptions par accident de comparaison."""
        self.assertEqual(etat_de(candidate(places=30, inscrits=31), AUJOURD_HUI), FERMEE_COMPLETE)

    def test_une_cohorte_commencee_reste_ouverte_le_temps_regle(self):
        """L'académie accepte le retardataire pendant deux mois — c'est `inscription_permise`, appliquée
        au moment où l'inscription est tentée. La page doit dire la même chose, sinon elle refuse une
        inscription que le serveur aurait acceptée."""
        commencee = candidate(debut=AUJOURD_HUI - datetime.timedelta(days=20))
        self.assertEqual(etat_de(commencee, AUJOURD_HUI), OUVERTE)

    def test_une_cohorte_commencee_depuis_trop_longtemps_est_close(self):
        vieille = candidate(debut=AUJOURD_HUI - datetime.timedelta(days=90))
        self.assertEqual(etat_de(vieille, AUJOURD_HUI), FERMEE_TARDIVE)

    def test_le_delai_de_retard_suit_les_reglages(self):
        """Porté à six mois, le même retardataire redevient recevable — et la page doit suivre."""
        commencee = candidate(debut=AUJOURD_HUI - datetime.timedelta(days=90))
        self.assertEqual(etat_de(commencee, AUJOURD_HUI, tardive_mois=6), OUVERTE)

    def test_la_page_ne_promet_jamais_ce_que_le_serveur_refusera(self):
        """L'invariant du module. Pour chaque jour d'une année autour du début d'une cohorte, ce que la
        page annonce ouvert, `inscription_permise` doit l'accepter — et réciproquement. Deux règles
        séparées auraient dérivé l'une de l'autre au premier changement de réglage."""
        debut = datetime.date(2026, 3, 15)
        for ecart in range(-120, 245):
            jour = debut + datetime.timedelta(days=ecart)
            cohorte = candidate(debut=debut, fin=debut + datetime.timedelta(days=400))
            with self.subTest(jour=jour.isoformat()):
                self.assertEqual(etat_de(cohorte, jour).ouverte,
                                 inscription_permise(debut, jour, 2))

    def test_une_cohorte_a_dates_fixes_est_ouverte_la_veille(self):
        demain = AUJOURD_HUI + datetime.timedelta(days=1)
        self.assertEqual(etat_de(candidate(debut=demain), AUJOURD_HUI), OUVERTE)

    def test_un_acces_libre_reste_ouvert_apres_son_debut(self):
        """Une fenêtre d'accès libre n'a pas de séance commune : on la rejoint quand on veut, tant
        qu'elle dure."""
        hier = AUJOURD_HUI - datetime.timedelta(days=30)
        self.assertEqual(etat_de(candidate(debut=hier, libre=True), AUJOURD_HUI), OUVERTE)

    def test_un_acces_libre_termine_est_ferme(self):
        termine = candidate(debut=AUJOURD_HUI - datetime.timedelta(days=60),
                            fin=AUJOURD_HUI - datetime.timedelta(days=1), libre=True)
        self.assertEqual(etat_de(termine, AUJOURD_HUI), FERMEE_PASSEE)

    def test_un_acces_libre_qui_finit_aujourd_hui_est_encore_ouvert(self):
        """Le dernier jour compte : la fenêtre se ferme à la fin de ce jour-là, pas à son début."""
        dernier = candidate(debut=AUJOURD_HUI - datetime.timedelta(days=60), fin=AUJOURD_HUI, libre=True)
        self.assertEqual(etat_de(dernier, AUJOURD_HUI), OUVERTE)

    def test_une_cohorte_a_dates_fixes_deja_terminee_est_passee_et_non_tardive(self):
        """L'ordre des refus compte : « terminée » se dit autrement que « close », et c'est ce que la
        page montre au visiteur."""
        passee = candidate(debut=AUJOURD_HUI - datetime.timedelta(days=200),
                           fin=AUJOURD_HUI - datetime.timedelta(days=10))
        self.assertEqual(etat_de(passee, AUJOURD_HUI), FERMEE_PASSEE)

    def test_le_retrait_prime_sur_tout_le_reste(self):
        """Une cohorte dépubliée ne doit laisser filtrer ni sa date ni son remplissage."""
        retiree = candidate(publiee=False, places=1, inscrits=99,
                            debut=AUJOURD_HUI - datetime.timedelta(days=1))
        self.assertEqual(etat_de(retiree, AUJOURD_HUI), FERMEE_RETIREE)


class TestLaCohorteQuiAccueille(unittest.TestCase):
    """Le visiteur choisit un parcours ; le serveur choisit la cohorte."""

    def test_sans_aucune_cohorte_personne_n_accueille(self):
        self.assertIsNone(cohorte_d_accueil((), AUJOURD_HUI))

    def test_la_seule_cohorte_ouverte_est_retenue(self):
        retenue = cohorte_d_accueil((candidate(identifiant="LOT-A"),), AUJOURD_HUI)
        self.assertEqual(retenue.identifiant, "LOT-A")

    def test_une_cohorte_fermee_n_accueille_pas(self):
        self.assertIsNone(cohorte_d_accueil((candidate(publiee=False),), AUJOURD_HUI))

    def test_entre_deux_ouvertes_la_plus_proche_accueille(self):
        """Celle qui commence le plus tôt : le visiteur veut commencer, pas attendre le trimestre
        suivant."""
        tot = candidate(identifiant="TOT", debut=AUJOURD_HUI + datetime.timedelta(days=7))
        tard = candidate(identifiant="TARD", debut=AUJOURD_HUI + datetime.timedelta(days=90))
        self.assertEqual(cohorte_d_accueil((tard, tot), AUJOURD_HUI).identifiant, "TOT")

    def test_une_fermee_ne_passe_jamais_devant_une_ouverte(self):
        pleine_et_proche = candidate(identifiant="PLEINE", places=5, inscrits=5,
                                     debut=AUJOURD_HUI + datetime.timedelta(days=2))
        ouverte_et_lointaine = candidate(identifiant="OUVERTE",
                                         debut=AUJOURD_HUI + datetime.timedelta(days=60))
        retenue = cohorte_d_accueil((pleine_et_proche, ouverte_et_lointaine), AUJOURD_HUI)
        self.assertEqual(retenue.identifiant, "OUVERTE")

    def test_a_dates_egales_le_choix_ne_depend_pas_de_l_ordre_recu(self):
        """Sans quoi deux visiteurs de la même page pourraient se voir proposer deux cohortes
        différentes, selon l'humeur de la base."""
        meme_date = AUJOURD_HUI + datetime.timedelta(days=30)
        a = candidate(identifiant="LOT-A", debut=meme_date)
        b = candidate(identifiant="LOT-B", debut=meme_date)
        self.assertEqual(cohorte_d_accueil((a, b), AUJOURD_HUI).identifiant,
                         cohorte_d_accueil((b, a), AUJOURD_HUI).identifiant)


class TestCeQuOnDitAuVisiteur(unittest.TestCase):
    """Un refus muet envoie le visiteur ailleurs. Chaque état porte donc sa phrase."""

    def test_chaque_etat_a_sa_phrase(self):
        for etat in Etat:
            with self.subTest(etat.name):
                self.assertTrue(etat.message.strip(), f"{etat.name} n'a rien à dire")

    def test_la_phrase_de_l_ouverture_invite_a_s_inscrire(self):
        self.assertIn("inscri", OUVERTE.message.lower())

    def test_une_cohorte_complete_ne_renvoie_pas_le_visiteur_les_mains_vides(self):
        """« Complet » sans suite fait fermer l'onglet. On annonce la suite."""
        self.assertIn("prochaine", FERMEE_COMPLETE.message.lower())

    def test_la_suspension_n_est_pas_une_ouverture_et_annonce_une_suite(self):
        self.assertFalse(SUSPENDUE.ouverte)
        self.assertIn("bientôt", SUSPENDUE.message.lower())


class TestLaSuspensionNEstPasUnEtatDeCohorte(unittest.TestCase):
    """La suspension est une décision de l'académie, pas l'état d'une cohorte.

    Si elle se glissait dans `etat_de`, elle dépendrait des dates et du remplissage — alors qu'elle
    doit valoir pour tous les parcours à la fois, y compris les gratuits, qui n'ont pas de cohorte.
    """

    def setUp(self):
        self.cohortes = [candidate(), candidate(publiee=False), candidate(places=5, inscrits=5),
                         candidate(fin=AUJOURD_HUI - datetime.timedelta(1)),
                         candidate(libre=True, debut=AUJOURD_HUI - datetime.timedelta(60))]

    def test_aucune_cohorte_ne_rend_jamais_l_etat_suspendu(self):
        for cohorte in self.cohortes:
            with self.subTest(cohorte.identifiant):
                self.assertIsNot(etat_de(cohorte, AUJOURD_HUI), SUSPENDUE)

    def test_l_annonce_d_un_parcours_ne_rend_jamais_l_etat_suspendu(self):
        self.assertIsNot(etat_du_parcours(self.cohortes, AUJOURD_HUI), SUSPENDUE)
        self.assertIsNot(etat_du_parcours((), AUJOURD_HUI), SUSPENDUE)


class TestCeQuAnnonceLaPageDuParcours(unittest.TestCase):
    """Quand aucune cohorte n'accueille, la page doit quand même dire quelque chose de juste."""

    def test_une_seule_ouverte_suffit_a_ouvrir_le_parcours(self):
        self.assertEqual(etat_du_parcours((candidate(publiee=False), candidate()), AUJOURD_HUI), OUVERTE)

    def test_sans_aucune_cohorte_les_inscriptions_ne_sont_pas_encore_ouvertes(self):
        self.assertEqual(etat_du_parcours((), AUJOURD_HUI), FERMEE_RETIREE)

    def test_complet_est_prefere_a_termine(self):
        """« Complet » dit qu'il y a eu de la demande et qu'il y aura une suite ; « terminé » ferme la
        porte. Entre les deux, on montre le premier."""
        pleine = candidate(identifiant="PLEINE", places=5, inscrits=5)
        passee = candidate(identifiant="PASSEE", debut=AUJOURD_HUI - datetime.timedelta(days=300),
                           fin=AUJOURD_HUI - datetime.timedelta(days=10))
        self.assertEqual(etat_du_parcours((passee, pleine), AUJOURD_HUI), FERMEE_COMPLETE)

    def test_l_ordre_recu_ne_change_pas_l_annonce(self):
        pleine = candidate(identifiant="PLEINE", places=5, inscrits=5)
        tardive = candidate(identifiant="TARDIVE", debut=AUJOURD_HUI - datetime.timedelta(days=90))
        self.assertEqual(etat_du_parcours((pleine, tardive), AUJOURD_HUI),
                         etat_du_parcours((tardive, pleine), AUJOURD_HUI))
