import unittest
from dataclasses import replace
from datetime import timedelta

from openlab_academy.application.chaine import (
    SYSTEME, Etat, FaireAvancer, TraiterEcheances, chaine_de, suppleant_de)
from openlab_academy.application.pairs import EnregistrerRelecture, StatutRelecture
from openlab_academy.domain.copie import Copie, Statut
from openlab_academy.domain.reglages_evaluation import (
    CHAINES_DEFAUT, Chaine, ConfigEtape, Etape, Expiration, ReglagesEvaluation, Surcharge, TypeExercice)
from openlab_academy.tests.memoire_evaluation import DEBUT, Memoire, SourceMemoire

LIVRABLE = CHAINES_DEFAUT[TypeExercice.LIVRABLE]
NIVEAUX = {"pertinence": 2, "rigueur": 1}
COMMENTAIRES = {"pertinence": "Clair.", "rigueur": "Précis."}


def chaine(*actives, **options) -> Chaine:
    """Chaîne de test : délais d'une heure, expirations par défaut du code."""
    expirations = {Etape.PAIRS: Expiration.REATTRIBUER, Etape.JURY: Expiration.ESCALADER,
                   Etape.FORMATEUR: Expiration.ESCALADER}
    return Chaine(tuple(ConfigEtape(e, e in actives, 1, expirations.get(e, Expiration.PASSER)) for e in Etape),
                  **options)


class Cas(unittest.TestCase):
    def monter(self, type_=TypeExercice.LIVRABLE, yaml=None, taille=4, reglages=None, surcharges=()):
        self.m = Memoire(type_, yaml, taille)
        self.source = SourceMemoire(reglages, surcharges)
        self.t = DEBUT
        self.file, self.journal = [], []
        horloge = lambda: self.t  # noqa: E731
        journal = lambda *args: self.journal.append(args)  # noqa: E731
        self.avancer = FaireAvancer(self.m, self.m, self.source, horloge, lambda *a: self.file.append(a), journal)
        self.echeances = TraiterEcheances(self.m, self.m, self.source, self.avancer, horloge, journal)
        self.relire = EnregistrerRelecture(self.m, self.m, self.avancer, journal)

    def rendre(self, apprenant, cohorte="COH1"):
        cid = self.m.rendre(apprenant, chaine_de(_copie_type(self.m, cohorte), self.m, self.source), self.t,
                            cohorte=cohorte)
        self.avancer.demarrer(cid)
        return cid

    def etape(self, cid):
        return self.m.etat(cid).etape, self.m.copie(cid).statut

    def actions(self, acteur=SYSTEME):
        return [j[2] for j in self.journal if j[1] == acteur]

    def avancer_horloge(self, heures):
        self.t += timedelta(hours=heures)
        self.echeances.executer()


def _copie_type(memoire, cohorte):
    return Copie("", "", "EX1", cohorte, memoire.type_, 1, Statut.RENDUE)


class TestFaireAvancer(Cas):
    def test_chaine_complete_controles_ia_pairs_formateur(self):
        self.monter()
        a = self.rendre("a@x.ci")
        # l'auto-évaluation précède le rendu : la copie part aussitôt aux contrôles
        self.assertEqual(self.etape(a), ("controles", Statut.RENDUE))
        self.assertEqual(self.file, [("controler", a)])
        self.assertEqual(self.m.etat(a).echeance, DEBUT + timedelta(hours=1))
        self.avancer.executer(a, Etape.CONTROLES)
        # pré-correction lancée, les pairs relisent pendant ce temps
        self.assertEqual(self.file[-1], ("pre_corriger", a))
        self.assertEqual(self.etape(a), ("pairs", Statut.EN_RELECTURE))
        self.assertEqual(self.m.etat(a).echeance, DEBUT + timedelta(hours=72))
        self.avancer.executer(a, Etape.IA)  # la pré-correction finit pendant les relectures : rien ne bouge
        self.assertEqual(self.etape(a), ("pairs", Statut.EN_RELECTURE))
        autres = [self.rendre(e) for e in ("b@x.ci", "c@x.ci", "d@x.ci")]
        for cid in autres:
            self.avancer.executer(cid, Etape.CONTROLES)
        for relecture in self.m.relectures_de(a):
            self.relire.executer(relecture.relecteur, relecture.id, NIVEAUX, COMMENTAIRES)
        self.assertEqual(len(self.m.propositions(a)), 3)
        self.assertEqual(self.etape(a), ("formateur", Statut.A_CORRIGER))
        self.assertEqual(self.m.etat(a).echeance, DEBUT + timedelta(hours=72))
        self.assertEqual(len(self.m.relectures_par("a@x.ci")), 3)
        self.assertIn("étape suivante", self.actions())

    def test_ia_non_disponible_la_copie_passe_aux_pairs(self):
        self.monter(yaml=chaine(Etape.IA, Etape.PAIRS, Etape.FORMATEUR))
        a = self.rendre("a@x.ci")
        self.assertEqual(self.file, [("pre_corriger", a)])
        self.avancer.executer(a, Etape.IA)  # « non disponible »
        self.assertEqual(self.etape(a), ("pairs", Statut.EN_RELECTURE))
        self.assertEqual(self.m.propositions(a), [])

    def test_ia_seule_attend_puis_passe_a_l_echeance(self):
        self.monter(yaml=chaine(Etape.IA, Etape.FORMATEUR))
        a = self.rendre("a@x.ci")
        self.assertEqual(self.etape(a), ("ia", Statut.RENDUE))
        self.avancer_horloge(1)
        self.assertEqual(self.etape(a), ("formateur", Statut.A_CORRIGER))
        self.assertIn("passer", self.actions())

    def test_controles_puis_formateur(self):
        self.monter(type_=TypeExercice.MISE_EN_SITUATION, yaml=chaine(Etape.CONTROLES, Etape.JURY, Etape.FORMATEUR))
        a = self.rendre("a@x.ci")
        self.avancer.executer(a)
        self.assertEqual(self.etape(a), ("jury", Statut.A_CORRIGER))
        self.avancer.executer(a)
        self.assertEqual(self.etape(a), ("formateur", Statut.A_CORRIGER))

    def test_controles_puis_ia_sans_pairs(self):
        self.monter(type_=TypeExercice.MISE_EN_SITUATION)
        a = self.rendre("a@x.ci")
        self.avancer.executer(a, Etape.CONTROLES)
        self.assertEqual(self.etape(a), ("ia", Statut.CONTROLEE))
        self.avancer.executer(a, Etape.IA)
        self.assertEqual(self.etape(a), ("formateur", Statut.A_CORRIGER))

    def test_cohorte_de_2_un_pair(self):
        self.monter(taille=2)
        a, b = self.rendre("a@x.ci"), self.rendre("b@x.ci")
        for cid in (a, b):
            self.avancer.executer(cid, Etape.CONTROLES)
        self.assertEqual([(r.copie, r.relecteur) for r in self.m.rel.values()], [(a, "b@x.ci"), (b, "a@x.ci")])
        (r,) = self.m.relectures_de(a)
        self.relire.executer("b@x.ci", r.id, NIVEAUX, COMMENTAIRES)
        self.assertEqual(self.etape(a), ("formateur", Statut.A_CORRIGER))
        self.assertEqual(self.etape(b), ("pairs", Statut.EN_RELECTURE))

    def test_cohorte_de_1_pairs_sautes(self):
        self.monter(taille=1)
        a = self.rendre("a@x.ci")
        self.avancer.executer(a, Etape.CONTROLES)
        self.assertEqual(self.etape(a), ("ia", Statut.CONTROLEE))  # pas de pairs : la pré-correction est attendue
        self.avancer.executer(a, Etape.IA)
        self.assertEqual(self.etape(a), ("formateur", Statut.A_CORRIGER))
        self.assertIn("pairs sautés", self.actions())
        self.assertEqual(self.m.rel, {})

    def test_sans_cohorte_pairs_sautes(self):
        self.monter(yaml=chaine(Etape.PAIRS, Etape.FORMATEUR))
        a = self.rendre("a@x.ci", cohorte="")
        self.assertEqual(self.etape(a), ("formateur", Statut.A_CORRIGER))

    def test_premiere_etape_pairs(self):
        self.monter(yaml=chaine(Etape.PAIRS, Etape.FORMATEUR))
        a = self.rendre("a@x.ci")
        self.assertEqual(self.etape(a), ("pairs", Statut.EN_RELECTURE))

    def test_quitter_les_pairs_annule_les_relectures_en_attente(self):
        self.monter(taille=2)
        a, b = self.rendre("a@x.ci"), self.rendre("b@x.ci")
        for cid in (a, b):
            self.avancer.executer(cid, Etape.CONTROLES)
        self.avancer.executer(a, Etape.PAIRS)
        self.assertEqual([r.statut for r in self.m.relectures_de(a)], [StatutRelecture.ANNULEE])

    def test_copie_terminee_ou_signal_perime_ignores(self):
        self.monter()
        a = self.rendre("a@x.ci")
        self.avancer.executer(a, Etape.IA)  # pas l'étape courante
        self.assertEqual(self.etape(a), ("controles", Statut.RENDUE))
        for statut in (Statut.RENVOYEE, Statut.PROVISOIRE, Statut.PUBLIEE):
            self.m.copies[a] = replace(self.m.copies[a], statut=statut)
            self.avancer.executer(a)
            self.assertEqual(self.m.etat(a).etape, "controles")
        self.m.copies[a] = replace(self.m.copies[a], statut=Statut.A_CORRIGER)
        self.m.etats[a] = Etat("formateur", None)
        self.avancer.executer(a)  # le formateur clôt la chaîne
        self.assertEqual(self.m.etat(a).etape, "formateur")

    def test_chaine_de_l_exercice_disparu_ou_surcharge_dangereuse(self):
        dangereuse = replace(LIVRABLE, etapes=tuple(
            replace(c, expiration=Expiration.PUBLIER_PROVISOIRE) if c.etape == Etape.FORMATEUR else c
            for c in LIVRABLE.etapes))
        self.monter(type_=TypeExercice.MISE_EN_SITUATION, surcharges=(Surcharge(None, "EX1", dangereuse),))
        copie = _copie_type(self.m, "COH1")
        self.assertEqual(chaine_de(copie, self.m, self.source), CHAINES_DEFAUT[TypeExercice.MISE_EN_SITUATION])
        self.m.exercices.clear()
        configuree = chaine(Etape.FORMATEUR)
        self.source.reglages_ = ReglagesEvaluation(chaines={TypeExercice.MISE_EN_SITUATION: configuree})
        self.source.surcharges_ = ()
        self.assertEqual(chaine_de(copie, self.m, self.source), configuree)

    def test_suppleant_de_la_cohorte(self):
        copie = _copie_type(Memoire(), "COH1")
        surcharges = (Surcharge(None, "EX1", LIVRABLE, suppleant="x@x.ci"), Surcharge("COH2", None, LIVRABLE, "y@x.ci"),
                      Surcharge("COH1", None, LIVRABLE), Surcharge("COH1", None, LIVRABLE, "sup@x.ci"))
        self.assertEqual(suppleant_de(copie, surcharges), "sup@x.ci")
        self.assertIsNone(suppleant_de(copie, surcharges[:3]))


class TestTraiterEcheances(Cas):
    def test_pair_en_retard_reattribue(self):
        self.monter(yaml=replace(LIVRABLE, nb_pairs=1), taille=3)
        a, b, c = (self.rendre(e) for e in ("a@x.ci", "b@x.ci", "c@x.ci"))
        for cid in (a, b, c):
            self.avancer.executer(cid, Etape.CONTROLES)
        (b_relit_a,) = self.m.relectures_de(a)
        (a_relit_b,) = self.m.relectures_de(b)
        self.assertEqual((b_relit_a.relecteur, a_relit_b.relecteur), ("b@x.ci", "a@x.ci"))
        self.relire.executer("a@x.ci", a_relit_b.id, NIVEAUX, COMMENTAIRES)
        self.avancer_horloge(72)
        self.assertEqual(self.m.rel[b_relit_a.id].statut, StatutRelecture.REATTRIBUEE)
        (nouvelle,) = self.m.relectures_de(a, StatutRelecture.A_FAIRE)
        self.assertEqual((nouvelle.relecteur, nouvelle.echeance), ("c@x.ci", self.t + timedelta(hours=72)))
        self.assertEqual(self.m.dispensees, [b])  # b n'a pas relu : sa note n'est plus masquée
        # la copie de a attend la relecture réattribuée ; celle de c, sans relecteur, avance
        self.assertEqual(self.etape(a), ("pairs", Statut.EN_RELECTURE))
        self.assertEqual(self.m.etat(a).echeance, nouvelle.echeance)
        self.assertEqual(self.etape(c), ("formateur", Statut.A_CORRIGER))
        for action in ("relecture réattribuée", "relectures dispensées", "réattribuer", "passer"):
            self.assertIn(action, self.actions())
        # personne d'autre à solliciter : la copie avance avec les relectures obtenues
        self.avancer_horloge(72)
        self.assertEqual(self.m.rel[nouvelle.id].statut, StatutRelecture.ANNULEE)
        self.assertEqual(self.etape(a), ("formateur", Statut.A_CORRIGER))

    def test_pair_en_retard_dispense(self):
        pairs = ConfigEtape(Etape.PAIRS, True, 72, Expiration.DISPENSER)
        self.monter(yaml=replace(LIVRABLE, etapes=tuple(pairs if c.etape == Etape.PAIRS else c
                                                        for c in LIVRABLE.etapes)), taille=2)
        a, b = self.rendre("a@x.ci"), self.rendre("b@x.ci")
        for cid in (a, b):
            self.avancer.executer(cid, Etape.CONTROLES)
        self.avancer_horloge(72)
        self.assertEqual({r.statut for r in self.m.rel.values()}, {StatutRelecture.ANNULEE})
        self.assertEqual(sorted(self.m.dispensees), [a, b])
        self.assertEqual({self.etape(a), self.etape(b)}, {("formateur", Statut.A_CORRIGER)})
        self.assertIn("dispenser", self.actions())

    def test_formateur_echu_escalade_au_suppleant_puis_au_responsable(self):
        reglages = ReglagesEvaluation(responsable_pedagogique="resp@x.ci")
        self.monter(reglages=reglages, surcharges=(Surcharge("COH1", None, chaine(Etape.FORMATEUR), "sup@x.ci"),))
        a = self.rendre("a@x.ci")
        self.avancer_horloge(1)
        self.assertEqual(self.m.etat(a), Etat("formateur", self.t + timedelta(hours=1), "sup@x.ci"))
        self.assertEqual(self.journal[-1][1:], (SYSTEME, "escalader", {"correcteurs": ["form@x.ci"]},
                                                {"correcteur": "sup@x.ci"}))
        self.avancer_horloge(1)
        self.assertEqual(self.m.etat(a).escalade_a, "resp@x.ci")
        self.assertEqual(self.journal[-1][3:], ({"correcteurs": ["sup@x.ci"]}, {"correcteur": "resp@x.ci"}))
        self.avancer_horloge(1)  # escalade épuisée, publication provisoire désactivée
        self.assertEqual(self.m.etat(a), Etat("formateur", None, "resp@x.ci"))
        self.assertEqual(self.m.copie(a).statut, Statut.A_CORRIGER)
        self.assertEqual(self.actions()[-1], "escalade épuisée")
        self.avancer_horloge(100)
        self.assertEqual(self.actions()[-1], "escalade épuisée")  # plus rien à traiter

    def test_sans_suppleant_escalade_au_responsable(self):
        self.monter(yaml=chaine(Etape.FORMATEUR), reglages=ReglagesEvaluation(responsable_pedagogique="resp@x.ci"))
        a = self.rendre("a@x.ci")
        self.avancer_horloge(1)
        self.assertEqual(self.m.etat(a).escalade_a, "resp@x.ci")

    def test_suppleant_responsable_ne_compte_qu_une_fois(self):
        self.monter(reglages=ReglagesEvaluation(responsable_pedagogique="r@x.ci"),
                    surcharges=(Surcharge("COH1", None, chaine(Etape.FORMATEUR), "r@x.ci"),))
        a = self.rendre("a@x.ci")
        self.avancer_horloge(1)
        self.avancer_horloge(1)
        self.assertEqual(self.m.etat(a), Etat("formateur", None, "r@x.ci"))

    def toute_la_chaine_echue(self, provisoire):
        self.monter(reglages=ReglagesEvaluation(publication_provisoire=provisoire), taille=2)
        a = self.rendre("a@x.ci")
        for _ in range(24 * 30):
            self.avancer_horloge(1)
        return a

    def test_toute_la_chaine_echue_publication_provisoire(self):
        a = self.toute_la_chaine_echue(True)
        self.assertEqual(self.etape(a), ("formateur", Statut.PROVISOIRE))
        self.assertIsNone(self.m.etat(a).echeance)
        self.assertEqual(self.actions()[-1], "publication provisoire")

    def test_toute_la_chaine_echue_sans_publication_provisoire(self):
        a = self.toute_la_chaine_echue(False)
        self.assertEqual(self.etape(a), ("formateur", Statut.A_CORRIGER))
        self.assertNotIn("publication provisoire", self.actions())

    def test_formateur_publication_provisoire_a_expiration(self):
        formateur = ConfigEtape(Etape.FORMATEUR, True, 1, Expiration.PUBLIER_PROVISOIRE)
        self.monter(yaml=Chaine((formateur,)), reglages=ReglagesEvaluation(publication_provisoire=True))
        a = self.rendre("a@x.ci")
        self.avancer_horloge(1)
        self.assertEqual(self.m.copie(a).statut, Statut.PROVISOIRE)

    def test_jure_absent_escalade_au_formateur(self):
        self.monter(type_=TypeExercice.CAPSTONE)
        a = self.rendre("a@x.ci")
        self.avancer.executer(a, Etape.CONTROLES)
        self.avancer.executer(a, Etape.IA)
        self.assertEqual(self.etape(a), ("jury", Statut.A_CORRIGER))
        self.avancer_horloge(168)
        self.assertEqual(self.etape(a), ("formateur", Statut.A_CORRIGER))
        self.assertIn("escalader", self.actions())

    def test_actions_automatiques_journalisees_par_le_systeme(self):
        self.monter(yaml=chaine(Etape.CONTROLES, Etape.FORMATEUR))
        a = self.rendre("a@x.ci")
        self.avancer_horloge(1)
        (passer,) = [j for j in self.journal if j[2] == "passer"]
        self.assertEqual(passer, (a, SYSTEME, "passer", {"etape": "controles"}, {}))

    def test_une_erreur_n_arrete_pas_le_traitement(self):
        self.monter(yaml=chaine(Etape.CONTROLES, Etape.FORMATEUR))
        a, b = self.rendre("a@x.ci"), self.rendre("b@x.ci")
        isoles = []

        def isoler(action):
            isoles.append(action)
            if len(isoles) > 1:
                action()

        TraiterEcheances(self.m, self.m, self.source, self.avancer, lambda: DEBUT + timedelta(hours=1),
                         lambda *args: None, isoler).executer()
        self.assertEqual((self.etape(a)[0], self.etape(b)[0]), ("controles", "formateur"))
