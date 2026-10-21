import unittest

from openlab_academy.domain.reglages import ReglagesInvalides
from openlab_academy.domain.reglages_evaluation import (
    CHAINES_DEFAUT, RESERVE_REPONSE_JETONS, Chaine, ConfigEtape, ConfigIA, Etape, Expiration, ReglagesEvaluation,
    Resoumission, Surcharge, TypeExercice,
)

E = Etape


def chaine_avec(etapes_actives, **options):
    return Chaine(tuple(ConfigEtape(e, e in etapes_actives, 1, Expiration.PASSER) for e in Etape), **options)


class TestDefauts(unittest.TestCase):
    def setUp(self):
        self.r = ReglagesEvaluation()

    def actives(self, type_):
        c = CHAINES_DEFAUT[type_]
        return {e for e in Etape if c.active(e)}

    def test_mise_en_situation(self):
        self.assertEqual(self.actives(TypeExercice.MISE_EN_SITUATION), {E.CONTROLES, E.IA, E.FORMATEUR})

    def test_livrable(self):
        self.assertEqual(self.actives(TypeExercice.LIVRABLE),
                         {E.AUTO_EVALUATION, E.CONTROLES, E.IA, E.PAIRS, E.FORMATEUR})

    def test_projet(self):
        self.assertEqual(self.actives(TypeExercice.PROJET), set(Etape) - {E.JURY})

    def test_capstone(self):
        self.assertEqual(self.actives(TypeExercice.CAPSTONE), {E.CONTROLES, E.IA, E.JURY, E.FORMATEUR})

    def test_delais_et_expirations(self):
        c = CHAINES_DEFAUT[TypeExercice.PROJET]
        self.assertEqual((c.config(E.CONTROLES).delai_heures, c.config(E.IA).delai_heures), (1, 1))
        self.assertEqual((c.config(E.PAIRS).delai_heures, c.config(E.PAIRS).expiration), (72, Expiration.REATTRIBUER))
        self.assertEqual((c.config(E.JURY).delai_heures, c.config(E.JURY).expiration), (168, Expiration.ESCALADER))
        self.assertEqual((c.config(E.FORMATEUR).delai_heures, c.config(E.FORMATEUR).expiration),
                         (72, Expiration.ESCALADER))

    def test_options_par_defaut(self):
        c = CHAINES_DEFAUT[TypeExercice.PROJET]
        self.assertEqual((c.nb_pairs, c.anonymat, c.note_masquee_avant_relectures, c.note_sur, c.seuil_reussite),
                         (3, True, True, 20, 10.0))
        self.assertFalse(self.r.publication_provisoire)
        self.assertEqual(self.r.hotes_depots, ("github.com", "gitlab.com"))
        self.assertEqual(sum(p for _, p in self.r.grille_generique), 100)
        self.assertEqual(self.r.grille_generique[0], ("Pertinence", 30))
        self.assertEqual(len(self.r.niveaux_generiques), 4)
        self.assertTrue(self.r.ia.tournures_injection)

    def test_config_absente(self):
        c = Chaine((ConfigEtape(E.FORMATEUR, True, 1, Expiration.ESCALADER),))
        self.assertFalse(c.active(E.IA))
        with self.assertRaises(ReglagesInvalides):
            c.config(E.IA)


class TestValidation(unittest.TestCase):
    def test_formateur_inactif_interdit(self):
        with self.assertRaisesRegex(ReglagesInvalides, "formateur"):
            chaine_avec({E.IA})

    def test_formateur_absent_interdit(self):
        with self.assertRaises(ReglagesInvalides):
            Chaine((ConfigEtape(E.IA, True, 1, Expiration.PASSER),))

    def test_nb_pairs_negatif(self):
        with self.assertRaises(ReglagesInvalides):
            chaine_avec({E.FORMATEUR}, nb_pairs=-1)

    def test_delai_negatif(self):
        with self.assertRaises(ReglagesInvalides):
            Chaine((ConfigEtape(E.FORMATEUR, True, -1, Expiration.ESCALADER),))

    def test_seuil_superieur_a_la_note(self):
        with self.assertRaises(ReglagesInvalides):
            chaine_avec({E.FORMATEUR}, seuil_reussite=21.0)

    def test_note_sur_non_positive(self):
        with self.assertRaises(ReglagesInvalides):
            chaine_avec({E.FORMATEUR}, note_sur=0, seuil_reussite=0.0)

    def test_seuil_confiance_hors_bornes(self):
        for v in (-0.1, 1.1):
            with self.assertRaises(ReglagesInvalides):
                ConfigIA(seuil_confiance=v)

    def test_ia_valeurs_negatives(self):
        with self.assertRaises(ReglagesInvalides):
            ConfigIA(delai_minutes=-1)
        with self.assertRaises(ReglagesInvalides):
            ConfigIA(plafond_caracteres=0)

    def test_contexte_du_modele_superieur_a_la_reserve_de_reponse(self):
        self.assertEqual(ConfigIA().contexte_tokens, 4096)
        with self.assertRaisesRegex(ReglagesInvalides, "contexte"):
            ConfigIA(contexte_tokens=RESERVE_REPONSE_JETONS)
        self.assertEqual(ConfigIA(contexte_tokens=RESERVE_REPONSE_JETONS + 1).contexte_tokens, RESERVE_REPONSE_JETONS + 1)

    def test_publier_provisoire_formateur_refuse_par_defaut(self):
        c = Chaine(tuple(ConfigEtape(e, True, 1, Expiration.PUBLIER_PROVISOIRE if e == E.FORMATEUR
                                     else Expiration.PASSER) for e in Etape))
        with self.assertRaisesRegex(ReglagesInvalides, "provisoire"):
            ReglagesEvaluation(chaines={TypeExercice.PROJET: c})
        ReglagesEvaluation(chaines={TypeExercice.PROJET: c}, publication_provisoire=True)

    def test_grille_generique_invalide(self):
        with self.assertRaises(ReglagesInvalides):
            ReglagesEvaluation(grille_generique=(("A", 50),))
        with self.assertRaises(ReglagesInvalides):
            ReglagesEvaluation(grille_generique=(("A", 120), ("B", -20)))
        with self.assertRaises(ReglagesInvalides):
            ReglagesEvaluation(niveaux_generiques=("Seul",))

    def test_longueur_minimale(self):
        self.assertEqual(ReglagesEvaluation().longueur_min_caracteres, 200)
        self.assertEqual(ReglagesEvaluation(longueur_min_caracteres=0).longueur_min_caracteres, 0)
        with self.assertRaisesRegex(ReglagesInvalides, "longueur_min_caracteres"):
            ReglagesEvaluation(longueur_min_caracteres=-1)


    def test_resoumission_jusqu_au_debut_de_la_correction_par_defaut(self):
        self.assertEqual(ReglagesEvaluation().resoumission_jusqua, Resoumission.DEBUT_CORRECTION)
        self.assertEqual({r.value for r in Resoumission}, {"echeance", "debut_correction"})

    def test_limites_reglables(self):
        r = ReglagesEvaluation()
        self.assertEqual((r.ia.citation_min_caracteres, r.instantane_fichiers_max, r.instantane_delai_s,
                          r.instantane_budget_s, r.instantane_budget_tache_s), (8, 12, 10, 20, 60))
        for champ in ("instantane_fichiers_max", "instantane_delai_s", "instantane_budget_s",
                      "instantane_budget_tache_s"):
            with self.subTest(champ=champ), self.assertRaisesRegex(ReglagesInvalides, champ):
                ReglagesEvaluation(**{champ: 0})
        with self.assertRaisesRegex(ReglagesInvalides, "citation_min_caracteres"):
            ConfigIA(citation_min_caracteres=0)
        self.assertEqual(ConfigIA(citation_min_caracteres=1).citation_min_caracteres, 1)


class TestChainePour(unittest.TestCase):
    def setUp(self):
        self.r = ReglagesEvaluation()
        self.s_ex = chaine_avec({E.FORMATEUR}, nb_pairs=1)
        self.s_co = chaine_avec({E.FORMATEUR}, nb_pairs=2)
        self.yaml = chaine_avec({E.FORMATEUR}, nb_pairs=4)
        self.surcharges = (Surcharge("C1", None, self.s_co), Surcharge(None, "EX1", self.s_ex))

    def test_exercice_prime(self):
        c = self.r.chaine_pour(TypeExercice.PROJET, "C1", "EX1", self.surcharges, self.yaml)
        self.assertIs(c, self.s_ex)

    def test_cohorte_ensuite(self):
        c = self.r.chaine_pour(TypeExercice.PROJET, "C1", "EX2", self.surcharges, self.yaml)
        self.assertIs(c, self.s_co)

    def test_yaml_avant_le_type(self):
        r = ReglagesEvaluation(chaines={TypeExercice.PROJET: chaine_avec({E.FORMATEUR}, nb_pairs=9)})
        c = r.chaine_pour(TypeExercice.PROJET, "C2", "EX2", self.surcharges, self.yaml)
        self.assertIs(c, self.yaml)

    def test_type_configure_sans_yaml(self):
        configuree = chaine_avec({E.FORMATEUR}, nb_pairs=9)
        r = ReglagesEvaluation(chaines={TypeExercice.PROJET: configuree})
        self.assertIs(r.chaine_pour(TypeExercice.PROJET, "C2", "EX2", self.surcharges, None), configuree)

    def test_defauts_du_code_en_dernier(self):
        self.assertEqual(self.r.chaines, {})
        c = self.r.chaine_pour(TypeExercice.PROJET, "C2", "EX2", self.surcharges, None)
        self.assertIs(c, CHAINES_DEFAUT[TypeExercice.PROJET])

    def test_surcharge_sans_cible_refusee(self):
        with self.assertRaises(ReglagesInvalides):
            Surcharge(None, None, self.yaml)

    def test_garde_publication_provisoire_sur_chaine_retournee(self):
        dangereuse = Chaine(tuple(ConfigEtape(e, True, 1, Expiration.PUBLIER_PROVISOIRE if e == E.FORMATEUR
                                              else Expiration.PASSER) for e in Etape))
        with self.assertRaisesRegex(ReglagesInvalides, "provisoire"):
            self.r.chaine_pour(TypeExercice.PROJET, "C1", "EX1", (Surcharge(None, "EX1", dangereuse),), None)
        with self.assertRaisesRegex(ReglagesInvalides, "provisoire"):
            self.r.chaine_pour(TypeExercice.PROJET, "C1", "EX1", (), dangereuse)
        autorise = ReglagesEvaluation(publication_provisoire=True)
        self.assertIs(autorise.chaine_pour(TypeExercice.PROJET, "C1", "EX1", (), dangereuse), dangereuse)

    def test_chaine_effective_retombe_sur_la_chaine_du_type(self):
        dangereuse = Chaine(tuple(ConfigEtape(e, e == E.FORMATEUR, 1, Expiration.PUBLIER_PROVISOIRE) for e in Etape))
        self.assertEqual(self.r.chaine_effective(TypeExercice.PROJET, "C1", "EX1", self.surcharges, self.yaml),
                         (self.s_ex, False))
        self.assertEqual(self.r.chaine_effective(TypeExercice.PROJET, "C1", "EX1", (Surcharge(None, "EX1", dangereuse),),
                                                 None), (CHAINES_DEFAUT[TypeExercice.PROJET], True))
        configuree = chaine_avec({E.FORMATEUR}, nb_pairs=9)
        r = ReglagesEvaluation(chaines={TypeExercice.PROJET: configuree})
        self.assertEqual(r.chaine_effective(TypeExercice.PROJET, "C1", "EX1", (), dangereuse), (configuree, True))

    def test_surcharge_suppleant_seul_ne_remplace_aucune_chaine(self):
        seul = Surcharge("C1", None, None, "sup@x.ci")
        self.assertIs(self.r.chaine_pour(TypeExercice.PROJET, "C1", "EX2", (seul,), self.yaml), self.yaml)
        self.assertIs(self.r.chaine_pour(TypeExercice.CAPSTONE, "C1", "EX2", (seul,), None),
                      CHAINES_DEFAUT[TypeExercice.CAPSTONE])
        self.assertIs(self.r.chaine_pour(TypeExercice.PROJET, "C1", "EX1", (seul, *self.surcharges), None), self.s_ex)

    def test_surcharge_sans_chaine_ni_suppleant_refusee(self):
        with self.assertRaisesRegex(ReglagesInvalides, "chaîne ou un suppléant"):
            Surcharge("C1", None, None)

    def test_suppleant_d_une_surcharge_d_exercice_refuse(self):
        for cohorte in (None, "C1"):
            with self.subTest(cohorte=cohorte), self.assertRaisesRegex(ReglagesInvalides, "suppléant"):
                Surcharge(cohorte, "EX1", self.yaml, "sup@x.ci")


class TestChaineDict(unittest.TestCase):
    def test_aller_retour(self):
        c = CHAINES_DEFAUT[TypeExercice.LIVRABLE]
        self.assertEqual(Chaine.depuis_dict(c.vers_dict()), c)

    def test_etapes_absentes_inactives_et_options_par_defaut(self):
        c = Chaine.depuis_dict({"etapes": [{"etape": "formateur", "active": True, "delai_heures": 5,
                                            "expiration": "escalader"}]})
        self.assertTrue(c.active(E.FORMATEUR))
        self.assertFalse(c.active(E.IA))
        self.assertEqual((c.nb_pairs, c.anonymat, c.note_sur), (3, True, 20))
        self.assertEqual(c.config(E.FORMATEUR).delai_heures, 5)

    def test_options_lues(self):
        c = Chaine.depuis_dict({"etapes": [{"etape": "formateur", "active": True, "delai_heures": 1,
                                            "expiration": "passer"}], "nb_pairs": 2, "anonymat": False,
                                "note_masquee_avant_relectures": False, "note_sur": 100, "seuil_reussite": 50})
        self.assertEqual((c.nb_pairs, c.anonymat, c.note_masquee_avant_relectures, c.note_sur, c.seuil_reussite),
                         (2, False, False, 100, 50))

    def test_attente_maximale_des_relectures(self):
        c = CHAINES_DEFAUT[TypeExercice.LIVRABLE]
        self.assertEqual(c.attente_max_heures, c.config(E.PAIRS).delai_heures)  # un rappel par défaut
        lue = Chaine.depuis_dict({**c.vers_dict(), "attente_max_heures": 0})
        self.assertEqual(lue.attente_max_heures, 0)
        self.assertEqual(Chaine.depuis_dict(lue.vers_dict()), lue)
        with self.assertRaisesRegex(ReglagesInvalides, "attente_max_heures"):
            chaine_avec({E.FORMATEUR}, attente_max_heures=-1)

    def test_invalides(self):
        for donnees, message in [
            ("x", "dictionnaire"),
            ({}, "etapes"),
            ({"etapes": "x"}, "etapes"),
            ({"etapes": ["x"]}, r"etapes\[0\]"),
            ({"etapes": [{"etape": "zzz", "active": True, "delai_heures": 1, "expiration": "passer"}]}, "zzz"),
            ({"etapes": [{"etape": "ia", "active": True, "delai_heures": 1, "expiration": "zzz"}]}, "zzz"),
            ({"etapes": [{"etape": "ia", "active": True}]}, r"etapes\[0\]"),
            ({"etapes": [{"etape": "ia", "active": True, "delai_heures": 1, "expiration": "passer"}]}, "formateur"),
        ]:
            with self.subTest(donnees=donnees), self.assertRaisesRegex(ReglagesInvalides, message):
                Chaine.depuis_dict(donnees)


if __name__ == "__main__":
    unittest.main()
