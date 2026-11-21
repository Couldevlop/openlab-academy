"""Parcours offert à un apprenant, de bout en bout : inscription permise, dossier né puis dispensé, retour payant.

L'inscription a bien lieu — c'est là que la donnée est collectée — et le dossier existe avec le tarif du jour :
l'intendance voit la personne, ce que le parcours aurait coûté, qui l'a offert et quand. Retirer la gratuité
rend le dossier dû tel qu'il est.
"""
import frappe
from frappe.tests.utils import FrappeTestCase

from openlab_academy.application.gratuites import ACTION_OFFERT, ACTION_RETRAIT
from openlab_academy.entrypoints import gratuites as ecran
from openlab_academy.infrastructure.depot_dossiers_frappe import DepotDossiersFrappe
from openlab_academy.infrastructure.gratuites_frappe import DOCTYPE, GratuitesFrappe
from openlab_academy.tests.sans_lancement import sans_phase_de_lancement
from openlab_academy.tests.test_paiement_donnees_frappe import cours, tarif, utilisateur

JOURNAL = "Journal Paiement OpenLab"


class _Socle(FrappeTestCase):
    def setUp(self):
        sans_phase_de_lancement(self)
        self.cours = cours("Parcours gratuite test")
        tarif(self.cours).insert(ignore_permissions=True)
        self.apprenant = utilisateur("awa.gratuite@example.ci")
        self.gratuites = GratuitesFrappe()

    def tearDown(self):
        frappe.db.rollback()

    def inscrire(self):
        """Inscription depuis l'écran : le LMS ferme l'auto-inscription des parcours payants."""
        return ecran.inscrire(self.cours, self.apprenant)

    def s_inscrire_soi_meme(self):
        frappe.set_user(self.apprenant)
        try:
            return frappe.get_doc({"doctype": "LMS Enrollment", "course": self.cours,
                                   "member": self.apprenant}).insert(ignore_permissions=True)
        finally:
            frappe.set_user("Administrator")

    def dossier(self):
        return DepotDossiersFrappe().charger(self.apprenant, self.cours)

    def offrir(self, motif="Bourse"):
        return ecran.basculer(self.cours, self.apprenant, 1, motif)

    def rendre_payant(self):
        return ecran.basculer(self.cours, self.apprenant, 0)


class TestDepot(_Socle):
    def test_accorder_puis_retirer(self):
        self.assertFalse(self.gratuites.accordee(self.apprenant, self.cours))
        self.gratuites.accorder(self.apprenant, self.cours, "Administrator", "Bourse")
        self.assertTrue(self.gratuites.accordee(self.apprenant, self.cours))
        self.assertEqual(self.gratuites.apprenants(self.cours), (self.apprenant,))
        self.gratuites.retirer(self.apprenant, self.cours)
        self.assertFalse(self.gratuites.accordee(self.apprenant, self.cours))

    def test_accorder_est_rejouable(self):
        self.gratuites.accorder(self.apprenant, self.cours, "Administrator")
        self.gratuites.accorder(self.apprenant, self.cours, "Administrator")
        self.assertEqual(frappe.db.count(DOCTYPE, {"apprenant": self.apprenant, "parcours": self.cours}), 1)

    def test_qui_a_offert_et_quand_sont_gardes(self):
        self.gratuites.accorder(self.apprenant, self.cours, "Administrator", "Partenariat")
        doc = frappe.get_doc(DOCTYPE, {"apprenant": self.apprenant, "parcours": self.cours})
        self.assertEqual((doc.accordee_par, doc.motif), ("Administrator", "Partenariat"))
        self.assertTrue(doc.accordee_le)


class TestInscriptionOfferte(_Socle):
    def test_sans_gratuite_l_inscription_directe_reste_refusee(self):
        with self.assertRaises(frappe.ValidationError):
            self.s_inscrire_soi_meme()

    def test_inscription_depuis_l_ecran_refusee_sans_gratuite(self):
        with self.assertRaises(frappe.ValidationError):
            ecran.inscrire(self.cours, self.apprenant)

    def test_le_parcours_offert_s_inscrit_depuis_l_ecran(self):
        self.offrir()
        self.inscrire()
        self.assertTrue(frappe.db.exists("LMS Enrollment", {"course": self.cours, "member": self.apprenant}))

    def test_le_dossier_nait_et_se_dispense(self):
        self.offrir()
        self.inscrire()
        enregistre = self.dossier()
        self.assertIsNotNone(enregistre, "l'inscription doit laisser un dossier, même offert")
        self.assertTrue(enregistre.dossier.dispense)
        self.assertGreater(enregistre.dossier.total, 0, "le tarif du jour reste figé au dossier")

    def test_la_dispense_est_journalisee(self):
        self.offrir()
        self.inscrire()
        lignes = frappe.get_all(JOURNAL, {"dossier": self.dossier().nom}, ["action", "motif"])
        self.assertIn(ACTION_OFFERT, [l.action for l in lignes])


class TestRetourAuPayant(_Socle):
    def test_le_dossier_redevient_du(self):
        self.offrir()
        self.inscrire()
        self.rendre_payant()
        enregistre = self.dossier()
        self.assertFalse(enregistre.dossier.dispense)
        self.assertGreater(enregistre.dossier.reste, 0)

    def test_le_retrait_est_journalise(self):
        self.offrir()
        self.inscrire()
        self.rendre_payant()
        actions = frappe.get_all(JOURNAL, {"dossier": self.dossier().nom}, pluck="action")
        self.assertIn(ACTION_RETRAIT, actions)

    def test_bascule_rejouable(self):
        self.offrir()
        self.assertFalse(ecran.basculer(self.cours, self.apprenant, 1)["change"])
        self.rendre_payant()
        self.assertFalse(ecran.basculer(self.cours, self.apprenant, 0)["change"])


class TestEcran(_Socle):
    def test_les_inscrits_et_les_personnes_a_qui_le_parcours_est_offert(self):
        self.offrir()
        vue = ecran.inscrits(self.cours)
        ligne = next(l for l in vue["lignes"] if l["apprenant"] == self.apprenant)
        self.assertEqual((ligne["offert"], ligne["inscrit"]), (True, False))
        self.inscrire()
        ligne = next(l for l in ecran.inscrits(self.cours)["lignes"] if l["apprenant"] == self.apprenant)
        self.assertEqual((ligne["offert"], ligne["inscrit"], ligne["reste"]), (True, True, 0))

    def test_l_etat_est_lisible_jamais_une_valeur_brute(self):
        """L'écran montre « En retard », pas « en_retard » : les libellés sont ceux de l'intendance."""
        self.offrir()
        self.inscrire()
        self.rendre_payant()
        ligne = next(l for l in ecran.inscrits(self.cours)["lignes"] if l["apprenant"] == self.apprenant)
        self.assertEqual(ligne["etat"], "En retard")

    def test_ecran_reserve_a_l_administration(self):
        frappe.set_user(self.apprenant)
        try:
            with self.assertRaises(frappe.PermissionError):
                ecran.inscrits(self.cours)
            with self.assertRaises(frappe.PermissionError):
                ecran.basculer(self.cours, self.apprenant, 1)
        finally:
            frappe.set_user("Administrator")

    def test_parcours_inconnu_refuse(self):
        with self.assertRaises(frappe.ValidationError):
            ecran.basculer("parcours-qui-n-existe-pas", self.apprenant, 1)


class TestCreationDUnCompteApprenant(_Socle):
    """Créer un compte apprenant depuis l'administration, pour les tests utilisateurs.

    Frappe sait créer un utilisateur dans son interface, mais le compte né ainsi attend un courriel
    de bienvenue pour choisir son mot de passe — et les comptes d'envoi de production ne sont pas en
    service. Un compte d'essai doit donc naître utilisable tout de suite.
    """

    COURRIEL = "essai.apprenant@example.ci"

    def creer(self, **remplacements):
        valeurs = {"courriel": self.COURRIEL, "nom": "Essai"}
        valeurs.update(remplacements)
        return ecran.creer_apprenant(**valeurs)

    def test_le_compte_nait_actif_et_apprenant(self):
        reponse = self.creer()
        self.assertTrue(reponse["cree"])
        self.assertEqual(reponse["apprenant"], self.COURRIEL)
        self.assertTrue(frappe.db.get_value("User", self.COURRIEL, "enabled"))
        self.assertIn("LMS Student", frappe.get_roles(self.COURRIEL))

    def test_aucun_courriel_de_bienvenue_n_est_envoye(self):
        """Les comptes d'envoi de production ne sont pas en service : un compte qui attendrait son
        courriel serait inutilisable, et la file d'envoi garderait une trace pour rien."""
        avant = frappe.db.count("Email Queue")
        self.creer()
        self.assertEqual(frappe.db.count("Email Queue"), avant)

    def test_le_mot_de_passe_tire_est_rendu_une_seule_fois(self):
        reponse = self.creer()
        self.assertGreaterEqual(len(reponse["mot_de_passe"]), 12)
        self.assertEqual(self.creer()["mot_de_passe"], "")

    def test_le_mot_de_passe_fourni_n_est_pas_renvoye(self):
        """Celui qui l'a choisi le connaît déjà ; le renvoyer ne ferait que l'exposer une fois de
        plus, dans une réponse d'API et dans les journaux du navigateur."""
        reponse = self.creer(mot_de_passe="un-mot-de-passe-d-essai-1")
        self.assertTrue(reponse["cree"])
        self.assertEqual(reponse["mot_de_passe"], "")

    def empreinte(self):
        """Le mot de passe chiffré, lu sans tri : la table `__Auth` n'a pas de colonne `modified`."""
        return frappe.db.get_value("__Auth", {"name": self.COURRIEL, "fieldname": "password"},
                                   "password", order_by=None)

    def test_rejoue_il_ne_reinitialise_pas_le_mot_de_passe(self):
        """Une réinitialisation silencieuse ferait perdre son accès à quelqu'un."""
        self.creer(mot_de_passe="un-mot-de-passe-d-essai-1")
        avant = self.empreinte()
        self.assertTrue(avant)
        reponse = self.creer()
        self.assertFalse(reponse["cree"])
        self.assertEqual(self.empreinte(), avant)

    def test_le_nom_complet_est_celui_demande(self):
        self.creer(nom="Koné", prenom="Awa")
        self.assertEqual(frappe.db.get_value("User", self.COURRIEL, "full_name"), "Awa Koné")

    def test_un_courriel_vide_est_refuse(self):
        for valeur in ("", "   ", "\t"):
            with self.subTest(repr(valeur)):
                with self.assertRaises(frappe.ValidationError):
                    self.creer(courriel=valeur)

    def test_un_courriel_qui_n_est_pas_du_texte_est_refuse_par_frappe(self):
        """Frappe contrôle le type des arguments d'une méthode exposée avant qu'elle ne s'exécute :
        le refus vient de lui, et il vient plus tôt que le nôtre. On l'épingle pour que la garde
        reste visible si l'annotation disparaissait un jour."""
        for valeur in (None, 0, [], {"a": 1}):
            with self.subTest(repr(valeur)):
                with self.assertRaises(frappe.exceptions.FrappeTypeError):
                    self.creer(courriel=valeur)
        self.assertFalse(frappe.db.exists("User", self.COURRIEL))

    def test_un_courriel_mal_forme_est_refuse(self):
        with self.assertRaises(frappe.ValidationError):
            self.creer(courriel="pas-une-adresse")

    def test_un_nom_vide_est_refuse(self):
        with self.assertRaises(frappe.ValidationError):
            self.creer(nom="  ")

    def test_la_creation_est_reservee_a_l_administration(self):
        """Les droits sont vérifiés dans le point d'entrée : un appel direct à l'API passe par les
        mêmes contrôles que l'écran."""
        frappe.set_user(self.apprenant)
        try:
            with self.assertRaises(frappe.PermissionError):
                self.creer()
        finally:
            frappe.set_user("Administrator")
        self.assertFalse(frappe.db.exists("User", self.COURRIEL))

    def test_le_compte_cree_peut_recevoir_un_parcours_offert(self):
        """C'est l'enchaînement visé pour un test utilisateur : créer, offrir, inscrire."""
        self.creer()
        ecran.basculer(self.cours, self.COURRIEL, 1, "Test utilisateur")
        ecran.inscrire(self.cours, self.COURRIEL)
        self.assertTrue(frappe.db.exists("LMS Enrollment",
                                         {"course": self.cours, "member": self.COURRIEL}))
