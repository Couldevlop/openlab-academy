import unittest
from datetime import timedelta

from openlab_academy.application.chaine import FaireAvancer, TraiterEcheances
from openlab_academy.application.corriger import (
    LIEN_RETOUR, Acces, AccesRefuse, ConsulterCorrection, CorrectionRefusee, CorrigerCopie, GererDelegations,
    PublierNote, ValiderLot, derniere, fiabilite, synthese)
from openlab_academy.application.pre_corriger import SIGNALEMENT
from openlab_academy.application.soumettre_copie import Contenu
from openlab_academy.domain.copie import Proposition, Source, Statut
from openlab_academy.domain.delegation import Delegation
from openlab_academy.domain.reglages_evaluation import Etape, TypeExercice
from openlab_academy.tests.memoire_evaluation import DEBUT, Memoire, SourceMemoire
from openlab_academy.tests.test_chaine import chaine

A, B = "a@x.ci", "b@x.ci"
FORM, DELEG, AUTRE, ADMIN, SUPP = "form@x.ci", "deleg@x.ci", "autre@x.ci", "admin@x.ci", "supp@x.ci"
J1, J2, J3 = "j1@x.ci", "j2@x.ci", "j3@x.ci"
MOYENS = {"pertinence": 1, "rigueur": 1}  # 10/20 sur la grille de test
BONS = {"pertinence": 2, "rigueur": 2}


def ia(niveaux, confiance=0.9):
    return Proposition(Source.IA, "ia", dict(niveaux), {c: f"Justification {c}" for c in niveaux},
                       {c: "extrait" for c in niveaux}, confiance)


def delegation(titulaire=FORM, delegataire=DELEG, **autres):
    return Delegation(titulaire, delegataire, DEBUT - timedelta(days=1), DEBUT + timedelta(days=10), **autres)


class Cas(unittest.TestCase):
    def monter(self, *actives, jures=(), delegations=(), seuil=10.0):
        actives = actives or (Etape.CONTROLES, Etape.IA, Etape.FORMATEUR)
        self.chaine_ = chaine(*actives, seuil_reussite=seuil)
        self.m = Memoire(TypeExercice.MISE_EN_SITUATION, self.chaine_)
        self.m.jures_ = set(jures)
        self.source = SourceMemoire()
        self.t = DEBUT
        self.journal, self.notes = [], []
        horloge = lambda: self.t  # noqa: E731
        journal = lambda *args: self.journal.append(args)  # noqa: E731
        self.avancer = FaireAvancer(self.m, self.m, self.source, horloge, lambda *a: None, journal)
        self.echeances = TraiterEcheances(self.m, self.m, self.source, self.avancer, horloge, journal)
        self.delegations = list(delegations)
        self.acces = Acces(self.m, lambda: self.delegations, horloge, lambda u: u == ADMIN)
        self.corriger = CorrigerCopie(self.m, self.acces, self.avancer, journal)
        self.publier = PublierNote(self.m, self.acces, self.avancer, journal, lambda *a: self.notes.append(a))
        self.lot = ValiderLot(self.m, self.acces, 0.8, journal)
        self.vue = ConsulterCorrection(self.m, self.acces, 0.8)

    def a_corriger(self, apprenant=A):
        """Copie rendue, contrôles passés : à l'étape suivante (jury ou formateur)."""
        cid = self.m.rendre(apprenant, self.chaine_, self.t)
        self.avancer.demarrer(cid)
        while self.m.etat(cid).etape not in (Etape.JURY.value, Etape.FORMATEUR.value):
            self.avancer.executer(cid, Etape(self.m.etat(cid).etape))
        return cid

    def dernier(self, action):
        return next(j for j in reversed(self.journal) if j[2] == action)


class TestAcces(Cas):
    def test_titulaire_formateur(self):
        self.monter()
        cid = self.a_corriger()
        hab = self.acces.correcteur(FORM, self.m.copie(cid), self.m.etat(cid))
        self.assertEqual((hab.source, hab.au_nom_de), (Source.FORMATEUR, None))

    def test_auteur_refuse_meme_titulaire_ou_administrateur(self):
        self.monter()
        for auteur in (FORM, ADMIN):
            cid = self.a_corriger(auteur)
            with self.subTest(auteur=auteur), self.assertRaises(AccesRefuse):
                self.acces.correcteur(auteur, self.m.copie(cid), self.m.etat(cid))

    def test_administrateur_corrige_en_son_nom(self):
        self.monter()
        cid = self.a_corriger()
        self.assertIsNone(self.acces.correcteur(ADMIN, self.m.copie(cid), self.m.etat(cid)).au_nom_de)

    def test_destinataire_de_l_escalade(self):
        self.monter()
        cid = self.a_corriger()
        self.m.escalader(cid, SUPP, None)
        self.assertEqual(self.acces.correcteur(SUPP, self.m.copie(cid), self.m.etat(cid)).source, Source.FORMATEUR)

    def test_delegataire_agit_au_nom_du_titulaire_le_plus_specifique(self):
        self.monter(delegations=[delegation(), delegation(titulaire="form2@x.ci", exercice="EX1")])
        self.m.titulaires_ = {FORM, "form2@x.ci"}
        cid = self.a_corriger()
        self.assertEqual(self.acces.correcteur(DELEG, self.m.copie(cid), self.m.etat(cid)).au_nom_de, "form2@x.ci")

    def test_delegation_expiree_revoquee_ou_hors_perimetre_refusee(self):
        for d in (delegation(revoquee=True), delegation(cohorte="AUTRE"),
                  Delegation(FORM, DELEG, DEBUT - timedelta(days=5), DEBUT - timedelta(days=1)),
                  delegation(titulaire="inconnu@x.ci")):
            self.monter(delegations=[d])
            cid = self.a_corriger()
            with self.subTest(d=d), self.assertRaises(AccesRefuse):
                self.acces.correcteur(DELEG, self.m.copie(cid), self.m.etat(cid))

    def test_formateur_quelconque_refuse(self):
        self.monter()
        cid = self.a_corriger()
        with self.assertRaisesRegex(AccesRefuse, "ni titulaire ni délégataire"):
            self.acces.correcteur(AUTRE, self.m.copie(cid), self.m.etat(cid))

    def test_jure_a_l_etape_jury_et_son_delegataire(self):
        self.monter(Etape.CONTROLES, Etape.JURY, Etape.FORMATEUR, jures={J1}, delegations=[delegation(J1, DELEG)])
        cid = self.a_corriger()
        copie, etat = self.m.copie(cid), self.m.etat(cid)
        self.assertEqual(self.acces.habilitation(J1, copie, etat).source, Source.JURY)
        hab = self.acces.habilitation(DELEG, copie, etat)
        self.assertEqual((hab.source, hab.au_nom_de), (Source.JURY, J1))
        self.assertEqual(self.acces.habilitation(FORM, copie, etat).source, Source.FORMATEUR)
        with self.assertRaises(AccesRefuse):
            self.acces.habilitation(AUTRE, copie, etat)

    def test_jure_hors_etape_jury_refuse(self):
        self.monter(jures={J1})
        cid = self.a_corriger()
        with self.assertRaises(AccesRefuse):
            self.acces.habilitation(J1, self.m.copie(cid), self.m.etat(cid))


class TestCorrigerCopie(Cas):
    def test_proposition_formateur_journalisee(self):
        self.monter()
        cid = self.a_corriger()
        self.corriger.executer(FORM, cid, MOYENS, {"pertinence": "  Bien.  ", "general": "Bon travail."})
        p = derniere(self.m.propositions(cid), Source.FORMATEUR)
        self.assertEqual((p.auteur, p.niveaux, p.commentaires, p.au_nom_de),
                         (FORM, MOYENS, {"pertinence": "Bien.", "general": "Bon travail."}, None))
        j = self.dernier("correction")
        self.assertEqual((j[0], j[1], j[4], j[5]), (cid, FORM, {"niveaux": MOYENS}, None))

    def test_delegataire_journal_avec_les_deux_identites(self):
        self.monter(delegations=[delegation()])
        cid = self.a_corriger()
        self.corriger.executer(DELEG, cid, MOYENS)
        self.corriger.executer(DELEG, cid, BONS)
        self.assertEqual(derniere(self.m.propositions(cid), Source.FORMATEUR).au_nom_de, FORM)
        j = self.dernier("correction")
        self.assertEqual((j[1], j[3], j[5]), (DELEG, {"niveaux": MOYENS}, FORM))

    def test_acces_verifie_avant_tout(self):
        self.monter()
        cid = self.a_corriger()
        with self.assertRaises(AccesRefuse):
            self.corriger.executer(AUTRE, cid, {"inconnu": 9})
        with self.assertRaises(AccesRefuse):
            self.corriger.executer(A, cid, MOYENS)  # l'auteur
        self.assertIsNone(derniere(self.m.propositions(cid), Source.FORMATEUR))

    def test_copie_pas_encore_a_corriger(self):
        self.monter()
        cid = self.m.rendre(A, self.chaine_, self.t)
        self.avancer.demarrer(cid)
        with self.assertRaisesRegex(CorrectionRefusee, "pas à corriger"):
            self.corriger.executer(FORM, cid, MOYENS)

    def test_niveaux_et_commentaires_valides(self):
        self.monter()
        cid = self.a_corriger()
        for niveaux, commentaires in (({"pertinence": 1}, None), ({"pertinence": 1, "rigueur": 7}, None),
                                      ({"pertinence": 1, "rigueur": True}, None), ("1,1", None),
                                      (MOYENS, {"inconnu": "x"}), (MOYENS, {"pertinence": "x" * 5001}),
                                      (MOYENS, {"pertinence": 3}), (MOYENS, "texte")):
            with self.subTest(niveaux=niveaux, commentaires=commentaires), self.assertRaises(CorrectionRefusee):
                self.corriger.executer(FORM, cid, niveaux, commentaires)

    def test_note_provisoire_remplacable(self):
        self.monter()
        cid = self.a_corriger()
        self.m.changer_statut(cid, Statut.PROVISOIRE, "formateur", None)
        self.corriger.executer(FORM, cid, BONS)
        self.assertEqual(derniere(self.m.propositions(cid), Source.FORMATEUR).niveaux, BONS)

    def test_jury_complet_fait_avancer(self):
        self.monter(Etape.CONTROLES, Etape.JURY, Etape.FORMATEUR, jures={J1, J2, J3})
        cid = self.a_corriger()
        self.assertEqual(self.m.etat(cid).etape, "jury")
        for jure in (J1, J2):
            self.corriger.executer(jure, cid, MOYENS)
        self.corriger.executer(J2, cid, BONS)  # un juré revient sur sa note : toujours deux votants
        self.assertEqual(self.m.etat(cid).etape, "jury")
        self.corriger.executer(J3, cid, BONS)
        self.assertEqual(self.m.etat(cid).etape, "formateur")
        self.assertEqual(self.dernier("note du jury")[1], J3)

    def test_deux_jures_sur_trois_puis_echeance_mediane_des_deux(self):
        self.monter(Etape.CONTROLES, Etape.JURY, Etape.FORMATEUR, jures={J1, J2, J3})
        cid = self.a_corriger()
        self.corriger.executer(J1, cid, {"pertinence": 2, "rigueur": 1})
        self.corriger.executer(J2, cid, {"pertinence": 1, "rigueur": 0})
        self.t += timedelta(hours=2)
        self.echeances.executer()
        self.assertEqual(self.m.etat(cid).etape, "formateur")
        vue = self.vue.copie(FORM, cid)
        self.assertEqual(vue["jury"], {"mediane": {"pertinence": 1, "rigueur": 0}, "nombre": 2, "attendus": 3})

    def test_jury_par_delegation_compte_pour_le_titulaire(self):
        self.monter(Etape.CONTROLES, Etape.JURY, Etape.FORMATEUR, jures={J1}, delegations=[delegation(J1, DELEG)])
        cid = self.a_corriger()
        self.corriger.executer(DELEG, cid, MOYENS)
        self.assertEqual(self.m.etat(cid).etape, "formateur")
        self.assertEqual(self.dernier("note du jury")[5], J1)


class TestValiderLot(Cas):
    def lot_de(self, n=2, confiance=0.9):
        self.monter()
        ids = [self.a_corriger(f"e{i}@x.ci") for i in range(n)]
        for cid in ids:
            self.m.ajouter_proposition(cid, ia(MOYENS, confiance))
        return ids

    def test_reprend_la_proposition_ia(self):
        ids = self.lot_de()
        self.assertEqual(self.lot.executer(FORM, ids + ids[:1]), sorted(ids))
        for cid in ids:
            p = derniere(self.m.propositions(cid), Source.FORMATEUR)
            self.assertEqual((p.niveaux, p.commentaires["pertinence"]), (MOYENS, "Justification pertinence"))
        self.assertEqual([j[2] for j in self.journal[-2:]], ["validation par lot"] * 2)

    def test_tout_ou_rien_si_une_copie_est_inaccessible(self):
        ids = self.lot_de()
        self.m.titulaires_ = {FORM}
        mienne = self.a_corriger(FORM)  # le formateur ne valide pas sa propre copie
        self.m.ajouter_proposition(mienne, ia(MOYENS))
        with self.assertRaises(AccesRefuse):
            self.lot.executer(FORM, ids + [mienne])
        self.assertTrue(all(derniere(self.m.propositions(c), Source.FORMATEUR) is None for c in ids))

    def test_hors_lot_refuse(self):
        ids = self.lot_de(confiance=0.5)
        with self.assertRaisesRegex(CorrectionRefusee, "hors lot"):
            self.lot.executer(FORM, ids)
        sans_ia = self.a_corriger("x@x.ci")
        with self.assertRaisesRegex(CorrectionRefusee, "hors lot"):
            self.lot.executer(FORM, [sans_ia])
        incomplete = self.a_corriger("y@x.ci")
        self.m.ajouter_proposition(incomplete, ia({"pertinence": 1}))
        with self.assertRaisesRegex(CorrectionRefusee, "niveau est attendu"):
            self.lot.executer(FORM, [incomplete])

    def test_lot_vide_ou_copie_terminee(self):
        ids = self.lot_de(1)
        with self.assertRaisesRegex(CorrectionRefusee, "aucune copie"):
            self.lot.executer(FORM, [])
        self.m.changer_statut(ids[0], Statut.PUBLIEE, "", None)
        with self.assertRaisesRegex(CorrectionRefusee, "pas à corriger"):
            self.lot.executer(FORM, ids)


class TestPublierNote(Cas):
    def corrigee(self, niveaux=MOYENS, seuil=10.0, **options):
        self.monter(seuil=seuil, **options)
        cid = self.a_corriger()
        self.corriger.executer(FORM, cid, niveaux)
        return cid

    def test_pass_a_10_sur_20_avec_seuil_10(self):
        cid = self.corrigee()
        self.assertEqual(self.publier.executer(FORM, cid), 10.0)
        self.assertEqual(self.m.copie(cid).statut, Statut.PUBLIEE)
        self.assertEqual(self.m.etat(cid).etape, "")
        (copie, note, reussite, resume, lien), = self.m.publications
        self.assertEqual((copie, note, reussite, lien), (cid, 10.0, True, LIEN_RETOUR.format(cid)))
        self.assertIn("10/20", resume)
        self.assertEqual(self.m.resultat(cid), (10.0, 20, True))
        self.assertEqual(self.notes[0][0], A)
        j = self.dernier("note publiée")
        self.assertEqual((j[1], j[3], j[4]["note"], j[5]), (FORM, {"statut": "a_corriger"}, 10.0, None))

    def test_fail_sous_le_seuil(self):
        cid = self.corrigee(seuil=12)
        self.publier.executer(FORM, cid)
        self.assertEqual(self.m.publications[0][2], False)

    def test_depuis_provisoire(self):
        cid = self.corrigee()
        self.m.changer_statut(cid, Statut.PROVISOIRE, "formateur", None)
        self.publier.executer(FORM, cid)
        self.assertEqual(self.dernier("note publiée")[3], {"statut": "provisoire"})

    def test_delegataire_publie_au_nom_du_titulaire(self):
        cid = self.corrigee(delegations=[delegation()])
        self.publier.executer(DELEG, cid)
        j = self.dernier("note publiée")
        self.assertEqual((j[1], j[5]), (DELEG, FORM))

    def test_refus(self):
        cid = self.corrigee()
        for acteur in (A, AUTRE):
            with self.subTest(acteur=acteur), self.assertRaises(AccesRefuse):
                self.publier.executer(acteur, cid)
        self.publier.executer(FORM, cid)
        with self.assertRaisesRegex(CorrectionRefusee, "pas à corriger"):
            self.publier.executer(FORM, cid)

    def test_sans_correction_du_formateur(self):
        self.monter()
        cid = self.a_corriger()
        self.m.ajouter_proposition(cid, ia(BONS))
        with self.assertRaisesRegex(CorrectionRefusee, "aucune correction"):
            self.publier.executer(FORM, cid)


class TestSynthese(unittest.TestCase):
    def test_sources_mediane_ecarts_et_niveaux_provisoires(self):
        props = [Proposition(Source.AUTO_EVALUATION, A, MOYENS),
                 Proposition(Source.CONTROLES, "systeme", {}, {"motif_1": "README absent"}),
                 ia({"pertinence": 0, "rigueur": 1}),
                 Proposition(Source.PAIR, "p1", BONS, {"pertinence": "ok", "rigueur": "ok"}),
                 Proposition(Source.PAIR, "p2", {"pertinence": 2, "rigueur": 1})]
        s = synthese(props)
        self.assertEqual((s.auto_evaluation.niveaux, s.controles), (MOYENS, ("README absent",)))
        self.assertEqual((s.mediane_pairs, s.ecarts), ({"pertinence": 2, "rigueur": 1}, {"pertinence"}))
        self.assertEqual(s.niveaux_provisoires(), {"pertinence": 2, "rigueur": 1})
        jury = synthese(props + [Proposition(Source.JURY, J1, MOYENS)])
        self.assertEqual(jury.niveaux_provisoires(), MOYENS)
        formateur = synthese(props + [Proposition(Source.FORMATEUR, FORM, BONS)])
        self.assertEqual(formateur.niveaux_provisoires(), BONS)
        self.assertIsNone(synthese([ia(BONS)]).niveaux_provisoires())
        self.assertEqual(synthese([]).ecarts, set())

    def test_fiabilite_ecart_moyen_ia_formateur_par_critere(self):
        copies = [[ia({"pertinence": 2, "rigueur": 0}), Proposition(Source.FORMATEUR, FORM, MOYENS)],
                  [ia({"pertinence": 1}), Proposition(Source.FORMATEUR, FORM, BONS)],
                  [ia(BONS)], [Proposition(Source.FORMATEUR, FORM, BONS)]]
        self.assertEqual(fiabilite(copies), {"pertinence": 1.0, "rigueur": 1.0})
        self.assertEqual(fiabilite([]), {})


class TestConsulterCorrection(Cas):
    def test_file_des_copies_corrigeables_et_lots(self):
        self.monter()
        ids = [self.a_corriger(f"e{i}@x.ci") for i in range(4)]
        for cid in ids[:3]:
            self.m.ajouter_proposition(cid, ia(BONS))
        self.m.ajouter_proposition(ids[2], Proposition(Source.PAIR, "p", {"pertinence": 0, "rigueur": 2}))
        mienne = self.a_corriger(FORM)
        file = self.vue.file(FORM)
        self.assertEqual([c["copie"] for c in file["copies"]], ids)
        self.assertNotIn(mienne, [c["copie"] for c in file["copies"]])
        self.assertEqual(file["lots"], [ids[:2]])  # écart IA/pairs : hors lot
        premiere = file["copies"][0]
        self.assertEqual((premiere["apprenant"], premiere["confiance"], premiere["role"]), ("e0@x.ci", 0.9, "formateur"))
        self.assertEqual(self.vue.file(AUTRE), {"copies": [], "lots": []})
        self.assertEqual(self.vue.file(FORM, exercice="EX2"), {"copies": [], "lots": []})

    def test_file_du_jure(self):
        self.monter(Etape.CONTROLES, Etape.JURY, Etape.FORMATEUR, jures={J1})
        cid = self.a_corriger()
        self.assertEqual([(c["copie"], c["role"]) for c in self.vue.file(J1)["copies"]], [(cid, "jury")])

    def test_copie_complete_pour_le_formateur(self):
        self.monter()
        cid = self.a_corriger()
        self.m.contenus[cid] = Contenu("Ma copie", "", "", "sig", "S1")
        for p in (Proposition(Source.AUTO_EVALUATION, A, MOYENS),
                  Proposition(Source.CONTROLES, "systeme", {}, {"motif_1": "trop court"}), ia(BONS, 0.7),
                  Proposition(Source.PAIR, "p1", {"pertinence": 0, "rigueur": 2}, {"pertinence": "à revoir"})):
            self.m.ajouter_proposition(cid, p)
        self.m.signalees.add(cid)
        vue = self.vue.copie(FORM, cid)
        self.assertEqual((vue["contenu"], vue["consigne"], vue["apprenant"]), ("Ma copie", "Analysez le cas.", A))
        self.assertEqual((vue["auto_evaluation"], vue["controles"]), (MOYENS, ["trop court"]))
        self.assertEqual(vue["ia"], {"niveaux": BONS, "justifications": {"pertinence": "Justification pertinence",
                                                                         "rigueur": "Justification rigueur"},
                                     "citations": {"pertinence": "extrait", "rigueur": "extrait"}, "confiance": 0.7})
        self.assertEqual(vue["pairs"], {"mediane": {"pertinence": 0, "rigueur": 2}, "nombre": 1,
                                        "commentaires": [{"pertinence": "à revoir"}]})
        self.assertEqual((vue["ecarts"], vue["signalement"], vue["formateur"]), (["pertinence"], SIGNALEMENT, None))
        self.assertEqual(vue["grille"]["criteres"][0]["code"], "pertinence")
        self.corriger.executer(FORM, cid, MOYENS, {"general": "Bien"})
        self.assertEqual(self.vue.copie(FORM, cid)["formateur"],
                         {"niveaux": MOYENS, "commentaires": {"general": "Bien"}, "auteur": FORM, "au_nom_de": None})

    def test_copie_sans_ia_ni_signalement(self):
        self.monter()
        cid = self.a_corriger()
        vue = self.vue.copie(FORM, cid)
        self.assertEqual((vue["ia"], vue["signalement"], vue["auto_evaluation"]), (None, "", None))

    def test_copie_refusee_hors_habilitation(self):
        self.monter()
        cid = self.a_corriger()
        with self.assertRaises(AccesRefuse):
            self.vue.copie(AUTRE, cid)


class TestGererDelegations(Cas):
    def setUp(self):
        self.monter()
        self.gerer = GererDelegations(self.m, lambda u: u in {FORM, DELEG, AUTRE, ADMIN}, lambda u: u == ADMIN,
                                      lambda: self.t, lambda *a: self.journal.append(a))

    def test_deleguer_ses_propres_corrections(self):
        did = self.gerer.deleguer(FORM, delegation())
        self.assertEqual(self.m.delegation(did).delegataire, DELEG)
        j = self.dernier("délégation créée")
        self.assertEqual((j[0], j[1], j[4]["delegataire"]), (f"délégation:{did}", FORM, DELEG))

    def test_pour_autrui_reserve_au_superviseur(self):
        with self.assertRaisesRegex(AccesRefuse, "propres corrections"):
            self.gerer.deleguer(AUTRE, delegation())
        self.assertTrue(self.gerer.deleguer(ADMIN, delegation()))

    def test_titulaire_ou_delegataire_non_habilite(self):
        with self.assertRaises(AccesRefuse):
            self.gerer.deleguer(A, delegation(titulaire=A))
        with self.assertRaisesRegex(CorrectionRefusee, "habilité"):
            self.gerer.deleguer(FORM, delegation(delegataire=A))

    def test_delegation_incoherente(self):
        for d in (delegation(delegataire=FORM),
                  Delegation(FORM, DELEG, DEBUT, DEBUT),
                  Delegation(FORM, DELEG, DEBUT - timedelta(days=3), DEBUT - timedelta(days=1))):
            with self.subTest(d=d), self.assertRaises(CorrectionRefusee):
                self.gerer.deleguer(FORM, d)

    def test_revoquer(self):
        did = self.gerer.deleguer(FORM, delegation())
        with self.assertRaises(AccesRefuse):
            self.gerer.revoquer(AUTRE, did)
        with self.assertRaises(AccesRefuse):
            self.gerer.revoquer(FORM, "inconnue")
        self.gerer.revoquer(FORM, did)
        self.assertTrue(self.m.delegation(did).revoquee)
        self.assertEqual(self.dernier("délégation révoquée")[1], FORM)
        n = len(self.journal)
        self.gerer.revoquer(ADMIN, did)  # déjà révoquée : rien de plus
        self.assertEqual(len(self.journal), n)
