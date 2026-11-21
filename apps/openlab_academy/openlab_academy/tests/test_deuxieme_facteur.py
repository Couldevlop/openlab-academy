"""Règles du second facteur : qui le porte, et à quelle condition on peut l'activer.

Le test qui compte est celui du verrou : activer sans porteur ferme la porte pour toujours, parce
que le code d'inscription part par courriel et que les comptes d'envoi ne sont pas en service.
"""
import unittest

from openlab_academy.domain.deuxieme_facteur import (METHODE_PAR_DEFAUT, ROLE_APPRENANT, Reglage,
                                                     SecondFacteurInvalide, exiger_un_porteur,
                                                     methode_valide, roles_demandes)

CONNUS = ("System Manager", "Intendant OpenLab", "Course Creator", ROLE_APPRENANT)


class TestLaMethode(unittest.TestCase):
    def test_une_methode_vide_retombe_sur_celle_par_defaut(self):
        self.assertEqual(methode_valide(""), METHODE_PAR_DEFAUT)
        self.assertEqual(methode_valide(None), METHODE_PAR_DEFAUT)

    def test_les_methodes_connues_passent(self):
        self.assertEqual(methode_valide("OTP App"), "OTP App")
        self.assertEqual(methode_valide("Email"), "Email")

    def test_une_methode_inconnue_est_refusee_en_disant_les_choix(self):
        with self.assertRaises(SecondFacteurInvalide) as e:
            methode_valide("SMS")
        self.assertIn("OTP App", str(e.exception))


class TestLesRolesDemandes(unittest.TestCase):
    def test_un_role_par_ligne_dans_l_ordre_de_saisie(self):
        self.assertEqual(roles_demandes("System Manager\nIntendant OpenLab", CONNUS),
                         ("System Manager", "Intendant OpenLab"))

    def test_les_lignes_vides_et_les_espaces_sont_ignores(self):
        self.assertEqual(roles_demandes("  System Manager  \n\n\n", CONNUS), ("System Manager",))

    def test_un_role_repete_ne_compte_qu_une_fois(self):
        self.assertEqual(roles_demandes("System Manager\nSystem Manager", CONNUS),
                         ("System Manager",))

    def test_un_role_inconnu_est_refuse_plutot_qu_ignore(self):
        """Ignoré, il donnerait le sentiment d'une protection posée alors que rien ne l'est."""
        with self.assertRaises(SecondFacteurInvalide) as e:
            roles_demandes("System Manger", CONNUS)  # faute de frappe volontaire
        self.assertIn("System Manger", str(e.exception))

    def test_le_role_des_apprenants_est_refuse(self):
        with self.assertRaises(SecondFacteurInvalide) as e:
            roles_demandes(ROLE_APPRENANT, CONNUS)
        self.assertIn(ROLE_APPRENANT, str(e.exception))

    def test_un_reglage_vide_ne_demande_aucun_role(self):
        self.assertEqual(roles_demandes("", CONNUS), ())


class TestLeVerrouDAccès(unittest.TestCase):
    """Le garde-fou qui empêche de s'enfermer dehors."""

    def reglage(self, actif=True, roles=("System Manager",)):
        return Reglage(actif=actif, methode="OTP App", roles=roles)

    def test_activer_sans_aucun_porteur_est_refuse(self):
        with self.assertRaises(SecondFacteurInvalide) as e:
            exiger_un_porteur(self.reglage(), inscrits=())
        self.assertIn("courriel", str(e.exception))

    def test_activer_avec_un_porteur_passe(self):
        exiger_un_porteur(self.reglage(), inscrits=("admin@openlab.test",))

    def test_activer_sans_aucun_role_est_refuse(self):
        """Actif mais sur personne : la case cochée laisserait croire à une protection."""
        with self.assertRaises(SecondFacteurInvalide) as e:
            exiger_un_porteur(self.reglage(roles=()), inscrits=("admin@openlab.test",))
        self.assertIn("ne protégerait rien", str(e.exception))

    def test_desactiver_ne_demande_aucun_porteur(self):
        """On doit toujours pouvoir éteindre, y compris depuis une situation cassée."""
        exiger_un_porteur(self.reglage(actif=False), inscrits=())
        exiger_un_porteur(self.reglage(actif=False, roles=()), inscrits=())
