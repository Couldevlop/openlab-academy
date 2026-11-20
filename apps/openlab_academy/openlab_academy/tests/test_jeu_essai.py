"""Le jeu d'essai du banc tient-il ses promesses — avant qu'on ouvre le navigateur pour s'en apercevoir.

Rien ici ne touche la base : ces tests lisent le plan de `entrypoints/jeu_essai.py`, pas ses écritures.
Ils existent parce qu'un jeu d'essai se dégrade en silence : on retire une copie, et l'écran des lots se
vide sans que rien ne proteste — un écran vide ressemble à un écran qui marche.
"""
import pathlib
import types
import unittest

from openlab_academy.domain.copie import lots
from openlab_academy.domain.reglages_evaluation import ConfigIA
from openlab_academy.entrypoints import jeu_essai

SOURCE = pathlib.Path(jeu_essai.__file__)


def propositions_ia() -> dict:
    """Les propositions de l'IA du plan, sous la forme que `lots` attend."""
    return {c["cle"]: types.SimpleNamespace(niveaux=c["ia"], confiance=c["confiance"])
            for c in jeu_essai.COPIES if "ia" in c}


class TestLeLotSeForme(unittest.TestCase):
    """L'écran des lots ne montre que des groupes d'au moins deux copies de même vecteur IA : une seule
    copie « propre » le laisserait vide, et on croirait la validation par lots cassée."""

    def test_le_plan_produit_un_lot_d_au_moins_deux_copies(self):
        groupes = lots(propositions_ia(), ConfigIA().seuil_confiance)
        self.assertTrue(groupes, "aucun lot : l'écran des lots serait vide")
        self.assertGreaterEqual(len(groupes[0]), 2)

    def test_les_cles_annoncees_par_le_plan_sont_celles_que_la_regle_du_domaine_retient(self):
        retenues = sorted(cle for groupe in lots(propositions_ia(), ConfigIA().seuil_confiance)
                          for cle in groupe)
        self.assertEqual(retenues, sorted(jeu_essai.lot_attendu()))

    def test_la_confiance_du_lot_passe_le_seuil_par_defaut_des_reglages(self):
        self.assertGreater(jeu_essai.CONFIANCE_LOT, ConfigIA().seuil_confiance)

    def test_la_copie_en_ecart_reste_hors_des_lots(self):
        ecart = next(c for c in jeu_essai.COPIES if c["cle"] == "ecart")
        self.assertNotIn("ecart", jeu_essai.lot_attendu())
        self.assertNotEqual(ecart["ia"], jeu_essai.BON)


class TestChaqueEcranEstAtteint(unittest.TestCase):
    """Neuf écrans, et pour chacun au moins une donnée qui le remplit. L'accueil n'en demande aucune : il
    ne fait que lister ce que le rôle ouvre."""

    def ecrans_couverts(self) -> set:
        return {"accueil"} | {plan["ecran"] for plans in
                              (jeu_essai.COPIES, jeu_essai.DOSSIERS, jeu_essai.VERSEMENTS)
                              for plan in plans} | {"relecture"}

    def test_aucun_ecran_ne_reste_sans_donnee(self):
        self.assertEqual(set(jeu_essai.ECRANS) - self.ecrans_couverts(), set())

    def test_aucun_ecran_annonce_n_est_inconnu(self):
        self.assertEqual(self.ecrans_couverts() - set(jeu_essai.ECRANS), set())


class TestLaVisiteuse(unittest.TestCase):
    """La session ouverte dans le navigateur est celle de la visiteuse : les écrans d'apprenant doivent
    lui montrer quelque chose, sans quoi la démonstration tourne à vide."""

    def test_elle_est_autrice_d_une_copie_publiee(self):
        publiees = [c for c in jeu_essai.COPIES
                    if c["statut"] == "publiee" and c["apprenant"] == jeu_essai.VISITEUSE]
        self.assertTrue(publiees, "sans copie publiée, l'écran « mon retour » n'a rien à montrer")

    def test_elle_a_une_relecture_a_faire(self):
        a_faire = [r for r in jeu_essai.RELECTURES
                   if r["relecteur"] == jeu_essai.VISITEUSE and r["statut"] == "à_faire"]
        self.assertTrue(a_faire)

    def test_sa_note_reste_en_attente_tant_que_sa_relecture_n_est_pas_faite(self):
        """L'écran « mon retour » doit montrer la note retenue, pas la note : c'est la règle du gating."""
        self.assertTrue(any(r["relecteur"] == jeu_essai.VISITEUSE and r["statut"] == "à_faire"
                            for r in jeu_essai.RELECTURES))

    def test_elle_a_un_dossier_de_paiement(self):
        self.assertIn(jeu_essai.VISITEUSE, [d["apprenant"] for d in jeu_essai.DOSSIERS])


class TestAucunPaiementSurLeParcoursGratuit(unittest.TestCase):
    """Un dossier posé sur le MOOC ferait afficher à l'intendance une somme due qui n'existe pas, et
    l'écran de paiement répondrait « parcours gratuit » à côté. C'est arrivé."""

    def test_le_parcours_payant_n_est_pas_le_parcours_gratuit(self):
        self.assertNotEqual(jeu_essai.COURS_PAYANT, jeu_essai.COURS_MOOC)

    def test_les_dossiers_ne_visent_que_le_parcours_payant(self):
        self.assertNotIn("COURS_MOOC", SOURCE.read_text(encoding="utf-8").split("def _dossier")[1])

    def test_un_dossier_pose_par_erreur_sur_le_parcours_gratuit_est_repris(self):
        """La purge reconnaît un dossier à son apprenant, pas à son parcours : celui qu'une version
        précédente avait posé sur le MOOC repart donc, sans qu'il faille nommer le parcours."""
        cibles = jeu_essai.cibles_purge(
            copies=[], equipes=[], paiements=[], relectures=[], propositions=[],
            dossiers=[("sur-le-mooc", jeu_essai.VISITEUSE), ("d-vrai", "eleve.reel@openlab.ci")])
        self.assertEqual(cibles["Dossier Paiement OpenLab"], {"sur-le-mooc"})


class TestAucunSecretDansLeDepot(unittest.TestCase):
    """Le mot de passe du formateur d'essai se tire au sort à l'exécution. Écrit ici, il partirait dans un
    dépôt public, et l'exception des identifiants inventés de `.gitleaks.toml` ne couvre pas ce fichier."""

    def test_le_mot_de_passe_se_tire_au_sort_ou_vient_de_l_environnement(self):
        texte = SOURCE.read_text(encoding="utf-8")
        self.assertIn("secrets.choice", texte)
        self.assertIn("OPENLAB_MDP_ESSAI", texte)

    def test_aucune_constante_ne_porte_un_mot_de_passe(self):
        for ligne in SOURCE.read_text(encoding="utf-8").splitlines():
            nom = ligne.split("=")[0].strip()
            if nom.isupper() and ("MDP" in nom or "PASSE" in nom or "PASSWORD" in nom):
                self.fail(f"mot de passe en dur : {ligne}")

    def test_deux_executions_ne_tirent_pas_le_meme_mot_de_passe(self):
        self.assertNotEqual(jeu_essai._mot_de_passe(), jeu_essai._mot_de_passe())


class TestLaPurgeNeTouchePasAuTravailDesAutres(unittest.TestCase):
    """Une premiere version effacait TOUTES les relectures, propositions, equipes, et tous les dossiers
    des deux parcours. Sur un banc qui porte autre chose que ce jeu, elle aurait detruit du travail.
    Chaque cas ci-dessous melange une ligne du jeu et une ligne etrangere, et exige que l'etrangere
    survive."""

    def cibles(self, **remplaces):
        donnees = {
            "copies": [("c-essai", jeu_essai.MARQUE + "abcd"), ("c-vraie", "DEPOT-2026-001")],
            "equipes": [("e-essai", jeu_essai.FORMATEUR), ("e-vraie", "prof@openlab.ci")],
            "dossiers": [("d-essai", jeu_essai.VISITEUSE), ("d-vrai", "eleve.reel@openlab.ci")],
            "paiements": [("p-essai", "d-essai", jeu_essai.MARQUE + "A1B2C3"),
                          ("p-vrai", "d-vrai", "CINETPAY-9931"),
                          ("p-reel-sur-dossier-essai", "d-essai", "CINETPAY-7742")],
            "relectures": [("r-essai", "c-essai"), ("r-vraie", "c-vraie")],
            "propositions": [("n-essai", "c-essai"), ("n-vraie", "c-vraie")],
        }
        donnees.update(remplaces)
        return jeu_essai.cibles_purge(**donnees)

    def test_une_copie_deposee_autrement_survit(self):
        self.assertEqual(self.cibles()["Copie OpenLab"], {"c-essai"})

    def test_les_relectures_et_propositions_d_une_copie_etrangere_survivent(self):
        cibles = self.cibles()
        self.assertEqual(cibles["Relecture Pair OpenLab"], {"r-essai"})
        self.assertEqual(cibles["Proposition OpenLab"], {"n-essai"})

    def test_une_equipe_de_correction_reelle_survit(self):
        self.assertEqual(self.cibles()["Equipe Correction OpenLab"], {"e-essai"})

    def test_le_dossier_de_paiement_d_un_vrai_apprenant_survit(self):
        self.assertEqual(self.cibles()["Dossier Paiement OpenLab"], {"d-essai"})

    def test_un_versement_reel_n_est_jamais_efface_meme_sur_un_dossier_d_essai(self):
        """Il empechera la suppression du dossier, et c'est voulu : un echec bruyant plutot qu'une
        perte silencieuse."""
        self.assertEqual(self.cibles()["Paiement OpenLab"], {"p-essai"})

    def test_sur_un_banc_sans_rien_d_etranger_tout_le_jeu_part(self):
        cibles = self.cibles(copies=[("c-essai", jeu_essai.MARQUE + "abcd")])
        self.assertEqual(cibles["Copie OpenLab"], {"c-essai"})

    def test_chaque_famille_a_son_rang_de_suppression(self):
        """Ce qui pointe vers le reste se retire d'abord, sinon la suppression echoue sur un lien."""
        self.assertEqual(set(jeu_essai.ORDRE_PURGE), set(self.cibles()))
        rang = jeu_essai.ORDRE_PURGE.index
        self.assertLess(rang("Relecture Pair OpenLab"), rang("Copie OpenLab"))
        self.assertLess(rang("Proposition OpenLab"), rang("Copie OpenLab"))
        self.assertLess(rang("Paiement OpenLab"), rang("Dossier Paiement OpenLab"))


class TestRienNeSExecuteHorsDUnBanc(unittest.TestCase):
    """`run` efface et reecrit. Sur un site servi, il n'a rien a faire."""

    def test_run_refuse_un_site_qui_n_est_pas_en_developper_mode(self):
        garde = SOURCE.read_text(encoding="utf-8").split("def run(")[0]
        self.assertIn("developer_mode", garde)

    def test_run_appelle_la_garde_avant_toute_ecriture(self):
        corps = SOURCE.read_text(encoding="utf-8").split("def run(")[1]
        self.assertLess(corps.index("_refuser_hors_developpement()"), corps.index("_purger()"))


class TestLePlanResteCoherent(unittest.TestCase):
    def test_chaque_relecture_porte_sur_une_copie_du_plan(self):
        cles = {c["cle"] for c in jeu_essai.COPIES}
        for relecture in jeu_essai.RELECTURES:
            self.assertIn(relecture["copie"], cles)

    def test_chaque_versement_vise_un_apprenant_qui_a_un_dossier(self):
        avec_dossier = {d["apprenant"] for d in jeu_essai.DOSSIERS}
        for versement in jeu_essai.VERSEMENTS:
            self.assertIn(versement["apprenant"], avec_dossier)

    def test_aucun_versement_ne_vise_un_dossier_dispense(self):
        dispenses = {d["apprenant"] for d in jeu_essai.DOSSIERS if d["dispense"]}
        for versement in jeu_essai.VERSEMENTS:
            self.assertNotIn(versement["apprenant"], dispenses)

    def test_chaque_copie_notee_porte_une_note_et_son_total(self):
        for copie in jeu_essai.COPIES:
            if copie["statut"] == "publiee":
                self.assertIn("note", copie)
                self.assertIn("note_sur", copie)

    def test_une_copie_hors_chaine_n_a_plus_d_etape(self):
        for copie in jeu_essai.COPIES:
            if copie["statut"] == "publiee":
                self.assertIsNone(copie["etape"])

    def test_une_copie_en_correction_garde_une_etape(self):
        """`copies_en_correction` exige une étape courante : sans elle, la copie sort de la file."""
        for copie in jeu_essai.COPIES:
            if copie["statut"] == "a_corriger":
                self.assertIsNotNone(copie["etape"])

    def test_tous_les_apprenants_du_plan_sont_declares(self):
        connus = {courriel for courriel, _, _ in jeu_essai.APPRENANTS}
        for plans, champ in ((jeu_essai.COPIES, "apprenant"), (jeu_essai.DOSSIERS, "apprenant"),
                             (jeu_essai.VERSEMENTS, "apprenant")):
            for plan in plans:
                self.assertIn(plan[champ], connus)

    def test_le_formateur_n_est_pas_un_apprenant(self):
        self.assertNotIn(jeu_essai.FORMATEUR, {courriel for courriel, _, _ in jeu_essai.APPRENANTS})
