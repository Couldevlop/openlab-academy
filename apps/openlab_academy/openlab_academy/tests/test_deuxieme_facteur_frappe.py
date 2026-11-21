"""Le second facteur posé dans Frappe : réglages du site, drapeau des rôles, et le verrou d'accès.

Le test qui compte est celui qui refuse l'activation quand plus personne ne peut entrer. Un second
facteur mal posé ne se répare pas depuis l'écran qu'il vient de fermer.
"""
import frappe
import pyotp
from frappe.tests.utils import FrappeTestCase

from openlab_academy.domain.deuxieme_facteur import Reglage, SecondFacteurInvalide
from openlab_academy.infrastructure import deuxieme_facteur_frappe as second

ROLE = "System Manager"
AUTRE_ROLE = "Course Creator"


class _Socle(FrappeTestCase):
    def setUp(self):
        frappe.set_user("Administrator")
        self.comptes = []
        self.compte = self.utilisateur("porteur.2fa@essai.test")

    def tearDown(self):
        # La marque d'inscription est aussi tenue en cache : le `rollback` défait la ligne en base
        # mais pas le cache, et un test suivant croirait le compte déjà inscrit. On l'efface
        # explicitement. En service il n'y a pas de rollback, donc rien à corriger de ce côté.
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

    def inscrire(self, compte):
        """Enrôle réellement le compte : on vérifie un code produit par la même horloge."""
        code = pyotp.TOTP(second.secret(compte)).now()
        self.assertTrue(second.confirmer(compte, code))
        return compte


class TestLInscription(_Socle):
    def test_un_compte_neuf_n_est_pas_inscrit(self):
        self.assertFalse(second.inscrit(self.compte))

    def test_le_lien_d_inscription_porte_le_compte_et_le_secret(self):
        lien = second.lien_d_inscription(self.compte)
        self.assertTrue(lien.startswith("otpauth://totp/"))
        self.assertIn("secret=", lien)
        self.assertIn("porteur.2fa", lien)

    def test_le_secret_est_stable_entre_deux_lectures(self):
        """Sinon le QR photographié ne vaudrait plus rien à la vérification suivante."""
        self.assertEqual(second.secret(self.compte), second.secret(self.compte))

    def test_un_code_juste_inscrit_le_compte(self):
        self.inscrire(self.compte)
        self.assertTrue(second.inscrit(self.compte))

    def test_un_code_faux_n_inscrit_rien(self):
        self.assertFalse(second.confirmer(self.compte, "000000"))
        self.assertFalse(second.inscrit(self.compte))

    def test_un_code_vide_n_inscrit_rien(self):
        self.assertFalse(second.confirmer(self.compte, ""))
        self.assertFalse(second.inscrit(self.compte))

    def test_oublier_remet_le_compte_a_l_enrolement(self):
        self.inscrire(self.compte)
        second.oublier(self.compte)
        self.assertFalse(second.inscrit(self.compte))


class TestLesPorteurs(_Socle):
    def test_seuls_les_comptes_inscrits_comptent(self):
        self.assertNotIn(self.compte, second.porteurs((ROLE,)))
        self.inscrire(self.compte)
        self.assertIn(self.compte, second.porteurs((ROLE,)))

    def test_un_compte_desactive_ne_compte_pas(self):
        """Il ne pourra pas ouvrir la porte : le compter laisserait croire qu'il le peut."""
        self.inscrire(self.compte)
        frappe.db.set_value("User", self.compte, "enabled", 0)
        self.assertNotIn(self.compte, second.porteurs((ROLE,)))

    def test_un_compte_d_un_autre_role_ne_compte_pas(self):
        autre = self.utilisateur("autre.2fa@essai.test", role=AUTRE_ROLE)
        self.inscrire(autre)
        self.assertNotIn(autre, second.porteurs((ROLE,)))

    def test_sans_role_demande_il_n_y_a_aucun_porteur(self):
        self.inscrire(self.compte)
        self.assertEqual(second.porteurs(()), ())


class TestLeVerrouALApplication(_Socle):
    """Ce que le garde-fou empêche, mesuré sur la vraie base."""

    def test_activer_sans_porteur_est_refuse_et_ne_touche_a_rien(self):
        avant = frappe.db.get_single_value(second.SYSTEME, "enable_two_factor_auth")
        with self.assertRaises(SecondFacteurInvalide):
            second.appliquer(Reglage(actif=True, methode="OTP App", roles=(ROLE,)))
        self.assertEqual(frappe.db.get_single_value(second.SYSTEME, "enable_two_factor_auth"), avant)

    def test_activer_avec_un_porteur_pose_le_reglage_du_site(self):
        self.inscrire(self.compte)
        second.appliquer(Reglage(actif=True, methode="OTP App", roles=(ROLE,)))
        self.assertEqual(frappe.db.get_single_value(second.SYSTEME, "enable_two_factor_auth"), 1)
        self.assertEqual(frappe.db.get_single_value(second.SYSTEME, "two_factor_method"), "OTP App")
        self.assertEqual(frappe.db.get_value("Role", ROLE, "two_factor_auth"), 1)

    def test_un_role_retire_du_reglage_cesse_d_etre_soumis(self):
        """Sinon décocher dans l'administration ne changerait rien, ce qui est le pire des deux."""
        self.inscrire(self.compte)
        second.appliquer(Reglage(actif=True, methode="OTP App", roles=(ROLE, AUTRE_ROLE)))
        self.assertEqual(frappe.db.get_value("Role", AUTRE_ROLE, "two_factor_auth"), 1)
        second.appliquer(Reglage(actif=True, methode="OTP App", roles=(ROLE,)))
        self.assertEqual(frappe.db.get_value("Role", AUTRE_ROLE, "two_factor_auth"), 0)
        self.assertEqual(frappe.db.get_value("Role", ROLE, "two_factor_auth"), 1)

    def test_eteindre_ce_qu_on_a_pose_fonctionne_meme_sans_aucun_porteur(self):
        """On doit toujours pouvoir rouvrir, sans avoir à toucher la base à la main."""
        self.inscrire(self.compte)
        second.appliquer(Reglage(actif=True, methode="OTP App", roles=(ROLE,)))
        second.oublier(self.compte)
        second.appliquer(Reglage(actif=False, methode="OTP App", roles=()))
        self.assertEqual(frappe.db.get_single_value(second.SYSTEME, "enable_two_factor_auth"), 0)
        self.assertEqual(frappe.db.get_value("Role", ROLE, "two_factor_auth"), 0)


class TestLaLectureDuReglage(_Socle):
    def test_le_reglage_est_lu_depuis_l_administration(self):
        frappe.db.set_single_value(second.REGLAGES, "deuxieme_facteur", 1)
        frappe.db.set_single_value(second.REGLAGES, "methode_deuxieme_facteur", "Email")
        frappe.db.set_single_value(second.REGLAGES, "roles_deuxieme_facteur", f"{ROLE}\n{AUTRE_ROLE}")
        r = second.reglage()
        self.assertTrue(r.actif)
        self.assertEqual(r.methode, "Email")
        self.assertEqual(r.roles, (ROLE, AUTRE_ROLE))

    def test_un_role_mal_orthographie_est_refuse_a_la_lecture(self):
        frappe.db.set_single_value(second.REGLAGES, "roles_deuxieme_facteur", "System Manger")
        with self.assertRaises(SecondFacteurInvalide):
            second.reglage()

    def test_preparer_n_active_pas_sur_un_reglage_intenable(self):
        """Une migration ne verrouille pas le site faute de porteur — et ne désarme rien non plus."""
        frappe.db.set_single_value(second.SYSTEME, "enable_two_factor_auth", 0)
        frappe.db.set_single_value(second.REGLAGES, "deuxieme_facteur", 1)
        frappe.db.set_single_value(second.REGLAGES, "roles_deuxieme_facteur", ROLE)
        for compte in second.porteurs((ROLE,)):
            second.oublier(compte)
        second.preparer()
        self.assertEqual(frappe.db.get_single_value(second.SYSTEME, "enable_two_factor_auth"), 0)


class TestCeQuiNeNousAppartientPas(_Socle):
    """La plateforme ne retire jamais un second facteur qu'elle n'a pas posé.

    Le sens « ne pas fermer la porte » vaut pour l'activation. Pris à l'envers, il autoriserait une
    migration à éteindre une protection mise par quelqu'un d'autre, ou une faute de frappe dans un
    nom de rôle à désarmer un site entier. C'est la direction dangereuse : on ne descend jamais le
    niveau d'authentification sans un ordre explicite.
    """

    def test_une_migration_n_eteint_pas_un_second_facteur_pose_ailleurs(self):
        frappe.db.set_single_value(second.SYSTEME, "enable_two_factor_auth", 1)
        frappe.db.set_single_value(second.REGLAGES, "deuxieme_facteur", 0)
        frappe.db.set_single_value(second.REGLAGES, "roles_deuxieme_facteur", ROLE)
        frappe.db.set_single_value(second.REGLAGES, "roles_deuxieme_facteur_poses", "")
        second.preparer()
        self.assertEqual(frappe.db.get_single_value(second.SYSTEME, "enable_two_factor_auth"), 1)

    def test_une_migration_ne_desarme_pas_un_role_pose_ailleurs(self):
        frappe.db.set_value("Role", AUTRE_ROLE, "two_factor_auth", 1)
        frappe.db.set_single_value(second.REGLAGES, "roles_deuxieme_facteur_poses", "")
        frappe.db.set_single_value(second.REGLAGES, "roles_deuxieme_facteur", ROLE)
        frappe.db.set_single_value(second.REGLAGES, "deuxieme_facteur", 1)
        self.inscrire(self.compte)
        second.preparer()
        self.assertEqual(frappe.db.get_value("Role", AUTRE_ROLE, "two_factor_auth"), 1)

    def test_un_reglage_illisible_ne_desarme_rien(self):
        """Une faute de frappe dans un nom de rôle ne doit pas valoir extinction du site."""
        frappe.db.set_single_value(second.SYSTEME, "enable_two_factor_auth", 1)
        frappe.db.set_single_value(second.REGLAGES, "deuxieme_facteur", 1)
        frappe.db.set_single_value(second.REGLAGES, "roles_deuxieme_facteur", "System Manger")
        second.preparer()
        self.assertEqual(frappe.db.get_single_value(second.SYSTEME, "enable_two_factor_auth"), 1)

    def test_sans_porteur_la_migration_n_active_pas_mais_n_eteint_pas_non_plus(self):
        frappe.db.set_single_value(second.SYSTEME, "enable_two_factor_auth", 1)
        frappe.db.set_single_value(second.REGLAGES, "deuxieme_facteur", 1)
        frappe.db.set_single_value(second.REGLAGES, "roles_deuxieme_facteur", ROLE)
        for compte in second.porteurs((ROLE,)):
            second.oublier(compte)
        second.preparer()
        self.assertEqual(frappe.db.get_single_value(second.SYSTEME, "enable_two_factor_auth"), 1)

    def test_ce_que_la_plateforme_a_pose_est_trace_et_repris(self):
        """Décocher dans l'administration doit encore retirer ce que la plateforme avait posé."""
        self.inscrire(self.compte)
        frappe.db.set_single_value(second.REGLAGES, "roles_deuxieme_facteur", ROLE)
        second.appliquer(Reglage(actif=True, methode="OTP App", roles=(ROLE,)))
        self.assertEqual(frappe.db.get_single_value(second.REGLAGES,
                                                    "roles_deuxieme_facteur_poses"), ROLE)
        frappe.db.set_single_value(second.REGLAGES, "deuxieme_facteur", 0)
        second.preparer()
        self.assertEqual(frappe.db.get_value("Role", ROLE, "two_factor_auth"), 0)
        self.assertEqual(frappe.db.get_single_value(second.SYSTEME, "enable_two_factor_auth"), 0)
