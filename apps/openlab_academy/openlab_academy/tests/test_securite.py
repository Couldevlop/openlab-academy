"""Les commandes du terminal qui inscrivent, activent et éteignent le second facteur.

Ce qui se teste ici n'est pas la cryptographie, déjà couverte ailleurs, mais l'ordre imposé : le
second facteur ne s'active pas avant d'avoir été inscrit, et il s'éteint en toute circonstance.
Un écran d'administration qui se referme sur son administrateur ne se répare pas depuis cet écran.

Les commandes appellent `frappe.db.commit`, sans quoi un administrateur verrouillé le resterait
jusqu'au prochain écrit. Le test le neutralise, pour que le `rollback` du socle rende le site à
l'état où il l'a trouvé.
"""
import io
import unittest.mock

import frappe
import pyotp
from frappe.tests.utils import FrappeTestCase

from openlab_academy.entrypoints import securite
from openlab_academy.infrastructure import deuxieme_facteur_frappe as second

ROLE = "System Manager"
AUTRE_ROLE = "Course Creator"


class _Socle(FrappeTestCase):
    def setUp(self):
        frappe.set_user("Administrator")
        self.comptes = []
        self.compte = self.utilisateur("terminal.2fa@essai.test")
        patch = unittest.mock.patch.object(frappe.db, "commit")
        self.addCleanup(patch.stop)
        patch.start()

    def tearDown(self):
        for compte in self.comptes:
            second.oublier(compte)
        frappe.set_user("Administrator")
        frappe.db.rollback()

    def utilisateur(self, courriel, role=ROLE):
        if not frappe.db.exists("User", courriel):
            frappe.get_doc({"doctype": "User", "email": courriel, "first_name": "Essai",
                            "enabled": 1, "send_welcome_email": 0,
                            "roles": [{"role": role}]}).insert(ignore_permissions=True)
        self.comptes.append(courriel)
        return courriel

    def lancer(self, commande, *args, **kwargs):
        """Lance une commande et rend ce qu'elle a écrit dans le terminal."""
        sortie = io.StringIO()
        with unittest.mock.patch("sys.stdout", sortie):
            commande(*args, **kwargs)
        return sortie.getvalue()

    def inscrire(self, compte):
        code = pyotp.TOTP(second.secret(compte)).now()
        self.lancer(securite.confirmer_le_second_facteur, code, utilisateur=compte)
        return compte


class TestLeChoixDuCompte(_Socle):
    def test_un_compte_introuvable_arrete_la_commande(self):
        with self.assertRaises(SystemExit) as arret:
            securite.inscrire_le_second_facteur("personne@essai.test")
        self.assertIn("introuvable", str(arret.exception))

    def test_sans_compte_la_commande_dit_comment_le_passer(self):
        """Lancée par `bench execute`, la session est celle de l'invité : deviner serait pire."""
        frappe.set_user("Guest")
        with self.assertRaises(SystemExit) as arret:
            securite.inscrire_le_second_facteur()
        self.assertIn("--kwargs", str(arret.exception))

    def test_le_compte_de_la_session_sert_par_defaut(self):
        frappe.set_user(self.compte)
        self.assertIn(self.compte, self.lancer(securite.inscrire_le_second_facteur))


class TestLInscriptionAuTerminal(_Socle):
    def test_le_qr_s_affiche_et_rien_n_est_encore_inscrit(self):
        sortie = self.lancer(securite.inscrire_le_second_facteur, self.compte)
        self.assertIn(self.compte, sortie)
        self.assertIn("confirmer_le_second_facteur", sortie)
        self.assertFalse(second.inscrit(self.compte))

    def test_un_code_faux_arrete_la_commande(self):
        with self.assertRaises(SystemExit) as arret:
            securite.confirmer_le_second_facteur("000000", utilisateur=self.compte)
        self.assertIn("Code refusé", str(arret.exception))
        self.assertFalse(second.inscrit(self.compte))

    def test_un_code_juste_inscrit_et_annonce_la_suite(self):
        code = pyotp.TOTP(second.secret(self.compte)).now()
        sortie = self.lancer(securite.confirmer_le_second_facteur, code, utilisateur=self.compte)
        self.assertTrue(second.inscrit(self.compte))
        self.assertIn("activer_le_second_facteur", sortie)


class TestLActivationAuTerminal(_Socle):
    def test_l_activation_refuse_tant_que_personne_n_est_inscrit(self):
        """Le cas qui compte : activer sans porteur fermerait la porte sur tout le monde."""
        for compte in second.porteurs((ROLE,)):
            second.oublier(compte)
        with self.assertRaises(SystemExit) as arret:
            securite.activer_le_second_facteur(roles=ROLE)
        self.assertIn("Activation refusée", str(arret.exception))
        self.assertEqual(frappe.db.get_single_value(securite.REGLAGES, "deuxieme_facteur"), 0)
        self.assertEqual(frappe.db.get_single_value(second.SYSTEME, "enable_two_factor_auth"), 0)

    def test_l_activation_passe_une_fois_un_porteur_inscrit(self):
        self.inscrire(self.compte)
        sortie = self.lancer(securite.activer_le_second_facteur, roles=ROLE, methode="OTP App")
        self.assertIn(self.compte, sortie)
        self.assertEqual(frappe.db.get_single_value(second.SYSTEME, "enable_two_factor_auth"), 1)
        self.assertEqual(frappe.db.get_value("Role", ROLE, "two_factor_auth"), 1)

    def test_sans_argument_l_activation_reprend_le_reglage_du_site(self):
        """Le cas ordinaire : les rôles ont déjà été choisis dans l'administration."""
        frappe.db.set_single_value(securite.REGLAGES, "roles_deuxieme_facteur", ROLE)
        self.inscrire(self.compte)
        self.lancer(securite.activer_le_second_facteur)
        self.assertEqual(frappe.db.get_value("Role", ROLE, "two_factor_auth"), 1)

    def test_les_roles_se_passent_separes_par_des_virgules(self):
        self.inscrire(self.compte)
        self.utilisateur("autre.2fa@essai.test", role=AUTRE_ROLE)
        self.inscrire("autre.2fa@essai.test")
        self.lancer(securite.activer_le_second_facteur, roles=f"{ROLE},{AUTRE_ROLE}")
        self.assertEqual(frappe.db.get_single_value(securite.REGLAGES, "roles_deuxieme_facteur"),
                         f"{ROLE}\n{AUTRE_ROLE}")


class TestLExtinctionAuTerminal(_Socle):
    def test_eteindre_rouvre_la_porte_et_garde_les_inscriptions(self):
        self.inscrire(self.compte)
        self.lancer(securite.activer_le_second_facteur, roles=ROLE)
        self.lancer(securite.eteindre_le_second_facteur)
        self.assertEqual(frappe.db.get_single_value(second.SYSTEME, "enable_two_factor_auth"), 0)
        self.assertEqual(frappe.db.get_value("Role", ROLE, "two_factor_auth"), 0)
        self.assertTrue(second.inscrit(self.compte))

    def test_eteindre_retire_aussi_un_role_marque_ailleurs(self):
        """Ici, et ici seulement, on retire sans distinction : c'est un ordre explicite de rouvrir."""
        frappe.db.set_value("Role", AUTRE_ROLE, "two_factor_auth", 1)
        self.lancer(securite.eteindre_le_second_facteur)
        self.assertEqual(frappe.db.get_value("Role", AUTRE_ROLE, "two_factor_auth"), 0)
