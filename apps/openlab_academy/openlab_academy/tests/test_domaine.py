"""Les règles des domaines : ce qu'une teinte doit valoir, ce qu'une clé a le droit d'être.

La liste, elle, n'est pas ici : elle vit en base et s'édite depuis l'administration. Ce fichier
éprouve les règles et la semence livrée, pas un catalogue figé.
"""
import unittest

from openlab_academy.domain.domaine import (DOMAINES_PAR_DEFAUT, ECART_MINIMAL, SEUIL_CONTRASTE, Domaine,
                                            DomaineInconnu, TeinteIllisible, contraste, ecart_percu,
                                            normaliser, valider, verifier_teinte)

CLES_SEMEES = tuple(d.cle for d in DOMAINES_PAR_DEFAUT)


class TestLaCleEstValideeContreLaTable(unittest.TestCase):
    def test_une_cle_presente_dans_la_table_passe(self):
        for cle in CLES_SEMEES:
            with self.subTest(cle):
                self.assertEqual(valider(cle, CLES_SEMEES), cle)

    def test_une_cle_absente_est_refusee_et_dit_ce_qu_elle_attendait(self):
        """Le message doit nommer les clés admises : c'est une faute de frappe dans un fichier, et
        celui qui la lit n'a pas la table sous les yeux."""
        with self.assertRaises(DomaineInconnu) as leve:
            valider("intelligence-artificielle", CLES_SEMEES)
        message = str(leve.exception)
        self.assertIn("intelligence-artificielle", message)
        for cle in CLES_SEMEES:
            self.assertIn(cle, message)

    def test_une_variante_de_casse_ou_d_accent_ne_passe_pas(self):
        """« IA » et « ia » donneraient deux couleurs pour une même famille : la reconnaissance d'un
        coup d'œil, seule raison d'être de la bande, s'effondre. On refuse plutôt que de deviner."""
        for variante in ("IA", "Ia", "cybersécurité", "Données", " ia"):
            with self.subTest(variante):
                with self.assertRaises(DomaineInconnu):
                    valider(variante, CLES_SEMEES)

    def test_une_table_vide_le_dit_plutot_que_de_montrer_une_liste_vide(self):
        with self.assertRaises(DomaineInconnu) as leve:
            valider("ia", ())
        self.assertIn("aucun domaine", str(leve.exception))

    def test_l_absence_de_domaine_reste_permise(self):
        """Sans cette tolérance, la notion aurait invalidé d'un coup tous les parcours déjà écrits."""
        self.assertEqual(valider("", CLES_SEMEES), "")
        self.assertEqual(valider("", ()), "")


class TestUneTeinteDoitPorterSonTitre(unittest.TestCase):
    """La seule limite posée au choix de l'administration, et elle tient à l'accessibilité."""

    def test_une_teinte_sombre_est_acceptee_et_normalisee(self):
        self.assertEqual(verifier_teinte("#B35210"), "#b35210")
        self.assertEqual(verifier_teinte("b35210"), "#b35210")
        self.assertEqual(verifier_teinte("  #B35210  "), "#b35210")

    def test_une_teinte_trop_claire_est_refusee_et_explique_pourquoi(self):
        """Le message doit donner la mesure et le seuil : sinon l'administration tâtonne."""
        for claire in ("#ffffff", "#fcd80f", "#f39a5b", "#eef1f6"):
            with self.subTest(claire):
                with self.assertRaises(TeinteIllisible) as leve:
                    verifier_teinte(claire)
                message = str(leve.exception)
                self.assertIn(":1", message)
                self.assertIn(str(SEUIL_CONTRASTE), message)

    def test_ce_qui_n_est_pas_une_couleur_est_refuse(self):
        for mauvais in ("", "bleu", "#12345", "#1234567", "#gggggg", None):
            with self.subTest(repr(mauvais)):
                with self.assertRaises(TeinteIllisible):
                    normaliser(mauvais)  # type: ignore[arg-type]

    def test_le_seuil_est_bien_celui_du_texte_normal(self):
        """4,5:1 et non 3:1 : le titre d'une carte n'est pas un grand texte au sens de la norme."""
        self.assertEqual(SEUIL_CONTRASTE, 4.5)


class TestLaSemenceLivreeTientSesPropresRegles(unittest.TestCase):
    """Livrer une semence qui ne passerait pas sa propre validation serait une faute."""

    def test_chaque_teinte_semee_porte_du_texte_blanc(self):
        for domaine in DOMAINES_PAR_DEFAUT:
            with self.subTest(domaine.cle):
                self.assertEqual(verifier_teinte(domaine.teinte), domaine.teinte)

    def test_chaque_cle_semee_est_unique(self):
        self.assertEqual(len(set(CLES_SEMEES)), len(CLES_SEMEES))

    def test_les_teintes_semees_se_distinguent_entre_elles(self):
        """Voisines au point de se confondre, elles ne valent pas mieux qu'une seule couleur."""
        for i, premier in enumerate(DOMAINES_PAR_DEFAUT):
            for second in DOMAINES_PAR_DEFAUT[i + 1:]:
                with self.subTest(f"{premier.cle}/{second.cle}"):
                    self.assertGreater(ecart_percu(premier.teinte, second.teinte), ECART_MINIMAL)

    def test_chaque_cle_semee_s_ecrit_sans_accent_ni_majuscule(self):
        for cle in CLES_SEMEES:
            with self.subTest(cle):
                self.assertTrue(cle.isascii() and cle.islower() and " " not in cle)


class TestLesMesuresSontJustes(unittest.TestCase):
    """Sans ces garde-fous, un calcul faux validerait six nuances du même bleu."""

    def test_le_contraste_est_juste(self):
        self.assertAlmostEqual(contraste("#000000", "#ffffff"), 21.0, places=2)
        self.assertAlmostEqual(contraste("#ffffff", "#ffffff"), 1.0, places=2)
        self.assertAlmostEqual(contraste("#b35210", "#ffffff"), 5.08, places=2)

    def test_l_ecart_percu_est_juste(self):
        self.assertAlmostEqual(ecart_percu("#ffffff", "#ffffff"), 0.0, places=3)
        self.assertAlmostEqual(ecart_percu("#000000", "#ffffff"), 100.0, places=1)
        self.assertGreater(ecart_percu("#ff0000", "#00ff00"), 100)

    def test_le_contraste_ne_sait_pas_distinguer_deux_teintes(self):
        """La raison d'être du ΔE : ces deux couleurs sont évidemment différentes, et pourtant le
        rapport de contraste les tient pour presque identiques. Mesurer la clarté ne mesure pas la
        couleur."""
        marine, violet = "#244498", "#5b2a86"
        self.assertLess(contraste(marine, violet), 1.15)
        self.assertGreater(ecart_percu(marine, violet), ECART_MINIMAL)


class TestLeDomaineEstUneDonneeFigee(unittest.TestCase):
    def test_un_domaine_ne_se_modifie_pas(self):
        with self.assertRaises(Exception):
            DOMAINES_PAR_DEFAUT[0].teinte = "#000000"  # type: ignore[misc]

    def test_la_structure_porte_les_trois_informations(self):
        d = Domaine("essai", "Essai", "#000000")
        self.assertEqual((d.cle, d.libelle, d.teinte), ("essai", "Essai", "#000000"))
