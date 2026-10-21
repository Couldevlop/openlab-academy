import unittest
from datetime import timedelta

from openlab_academy.application.pairs import (
    AttribuerPairs, EnregistrerRelecture, RelectureRefusee, StatutRelecture)
from openlab_academy.domain.copie import Proposition, Source, Statut
from openlab_academy.domain.reglages_evaluation import CHAINES_DEFAUT, Etape, TypeExercice
from openlab_academy.tests.memoire_evaluation import DEBUT, Memoire

CHAINE = CHAINES_DEFAUT[TypeExercice.LIVRABLE]
NIVEAUX = {"pertinence": 2, "rigueur": 1}
COMMENTAIRES = {"pertinence": "Bien argumenté.", "rigueur": "Sources à préciser."}


def en_relecture(memoire, *apprenants, cohorte="COH1"):
    ids = []
    for a in apprenants:
        cid = memoire.rendre(a, CHAINE, DEBUT, cohorte=cohorte)
        memoire.changer_statut(cid, Statut.EN_RELECTURE, "pairs", DEBUT + timedelta(hours=72))
        ids.append(cid)
    return ids


class TestAttribuerPairs(unittest.TestCase):
    def setUp(self):
        self.m = Memoire()
        self.uc = AttribuerPairs(self.m, lambda: DEBUT)

    def attribuer(self, cid, n=3):
        return self.uc.executer(self.m.copie(cid), self.m.copies_rendues("EX1", "COH1"), n, 72)

    def test_premier_rendu_sans_rien_a_relire(self):
        (a,) = en_relecture(self.m, "a@x.ci")
        self.assertEqual(self.attribuer(a), ())
        self.assertEqual(self.m.rel, {})

    def test_deux_rendus_se_relisent_mutuellement(self):
        a, b = en_relecture(self.m, "a@x.ci", "b@x.ci")
        ids = self.attribuer(a, 1)
        self.assertEqual(self.attribuer(b, 1), ())  # déjà servi dans les deux sens
        self.assertEqual([(r.copie, r.relecteur) for r in self.m.rel.values()], [(b, "a@x.ci"), (a, "b@x.ci")])
        self.assertEqual(len(ids), 1)
        self.assertEqual(self.m.rel[ids[0]].echeance, DEBUT + timedelta(hours=72))

    def test_jamais_la_sienne_ni_deux_fois_la_meme(self):
        a, b, c = en_relecture(self.m, "a@x.ci", "b@x.ci", "c@x.ci")
        for cid in (a, b, c):
            self.attribuer(cid)
        self.attribuer(c)  # un second passage n'attribue rien de plus
        paires = [(r.relecteur, self.m.copie(r.copie).apprenant) for r in self.m.rel.values()]
        self.assertTrue(all(relecteur != auteur for relecteur, auteur in paires))
        self.assertEqual(len(paires), len(set(paires)))
        self.assertEqual(len(paires), 6)  # cohorte de 3 : chacun relit les 2 autres

    def test_les_moins_relues_d_abord(self):
        a, b, c = en_relecture(self.m, "a@x.ci", "b@x.ci", "c@x.ci")
        self.m.attribuer(a, "z@x.ci", DEBUT)
        (d,) = en_relecture(self.m, "d@x.ci")
        ids = self.attribuer(d, 2)
        self.assertEqual([self.m.rel[i].copie for i in ids], [b, c])

    def test_copies_en_retard_d_abord_les_plus_anciennes(self):
        a, b, c = en_relecture(self.m, "a@x.ci", "b@x.ci", "c@x.ci")
        for cid, retard in ((b, 48), (c, 24)):
            self.m.changer_statut(cid, Statut.EN_RELECTURE, "pairs", DEBUT - timedelta(hours=retard))
        (d,) = en_relecture(self.m, "d@x.ci")
        ids = self.attribuer(d, 2)
        self.assertEqual([self.m.rel[i].copie for i in ids], [b, c])

    def test_copie_assez_relue_ou_hors_relecture_non_proposee(self):
        a, b = en_relecture(self.m, "a@x.ci", "b@x.ci")
        self.m.attribuer(a, "z@x.ci", DEBUT)
        self.m.changer_statut(b, Statut.A_CORRIGER, "formateur", None)
        (c,) = en_relecture(self.m, "c@x.ci")
        self.assertEqual(self.attribuer(c, 1), ())

    def test_relecture_retiree_jamais_rendue_au_meme_relecteur(self):
        a, b = en_relecture(self.m, "a@x.ci", "b@x.ci")
        rid = self.m.attribuer(a, "b@x.ci", DEBUT)
        self.m.changer_statut_relecture(rid, StatutRelecture.REATTRIBUEE)
        self.assertEqual(self.attribuer(b, 1), ())

    def test_paire_creee_en_concurrence_ignoree(self):
        a, b, c = en_relecture(self.m, "a@x.ci", "b@x.ci", "c@x.ci")
        self.m.paires_concurrentes = {(b, "a@x.ci"), (a, "b@x.ci")}
        self.assertEqual(self.attribuer(a, 1), (self.m.relectures_par("a@x.ci")[0].id,))  # c plutôt que b
        self.assertEqual(self.m.relectures_par("a@x.ci")[0].copie, c)
        self.assertEqual([r.relecteur for r in self.m.relectures_de(a)], ["c@x.ci"])
        self.assertIsNone(self.uc.reattribuer(self.m.copie(a), self.m.copies_rendues("EX1", "COH1"), 72))

    def test_anonymat_des_donnees_renvoyees(self):
        a, b = en_relecture(self.m, "a@x.ci", "b@x.ci")
        ids = self.attribuer(b, 1)
        self.assertFalse(any("@" in i for i in ids))

    def test_reattribuer_au_pair_le_moins_charge_jamais_deja_sollicite(self):
        a, b, c, d = en_relecture(self.m, "a@x.ci", "b@x.ci", "c@x.ci", "d@x.ci")
        self.m.attribuer(a, "b@x.ci", DEBUT)
        self.m.attribuer(b, "c@x.ci", DEBUT)
        nouveau = self.uc.reattribuer(self.m.copie(a), self.m.copies_rendues("EX1", "COH1"), 72)
        self.assertEqual(nouveau, "d@x.ci")
        self.assertEqual(self.m.relectures_par("d@x.ci")[0].copie, a)
        self.assertIsNone(self.uc.reattribuer(self.m.copie(a), [self.m.copie(a)], 72))


class AvanceurMemoire:
    def __init__(self, requis=1):
        self.requis, self.appels = requis, []

    def pairs_requis(self, copie):
        return self.requis

    def executer(self, copie_id, terminee=None):
        self.appels.append((copie_id, terminee))


class TestEnregistrerRelecture(unittest.TestCase):
    def setUp(self):
        self.m = Memoire()
        self.a, self.b = en_relecture(self.m, "a@x.ci", "b@x.ci")
        self.rid = self.m.attribuer(self.a, "b@x.ci", DEBUT + timedelta(hours=72))
        self.avanceur = AvanceurMemoire(requis=2)
        self.journal = []
        self.uc = EnregistrerRelecture(self.m, self.m, self.avanceur, lambda *args: self.journal.append(args))

    def test_relecture_enregistree(self):
        self.uc.executer("b@x.ci", self.rid, NIVEAUX, COMMENTAIRES)
        self.assertEqual(self.m.propositions(self.a),
                         [Proposition(Source.PAIR, "b@x.ci", NIVEAUX, COMMENTAIRES)])
        self.assertEqual(self.m.rel[self.rid].statut, StatutRelecture.FAITE)
        self.assertEqual(self.journal[0][:3], (self.a, "b@x.ci", "relecture"))
        self.assertEqual(self.avanceur.appels, [])  # 1 relecture sur 2

    def test_n_relectures_faites_la_copie_avance(self):
        autre = self.m.attribuer(self.a, "c@x.ci", DEBUT)
        self.uc.executer("b@x.ci", self.rid, NIVEAUX, COMMENTAIRES)
        self.uc.executer("c@x.ci", autre, NIVEAUX, COMMENTAIRES)
        self.assertEqual(self.avanceur.appels, [(self.a, Etape.PAIRS)])

    def test_relectures_faites_comptees_sous_verrou(self):
        autre = self.m.attribuer(self.a, "c@x.ci", DEBUT)
        self.m.relectures = lambda exercice, cohorte: []  # instantané périmé : ignoré
        self.uc.executer("b@x.ci", self.rid, NIVEAUX, COMMENTAIRES)
        self.uc.executer("c@x.ci", autre, NIVEAUX, COMMENTAIRES)
        self.assertEqual(self.avanceur.appels, [(self.a, Etape.PAIRS)])

    def test_copie_sortie_des_pairs_n_avance_plus(self):
        self.avanceur.requis = 1
        self.m.changer_statut(self.a, Statut.A_CORRIGER, "formateur", None)
        self.uc.executer("b@x.ci", self.rid, NIVEAUX, COMMENTAIRES)
        self.assertEqual(self.avanceur.appels, [])

    def test_relecture_non_attribuee_refusee(self):
        for relecteur, rid in (("c@x.ci", self.rid), ("b@x.ci", "R404")):
            with self.assertRaisesRegex(RelectureRefusee, "non attribuée"):
                self.uc.executer(relecteur, rid, NIVEAUX, COMMENTAIRES)
        self.assertEqual(self.m.propositions(self.a), [])

    def test_double_relecture_refusee(self):
        self.uc.executer("b@x.ci", self.rid, NIVEAUX, COMMENTAIRES)
        with self.assertRaisesRegex(RelectureRefusee, "plus à faire"):
            self.uc.executer("b@x.ci", self.rid, NIVEAUX, COMMENTAIRES)
        self.assertEqual(len(self.m.propositions(self.a)), 1)
        self.assertEqual(self.m.verrous, [self.a, self.a])  # la copie est verrouillée avant la relecture

    def test_commentaire_obligatoire_par_critere(self):
        with self.assertRaisesRegex(RelectureRefusee, "commentaire"):
            self.uc.executer("b@x.ci", self.rid, NIVEAUX, {"pertinence": "ok", "rigueur": "  "})
        self.assertEqual(self.m.rel[self.rid].statut, StatutRelecture.A_FAIRE)

    def test_niveaux_incomplets_ou_hors_grille_refuses(self):
        for niveaux in ({"pertinence": 2}, {"pertinence": 2, "rigueur": 9}, {**NIVEAUX, "intrus": 1}):
            with self.assertRaisesRegex(RelectureRefusee, "niveau"):
                self.uc.executer("b@x.ci", self.rid, niveaux, {**COMMENTAIRES, "intrus": "x"})
        self.assertEqual(self.m.propositions(self.a), [])
