import unittest
from datetime import datetime, timedelta

from openlab_academy.domain.copie import (
    Copie, Proposition, Source, Statut, TransitionInterdite, ecarts, etape_suivante, lots, mediane, nb_pairs_possible,
    refus_de_resoumission,
)
from openlab_academy.domain.reglages_evaluation import (
    Chaine, ConfigEtape, Etape, Expiration, Resoumission, TypeExercice)

MAINTENANT = datetime(2026, 10, 21, 12, 0)


def copie(statut=Statut.RENDUE):
    return Copie("C1", "a@x.ci", "EX1", "COH1", TypeExercice.PROJET, 1, statut)


def prop(niveaux, source=Source.PAIR, **kw):
    return Proposition(source, "auteur", niveaux, **kw)


def chaine(actives):
    return Chaine(tuple(ConfigEtape(e, e in actives, 1, Expiration.PASSER) for e in Etape))


class TestTransitions(unittest.TestCase):
    def test_legales(self):
        legales = {
            Statut.RENDUE: {Statut.CONTROLEE, Statut.RENVOYEE, Statut.PRE_CORRIGEE, Statut.EN_RELECTURE, Statut.A_CORRIGER,
                            Statut.REMPLACEE},
            Statut.RENVOYEE: set(),
            Statut.CONTROLEE: {Statut.PRE_CORRIGEE, Statut.EN_RELECTURE, Statut.A_CORRIGER, Statut.REMPLACEE},
            Statut.PRE_CORRIGEE: {Statut.EN_RELECTURE, Statut.A_CORRIGER, Statut.REMPLACEE},
            Statut.EN_RELECTURE: {Statut.A_CORRIGER, Statut.REMPLACEE},
            Statut.A_CORRIGER: {Statut.PROVISOIRE, Statut.PUBLIEE, Statut.REMPLACEE},
            Statut.PROVISOIRE: {Statut.PUBLIEE, Statut.REMPLACEE},
            Statut.PUBLIEE: set(),
            Statut.REMPLACEE: set(),  # terminale, en lecture seule
        }
        for depart, cibles in legales.items():
            for cible in Statut:
                c = copie(depart)
                if cible in cibles:
                    self.assertEqual(c.passer_a(cible).statut, cible)
                else:
                    with self.assertRaises(TransitionInterdite):
                        c.passer_a(cible)

    def test_publiee_vers_rendue_interdit(self):
        with self.assertRaisesRegex(TransitionInterdite, "publiee"):
            copie(Statut.PUBLIEE).passer_a(Statut.RENDUE)

    def test_immuable(self):
        c = copie()
        n = c.passer_a(Statut.CONTROLEE)
        self.assertEqual(c.statut, Statut.RENDUE)
        self.assertEqual(n.id, c.id)


class TestResoumission(unittest.TestCase):
    def refus(self, statut=Statut.RENDUE, props=(), regle=Resoumission.DEBUT_CORRECTION, echeance=None):
        return refus_de_resoumission(copie(statut), list(props), regle, MAINTENANT, echeance)

    def test_publiee_definitive_quelle_que_soit_la_regle(self):
        for regle in Resoumission:
            self.assertEqual(self.refus(Statut.PUBLIEE, regle=regle), "rendu après publication ignoré")

    def test_jusqu_au_debut_de_la_correction(self):
        for statut in (Statut.RENDUE, Statut.EN_RELECTURE, Statut.A_CORRIGER, Statut.RENVOYEE):
            self.assertIsNone(self.refus(statut, props=[prop({"a": 1}), prop({"a": 1}, Source.IA)]))
        debut = "rendu après le début de la correction ignoré"
        for source in (Source.FORMATEUR, Source.JURY):  # premier geste humain de correction
            self.assertEqual(self.refus(Statut.A_CORRIGER, props=[prop({"a": 1}, source)]), debut)
        self.assertEqual(self.refus(Statut.PROVISOIRE), debut)
        self.assertIsNone(self.refus(Statut.A_CORRIGER, echeance=MAINTENANT - timedelta(days=1)))  # échéance ignorée

    def test_jusqu_a_l_echeance_de_l_exercice(self):
        regle = Resoumission.ECHEANCE
        corrigee = [prop({"a": 1}, Source.FORMATEUR)]
        self.assertIsNone(self.refus(Statut.PROVISOIRE, corrigee, regle, MAINTENANT))  # échéance comprise
        self.assertIsNone(self.refus(Statut.A_CORRIGER, corrigee, regle, None))  # exercice sans échéance
        self.assertEqual(self.refus(Statut.RENDUE, (), regle, MAINTENANT - timedelta(minutes=1)),
                         "rendu après l'échéance ignoré")
        self.assertIsNone(self.refus(Statut.RENVOYEE, (), regle, MAINTENANT - timedelta(minutes=1)))


class TestEtapeSuivante(unittest.TestCase):
    def test_depart_saute_inactives(self):
        ch = chaine({Etape.CONTROLES, Etape.FORMATEUR})
        self.assertEqual(etape_suivante(ch, None), Etape.CONTROLES)
        self.assertEqual(etape_suivante(ch, Etape.CONTROLES), Etape.FORMATEUR)

    def test_saute_ia_inactive(self):
        ch = chaine({Etape.CONTROLES, Etape.PAIRS, Etape.FORMATEUR})
        self.assertEqual(etape_suivante(ch, Etape.CONTROLES), Etape.PAIRS)

    def test_apres_formateur(self):
        with self.assertRaises(ValueError):
            etape_suivante(chaine({Etape.FORMATEUR}), Etape.FORMATEUR)


class TestMedianeEcarts(unittest.TestCase):
    def test_mediane_impaire(self):
        ps = [prop({"a": 1}), prop({"a": 3}), prop({"a": 2})]
        self.assertEqual(mediane(ps), {"a": 2})

    def test_mediane_paire_basse(self):
        self.assertEqual(mediane([prop({"a": 1}), prop({"a": 3})]), {"a": 1})

    def test_mediane_plusieurs_criteres_et_absents(self):
        ps = [prop({"a": 1, "b": 0}), prop({"a": 2}), prop({"a": 3, "b": 2})]
        self.assertEqual(mediane(ps), {"a": 2, "b": 0})

    def test_mediane_vide(self):
        self.assertEqual(mediane([]), {})

    def test_ecart_ia_formateur(self):
        ps = [prop({"a": 0, "b": 1}, Source.IA), prop({"a": 2, "b": 1}, Source.FORMATEUR)]
        self.assertEqual(ecarts(ps), {"a"})

    def test_pas_d_ecart_dans_le_seuil(self):
        ps = [prop({"a": 1}), prop({"a": 2})]
        self.assertEqual(ecarts(ps), set())
        self.assertEqual(ecarts(ps, seuil=0), {"a"})

    def test_ecart_ignore_critere_non_partage(self):
        self.assertEqual(ecarts([prop({"a": 0}), prop({"b": 3})]), set())


class TestPairsEtLots(unittest.TestCase):
    def test_nb_pairs_possible(self):
        self.assertEqual(nb_pairs_possible(3, 1), 0)
        self.assertEqual(nb_pairs_possible(3, 2), 1)
        self.assertEqual(nb_pairs_possible(3, 10), 3)
        self.assertEqual(nb_pairs_possible(3, 0), 0)

    def test_lots(self):
        ia = {
            "c1": prop({"a": 2, "b": 1}, Source.IA, confiance=0.9),
            "c2": prop({"b": 1, "a": 2}, Source.IA, confiance=0.85),
            "c3": prop({"a": 2, "b": 1}, Source.IA, confiance=0.8),
            "c4": prop({"a": 2, "b": 1}, Source.IA, confiance=0.5),
            "c5": prop({"a": 0, "b": 0}, Source.IA, confiance=0.95),
            "c6": prop({"a": 2, "b": 1}, Source.IA),
        }
        res = lots(ia, 0.8)
        self.assertEqual(res, [["c1", "c2", "c3"]])

    def test_defauts_non_partages(self):
        a, b = prop({"a": 1}), prop({"a": 1})
        a.commentaires["a"] = "x"
        self.assertEqual(b.commentaires, {})


if __name__ == "__main__":
    unittest.main()
