"""Le cas d'usage de l'inscription depuis le site public : ce que la page montre, et ce qu'elle fait.

Deux exigences gouvernent tout ce fichier.

La première : **le visiteur n'envoie qu'un nom de parcours**. Il ne choisit pas sa cohorte, ne dit pas si
le parcours est gratuit, ne fournit pas de tarif. Tout cela est relu côté serveur. Un formulaire bricolé
ne doit pouvoir rien obtenir de plus qu'un formulaire honnête.

La seconde : **l'offre montrée et l'inscription faite reposent sur le même calcul**. Une page qui annonce
« ouvert » et une inscription qui refuse, c'est un visiteur perdu ; l'inverse, c'est une place vendue deux
fois.
"""
import datetime
import unittest

from openlab_academy.application.inscrire_au_parcours import (InscriptionImpossible, InscrireAuParcours,
                                                              Offre)
from openlab_academy.domain.inscription_ouverte import (FERMEE_COMPLETE, FERMEE_RETIREE, OUVERTE,
                                                        Candidate)

AUJOURD_HUI = datetime.date(2026, 11, 21)
COURS = "fondamentaux-de-la-data-science"
APPRENANT = "awa.kone@exemple.ci"


def candidate(**remplacements) -> Candidate:
    valeurs = {"identifiant": "LOT-001", "titre": "Promo 1", "debut": AUJOURD_HUI + datetime.timedelta(14),
               "fin": AUJOURD_HUI + datetime.timedelta(120), "places": 30, "inscrits": 4,
               "publiee": True, "libre": False}
    valeurs.update(remplacements)
    return Candidate(**valeurs)


class CohortesFeintes:
    def __init__(self, par_cours=None):
        self._par_cours = par_cours or {}

    def candidates(self, cours):
        return tuple(self._par_cours.get(cours, ()))


class InscripteurFeint:
    def __init__(self, deja=()):
        self.cohortes_faites = []
        self.parcours_faits = []
        self._deja = set(deja)

    def deja_inscrit(self, apprenant, cours):
        return (apprenant, cours) in self._deja

    def a_la_cohorte(self, apprenant, cohorte, cours):
        self.cohortes_faites.append((apprenant, cohorte, cours))

    def au_parcours(self, apprenant, cours):
        self.parcours_faits.append((apprenant, cours))


class GratuitsFeints:
    def __init__(self, gratuits=()):
        self._gratuits = set(gratuits)

    def gratuit(self, cours):
        return cours in self._gratuits


class TarifsFeints:
    def __init__(self, par_cours=None):
        self._par_cours = par_cours or {}

    def montant(self, cours):
        return self._par_cours.get(cours)


class ReglagesFeints:
    def __init__(self, mois=2):
        self.mois = mois

    def inscription_tardive_mois(self):
        return self.mois


def cas(cohortes=None, gratuits=(), tarifs=None, deja=(), mois=2):
    inscripteur = InscripteurFeint(deja)
    usage = InscrireAuParcours(
        cohortes=CohortesFeintes({COURS: [candidate()]} if cohortes is None else cohortes),
        inscripteur=inscripteur,
        gratuits=GratuitsFeints(gratuits),
        tarifs=TarifsFeints({COURS: 250000} if tarifs is None else tarifs),
        reglages=ReglagesFeints(mois),
        aujourd_hui=lambda: AUJOURD_HUI)
    return usage, inscripteur


class TestCeQueLaPageMontre(unittest.TestCase):
    def test_un_parcours_payant_a_cohorte_ouverte_se_presente_avec_sa_session_et_son_prix(self):
        usage, _ = cas()
        offre = usage.offre(COURS, APPRENANT)
        self.assertEqual(offre.etat, OUVERTE)
        self.assertEqual(offre.session, "Promo 1")
        self.assertEqual(offre.places_restantes, 26)
        self.assertEqual(offre.montant, 250000)
        self.assertFalse(offre.gratuit)

    def test_un_parcours_gratuit_s_ouvre_sans_cohorte_ni_prix(self):
        """Un MOOC n'a pas de promotion : on s'y inscrit seul, et tout de suite."""
        usage, _ = cas(cohortes={COURS: []}, gratuits=(COURS,))
        offre = usage.offre(COURS, APPRENANT)
        self.assertEqual(offre.etat, OUVERTE)
        self.assertTrue(offre.gratuit)
        self.assertIsNone(offre.montant)
        self.assertEqual(offre.session, "")

    def test_sans_cohorte_ouverte_un_parcours_payant_est_ferme(self):
        usage, _ = cas(cohortes={COURS: [candidate(places=5, inscrits=5)]})
        self.assertEqual(usage.offre(COURS, APPRENANT).etat, FERMEE_COMPLETE)

    def test_un_parcours_sans_aucune_cohorte_n_est_pas_encore_ouvert(self):
        usage, _ = cas(cohortes={COURS: []})
        self.assertEqual(usage.offre(COURS, APPRENANT).etat, FERMEE_RETIREE)

    def test_un_parcours_payant_sans_tarif_n_est_pas_propose(self):
        """Garde-fou contre l'oubli du prix : le serveur refuserait l'inscription plus loin
        (`TarifAbsent`). Autant ne pas l'annoncer ouverte."""
        usage, _ = cas(tarifs={})
        offre = usage.offre(COURS, APPRENANT)
        self.assertFalse(offre.etat.ouverte)

    def test_un_apprenant_deja_inscrit_le_voit_dire(self):
        usage, _ = cas(deja=[(APPRENANT, COURS)])
        offre = usage.offre(COURS, APPRENANT)
        self.assertTrue(offre.deja_inscrit)

    def test_un_visiteur_sans_compte_voit_l_offre_sans_etre_dit_inscrit(self):
        """La page est publique : elle doit montrer prix et dates à qui n'a pas de compte, c'est tout
        l'intérêt d'une façade."""
        usage, _ = cas()
        offre = usage.offre(COURS, apprenant="")
        self.assertEqual(offre.etat, OUVERTE)
        self.assertEqual(offre.montant, 250000)
        self.assertFalse(offre.deja_inscrit)

    def test_l_offre_ne_nomme_jamais_la_cohorte_au_client(self):
        """Le titre de la session s'affiche ; son identifiant, non. Ce que le client ne connaît pas, il
        ne peut pas le falsifier."""
        usage, _ = cas()
        offre = usage.offre(COURS, APPRENANT)
        self.assertNotIn("LOT-001", str(offre.__dict__.values()))


class TestCeQueLInscriptionFait(unittest.TestCase):
    def test_un_parcours_payant_inscrit_a_la_cohorte_et_renvoie_au_paiement(self):
        """L'inscription à la cohorte suffit : le dossier de paiement naît d'elle, par les hooks."""
        usage, inscripteur = cas()
        destination = usage.executer(COURS, APPRENANT)
        self.assertEqual(inscripteur.cohortes_faites, [(APPRENANT, "LOT-001", COURS)])
        self.assertEqual(inscripteur.parcours_faits, [])
        self.assertEqual(destination, "/espace/paiement/fondamentaux-de-la-data-science")

    def test_un_parcours_gratuit_inscrit_directement_et_renvoie_au_cours(self):
        usage, inscripteur = cas(cohortes={COURS: []}, gratuits=(COURS,))
        destination = usage.executer(COURS, APPRENANT)
        self.assertEqual(inscripteur.parcours_faits, [(APPRENANT, COURS)])
        self.assertEqual(inscripteur.cohortes_faites, [])
        self.assertIn(COURS, destination)

    def test_la_cohorte_est_choisie_par_le_serveur_et_non_recue(self):
        """La signature elle-même l'interdit : `executer` ne prend pas de cohorte. C'est la barrière la
        plus solide — on ne peut pas falsifier un paramètre qui n'existe pas."""
        import inspect
        parametres = set(inspect.signature(InscrireAuParcours.executer).parameters)
        self.assertEqual(parametres, {"self", "cours", "apprenant"})

    def test_une_inscription_sur_un_parcours_ferme_est_refusee(self):
        usage, inscripteur = cas(cohortes={COURS: [candidate(places=5, inscrits=5)]})
        with self.assertRaises(InscriptionImpossible):
            usage.executer(COURS, APPRENANT)
        self.assertEqual(inscripteur.cohortes_faites, [])

    def test_une_inscription_sans_cohorte_est_refusee(self):
        usage, _ = cas(cohortes={COURS: []})
        with self.assertRaises(InscriptionImpossible):
            usage.executer(COURS, APPRENANT)

    def test_une_inscription_sans_compte_est_refusee(self):
        """Le garde-fou de dernier recours : la page n'offre le bouton qu'aux connectés, mais l'API ne
        s'y fie pas."""
        usage, inscripteur = cas()
        with self.assertRaises(InscriptionImpossible):
            usage.executer(COURS, apprenant="")
        self.assertEqual(inscripteur.cohortes_faites, [])

    def test_une_seconde_inscription_ne_cree_rien_et_mene_au_meme_endroit(self):
        """Un double clic, un retour arrière, un onglet rouvert : rien de tout cela ne doit créer une
        deuxième inscription."""
        usage, inscripteur = cas(deja=[(APPRENANT, COURS)])
        destination = usage.executer(COURS, APPRENANT)
        self.assertEqual(inscripteur.cohortes_faites, [])
        self.assertEqual(inscripteur.parcours_faits, [])
        self.assertTrue(destination)

    def test_un_parcours_payant_sans_tarif_refuse_l_inscription(self):
        usage, inscripteur = cas(tarifs={})
        with self.assertRaises(InscriptionImpossible):
            usage.executer(COURS, APPRENANT)
        self.assertEqual(inscripteur.cohortes_faites, [])

    def test_le_refus_dit_pourquoi(self):
        """Un message vide renvoie le visiteur sans rien lui apprendre."""
        usage, _ = cas(cohortes={COURS: [candidate(places=5, inscrits=5)]})
        with self.assertRaises(InscriptionImpossible) as refus:
            usage.executer(COURS, APPRENANT)
        self.assertIn("complète", str(refus.exception).lower())


class TestLesDeuxCheminsSAccordent(unittest.TestCase):
    """Ce que la page annonce et ce que l'inscription fait reposent sur le même calcul."""

    def test_ce_qui_est_annonce_ouvert_s_inscrit(self):
        for description, cohortes, gratuits, tarifs in (
                ("payant ouvert", {COURS: [candidate()]}, (), {COURS: 250000}),
                ("gratuit", {COURS: []}, (COURS,), {}),
                ("commencé depuis peu", {COURS: [candidate(debut=AUJOURD_HUI - datetime.timedelta(20))]},
                 (), {COURS: 250000}),
                ("une place restante", {COURS: [candidate(places=30, inscrits=29)]}, (), {COURS: 250000})):
            with self.subTest(description):
                usage, _ = cas(cohortes=cohortes, gratuits=gratuits, tarifs=tarifs)
                if usage.offre(COURS, APPRENANT).etat.ouverte:
                    usage.executer(COURS, APPRENANT)  # ne doit pas lever

    def test_ce_qui_est_annonce_ferme_ne_s_inscrit_pas(self):
        for description, cohortes, tarifs in (
                ("complet", {COURS: [candidate(places=5, inscrits=5)]}, {COURS: 250000}),
                ("aucune cohorte", {COURS: []}, {COURS: 250000}),
                ("retirée", {COURS: [candidate(publiee=False)]}, {COURS: 250000}),
                ("trop tard", {COURS: [candidate(debut=AUJOURD_HUI - datetime.timedelta(90))]},
                 {COURS: 250000}),
                ("sans tarif", {COURS: [candidate()]}, {})):
            with self.subTest(description):
                usage, _ = cas(cohortes=cohortes, tarifs=tarifs)
                self.assertFalse(usage.offre(COURS, APPRENANT).etat.ouverte)
                with self.assertRaises(InscriptionImpossible):
                    usage.executer(COURS, APPRENANT)

    def test_l_offre_est_une_lecture_et_n_inscrit_jamais_personne(self):
        """Afficher une page ne doit rien écrire. Une page vue par un robot d'indexation ne doit pas
        inscrire qui que ce soit."""
        usage, inscripteur = cas()
        for _ in range(3):
            usage.offre(COURS, APPRENANT)
        self.assertEqual((inscripteur.cohortes_faites, inscripteur.parcours_faits), ([], []))


class TestLOffreEstSereinementSerialisable(unittest.TestCase):
    def test_l_offre_se_rend_en_dictionnaire_pour_la_page(self):
        usage, _ = cas()
        rendu = usage.offre(COURS, APPRENANT).en_dict()
        self.assertEqual(rendu["etat"], "OUVERTE")
        self.assertEqual(rendu["message"], OUVERTE.message)
        self.assertEqual(rendu["montant"], 250000)
        self.assertNotIn("identifiant", rendu)

    def test_le_dictionnaire_ne_porte_que_des_valeurs_simples(self):
        """Il part en JSON vers la page : un objet de domaine qui s'y glisserait casserait à
        l'encodage, et le casse en production plutôt qu'en test."""
        usage, _ = cas()
        for cle, valeur in usage.offre(COURS, APPRENANT).en_dict().items():
            with self.subTest(cle):
                self.assertIsInstance(valeur, (str, int, bool, type(None)))


if __name__ == "__main__":
    unittest.main()
