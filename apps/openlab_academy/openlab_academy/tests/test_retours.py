import unittest
from datetime import timedelta

from openlab_academy.application.corriger import AccesRefuse, CorrectionRefusee
from openlab_academy.application.pairs import StatutRelecture
from openlab_academy.application.retours import (
    EN_COURS, MASQUEE, PROVISOIRE, REMPLACEE, AutoEvaluer, ConsulterRelectures, ConsulterRetour)
from openlab_academy.application.soumettre_copie import Contenu
from openlab_academy.domain.copie import Proposition, Source, Statut
from openlab_academy.domain.reglages_evaluation import Etape, TypeExercice
from openlab_academy.tests.memoire_evaluation import DEBUT, Memoire
from openlab_academy.tests.test_chaine import chaine

A, B, C = "a@x.ci", "b@x.ci", "c@x.ci"
MOYENS = {"pertinence": 1, "rigueur": 1}
BONS = {"pertinence": 2, "rigueur": 2}


class Cas(unittest.TestCase):
    def monter(self, masquee=True):
        self.chaine_ = chaine(Etape.PAIRS, Etape.FORMATEUR, note_masquee_avant_relectures=masquee)
        self.m = Memoire(TypeExercice.LIVRABLE, self.chaine_)
        self.retour = ConsulterRetour(self.m, self.m, lambda copie: self.chaine_)
        self.a = self.m.rendre(A, self.chaine_, DEBUT)
        self.b = self.m.rendre(B, self.chaine_, DEBUT)

    def publiee(self, cid, note=10.0, reussite=True):
        self.m.changer_statut(cid, Statut.PUBLIEE, "", None)
        self.m.resultats[cid] = (note, 20, reussite)


class TestConsulterRetour(Cas):
    def test_copie_d_autrui_refusee(self):
        self.monter()
        with self.assertRaises(AccesRefuse):
            self.retour.executer(B, self.a)

    def test_en_cours_sans_note_ni_proposition(self):
        self.monter()
        self.m.ajouter_proposition(self.a, Proposition(Source.IA, "ia", BONS, {"pertinence": "secret"}))
        retour = self.retour.executer(A, self.a)
        self.assertEqual((retour["statut"], retour["note"], retour["criteres"], retour["message"], retour["titre"]),
                         ("rendue", None, [], EN_COURS, "Mise en situation 01"))
        self.assertNotIn("secret", repr(retour))

    def test_note_masquee_tant_que_les_relectures_ne_sont_pas_faites(self):
        self.monter()
        self.publiee(self.a)
        self.m.attribuer(self.b, A, DEBUT + timedelta(hours=1))
        retour = self.retour.executer(A, self.a)
        self.assertEqual((retour["masquee"], retour["note"], retour["criteres"], retour["message"]),
                         (True, None, [], MASQUEE))
        self.m.dispenser(self.a)
        self.assertEqual(self.retour.executer(A, self.a)["note"], 10.0)

    def test_relectures_faites_ou_gating_inactif(self):
        self.monter()
        self.publiee(self.a)
        rid = self.m.attribuer(self.b, A, DEBUT)
        self.m.changer_statut_relecture(rid, StatutRelecture.FAITE)
        self.assertFalse(self.retour.executer(A, self.a)["masquee"])
        self.monter(masquee=False)
        self.publiee(self.a)
        self.m.attribuer(self.b, A, DEBUT)
        self.assertEqual(self.retour.executer(A, self.a)["note"], 10.0)

    def test_retour_publie_par_critere(self):
        self.monter()
        self.publiee(self.a, 12.5, True)
        for p in (Proposition(Source.AUTO_EVALUATION, A, MOYENS),
                  Proposition(Source.IA, "ia", BONS, {"pertinence": "justification IA"}),
                  Proposition(Source.PAIR, B, BONS, {"pertinence": "Très clair", "rigueur": "Précis"}),
                  Proposition(Source.FORMATEUR, "form@x.ci", BONS, {"pertinence": "Bien", "general": "Bravo"})):
            self.m.ajouter_proposition(self.a, p)
        retour = self.retour.executer(A, self.a)
        self.assertEqual((retour["note"], retour["note_sur"], retour["reussite"], retour["provisoire"]),
                         (12.5, 20, True, False))
        premier = retour["criteres"][0]
        self.assertEqual(premier, {"code": "pertinence", "libelle": "Pertinence", "poids": 60, "niveau": 2,
                                   "niveau_libelle": "Bon", "niveaux": ["Faible", "Moyen", "Bon"],
                                   "auto_evaluation": 1, "commentaire": "Bien", "pairs": ["Très clair"]})
        self.assertEqual(retour["titre"], "Mise en situation 01")
        self.assertEqual(retour["commentaire_general"], "Bravo")
        self.assertNotIn(B, repr(retour))  # pairs anonymes

    def test_version_remplacee_sans_note(self):
        self.monter()
        self.m.changer_statut(self.a, Statut.PROVISOIRE, "formateur", None)
        self.m.ajouter_proposition(self.a, Proposition(Source.PAIR, B, MOYENS, {"pertinence": "ok", "rigueur": "ok"}))
        self.m.changer_statut(self.a, Statut.REMPLACEE, "", None)
        retour = self.retour.executer(A, self.a)
        self.assertEqual((retour["statut"], retour["provisoire"], retour["note"], retour["criteres"], retour["message"]),
                         ("remplacee", False, None, [], REMPLACEE))

    def test_note_provisoire_affichee_provisoire(self):
        self.monter()
        self.m.changer_statut(self.a, Statut.PROVISOIRE, "formateur", None)
        self.m.ajouter_proposition(self.a, Proposition(Source.IA, "ia", {"pertinence": 0, "rigueur": 0},
                                                       {"pertinence": "justification IA"}))
        retour = self.retour.executer(A, self.a)
        self.assertEqual((retour["provisoire"], retour["note"], retour["message"]), (True, None, PROVISOIRE))
        self.assertNotIn("justification IA", repr(retour))
        self.m.ajouter_proposition(self.a, Proposition(Source.PAIR, B, MOYENS, {"pertinence": "ok", "rigueur": "ok"}))
        retour = self.retour.executer(A, self.a)
        self.assertEqual((retour["provisoire"], retour["note"], retour["reussite"]), (True, 10.0, True))
        self.assertEqual(retour["criteres"][0]["niveau"], 1)
        self.assertEqual(retour["criteres"][0]["commentaire"], "")


class TestAutoEvaluer(Cas):
    def setUp(self):
        self.monter()
        self.auto = AutoEvaluer(self.m)
        self.m.inscrits.add((C, "EX1"))

    def test_consulter_puis_enregistrer(self):
        vue = self.auto.consulter(C, "EX1")
        self.assertEqual((vue["niveaux"], vue["modifiable"]), (None, True))
        self.assertEqual(vue["grille"]["criteres"][1]["code"], "rigueur")
        self.auto.enregistrer(C, "EX1", MOYENS)
        self.assertEqual(self.auto.consulter(C, "EX1")["niveaux"], MOYENS)

    def test_non_inscrit_ou_exercice_sans_grille(self):
        for apprenant, exercice in ((B, "EX1"), (C, "EX2")):
            with self.subTest(exercice=exercice), self.assertRaises(AccesRefuse):
                self.auto.consulter(apprenant, exercice)
            with self.assertRaises(AccesRefuse):
                self.auto.enregistrer(apprenant, exercice, MOYENS)

    def test_niveaux_invalides(self):
        with self.assertRaises(CorrectionRefusee):
            self.auto.enregistrer(C, "EX1", {"pertinence": 9, "rigueur": 0})

    def test_close_apres_le_rendu_rouverte_apres_un_renvoi(self):
        cid = self.m.rendre(C, self.chaine_, DEBUT)
        self.assertFalse(self.auto.consulter(C, "EX1")["modifiable"])
        with self.assertRaisesRegex(CorrectionRefusee, "déjà rendue"):
            self.auto.enregistrer(C, "EX1", MOYENS)
        self.m.changer_statut(cid, Statut.RENVOYEE, "", None)
        self.auto.enregistrer(C, "EX1", MOYENS)


class TestConsulterRelectures(Cas):
    def setUp(self):
        self.monter()
        self.m.contenus[self.b] = Contenu("Copie de B", "https://github.com/bkone/depot", "abc", "s", "SUB-B")
        self.r1 = self.m.attribuer(self.b, A, DEBUT + timedelta(hours=3))
        c = self.m.rendre(C, self.chaine_, DEBUT)
        self.r2 = self.m.attribuer(c, A, DEBUT + timedelta(hours=4))
        self.m.changer_statut_relecture(self.r2, StatutRelecture.FAITE)
        annulee = self.m.attribuer(self.a, C, DEBUT)
        self.m.changer_statut_relecture(annulee, StatutRelecture.ANNULEE)
        self.annulee = annulee
        self.vue = ConsulterRelectures(self.m, self.m)

    def test_mes_relectures_sans_auteur(self):
        liste = self.vue.mes_relectures(A)
        self.assertEqual([(r["relecture"], r["statut"], r["rang"], r["total"]) for r in liste],
                         [(self.r1, "à_faire", 1, 2), (self.r2, "faite", 2, 2)])
        self.assertEqual(liste[0]["exercice"], "EX1")
        self.assertNotIn(B, repr(liste))
        self.assertEqual(self.vue.mes_relectures(C), [])  # relecture annulée : retirée

    def test_relecture_sans_champ_identifiant_l_auteur(self):
        vue = self.vue.relecture(A, self.r1)
        self.assertEqual(set(vue), {"relecture", "exercice", "titre", "consigne", "contenu", "grille", "statut",
                                    "echeance", "rang", "total", "anonymat_garanti"})
        self.assertEqual(vue["titre"], "Mise en situation 01")
        self.assertEqual((vue["contenu"], vue["consigne"], vue["anonymat_garanti"]),
                         ("Copie de B", "Analysez le cas.", False))
        self.assertNotIn(B, repr(vue))
        self.assertNotIn(self.b, repr(vue))
        self.assertNotIn("bkone", repr(vue))

    def test_relecture_d_autrui_inconnue_ou_retiree_refusee(self):
        for relecteur, rid in ((B, self.r1), (A, "inconnue"), (C, self.annulee)):
            with self.subTest(rid=rid), self.assertRaises(AccesRefuse):
                self.vue.relecture(relecteur, rid)

    def test_copie_texte_anonymat_garanti(self):
        self.assertTrue(self.vue.relecture(A, self.r2)["anonymat_garanti"])
