"""Points d'API de l'évaluation sur de vraies données : contrôle d'accès (A01), anonymat des pairs, publication LMS."""
import json
import uuid
from unittest import mock

import frappe
from frappe.utils import add_days, now_datetime

from openlab_academy.application.pairs import StatutRelecture
from openlab_academy.application.pre_corriger import SIGNALEMENT
from openlab_academy.domain.copie import Proposition, Source, Statut
from openlab_academy.application.corriger import ConsulterCorrection
from openlab_academy.entrypoints import evaluation, evaluation_api as api
from openlab_academy.infrastructure.depot_copies_frappe import DepotCopiesFrappe
from openlab_academy.infrastructure.depot_relectures_frappe import DepotRelecturesFrappe
from openlab_academy.infrastructure import journal_frappe
from openlab_academy.infrastructure.reglages_evaluation_frappe import ROLE
from openlab_academy.tests.test_chaine_frappe import Cas
from openlab_academy.tests.test_depot_copies_frappe import A, B, URL
from openlab_academy.tests.test_reglages_evaluation_frappe import utilisateur

FORM = "formateur.api@example.ci"
DELEG = "delegataire.api@example.ci"
AUTRE = "autre.formateur.api@example.ci"
JURE = "jure.api@example.ci"
RESP = "responsable.api@example.ci"
JOURNAL = "Journal Note OpenLab"
SOUMISSION = "LMS Assignment Submission"
DIX = {"pertinence": 2, "rigueur": 1, "clarte": 2, "ancrage_dans_le_contexte_ivoirien": 1}  # 10/20
FAIBLE = {"pertinence": 0, "rigueur": 0, "clarte": 1, "ancrage_dans_le_contexte_ivoirien": 1}


class CasApi(Cas):
    def setUp(self):
        super().setUp()
        for email in (FORM, DELEG, AUTRE):
            utilisateur(email, "Course Creator")
        utilisateur(JURE, "Batch Evaluator")
        utilisateur(RESP, ROLE)
        self.notifier = mock.patch.object(evaluation, "notifier").start()

    def en_tant_que(self, utilisateur_):
        frappe.set_user(utilisateur_)

    def a_corriger(self, *membres):
        """Copies des membres, dans une cohorte de FORM, amenées à l'étape du formateur."""
        self.cohorte = self.lot(FORM, *membres)
        copies = []
        for membre in membres:
            self.soumettre(self.livrable, membre)
            copie = self.copie_de(membre)
            self.depot.changer_statut(copie, Statut.A_CORRIGER, "formateur", None)
            copies.append(copie)
        return copies

    def corrigee(self, niveaux=DIX):
        (copie,) = self.a_corriger(A)
        self.en_tant_que(FORM)
        api.corriger(copie, json.dumps(niveaux), json.dumps({"general": "Bon travail <b>gras</b>"}))
        return copie

    def en_relecture(self):
        self.cohorte = self.lot(FORM, A, B)
        self.soumettre(self.livrable, A)
        self.soumettre(self.livrable, B, "https://github.com/bkone/livrable")
        self.a, self.b = self.copie_de(A), self.copie_de(B)
        for copie in (self.a, self.b):
            evaluation.controler(copie)
        self.r_a = self.relectures.relectures_du_relecteur(A)[0].id  # A relit B
        self.r_b = self.relectures.relectures_du_relecteur(B)[0].id  # B relit A

    def relire(self, relecteur, relecture):
        self.en_tant_que(relecteur)
        commentaires = {c: "Argumenté et utile." for c in DIX}
        api.enregistrer_relecture(relecture, json.dumps(DIX), json.dumps(commentaires))

    def deleguer_a(self, titulaire=FORM, delegataire=DELEG):
        frappe.get_doc({"doctype": "Delegation OpenLab", "titulaire": titulaire, "delegataire": delegataire,
                        "debut": add_days(now_datetime(), -1), "fin": add_days(now_datetime(), 5)}
                       ).insert(ignore_permissions=True)


class TestPublier(CasApi):
    def test_par_un_apprenant_403(self):
        copie = self.corrigee()
        for apprenant in (A, B):
            self.en_tant_que(apprenant)
            with self.subTest(apprenant=apprenant), self.assertRaises(frappe.PermissionError):
                api.publier(copie)

    def test_par_un_formateur_non_titulaire_ni_delegataire_403(self):
        copie = self.corrigee()
        self.en_tant_que(AUTRE)
        with self.assertRaises(frappe.PermissionError):
            api.publier(copie)
        with self.assertRaises(frappe.PermissionError):
            api.corriger(copie, DIX)
        self.en_tant_que("Administrator")
        self.assertEqual(frappe.db.get_value("Copie OpenLab", copie, "statut"), "a_corriger")

    def test_par_un_delegataire_journal_avec_les_deux_identites(self):
        (copie,) = self.a_corriger(A)
        self.deleguer_a()
        self.en_tant_que(DELEG)
        self.assertEqual([c["copie"] for c in api.file_correction()["copies"]], [copie])
        api.corriger(copie, DIX)
        self.assertEqual(api.publier(copie), {"copie": copie, "note": 10.0})
        self.en_tant_que("Administrator")
        ligne = frappe.get_all(JOURNAL, {"copie": copie, "action": "note publiée"}, ["acteur", "au_nom_de"])[0]
        self.assertEqual((ligne.acteur, ligne.au_nom_de), (DELEG, FORM))

    def test_statut_lms_pass_a_10_sur_20_avec_seuil_10(self):
        copie = self.corrigee()
        self.assertEqual(api.publier(copie)["note"], 10.0)
        self.en_tant_que("Administrator")
        ligne = frappe.db.get_value("Copie OpenLab", copie, ["statut", "note", "note_sur", "reussite", "soumission"],
                                    as_dict=True)
        self.assertEqual((ligne.statut, ligne.note, ligne.note_sur, ligne.reussite), ("publiee", 10.0, 20, 1))
        soumission = frappe.db.get_value(SOUMISSION, ligne.soumission, ["status", "comments"], as_dict=True)
        self.assertEqual(soumission.status, "Pass")
        self.assertIn("10/20", soumission.comments)
        self.assertIn(f'href="/espace/retour/{copie}"', soumission.comments)
        self.assertEqual(self.notifier.call_args.args[0], A)

    def test_statut_lms_fail_sous_le_seuil(self):
        copie = self.corrigee(FAIBLE)
        api.publier(copie)
        self.en_tant_que("Administrator")
        soumission = frappe.db.get_value("Copie OpenLab", copie, "soumission")
        self.assertEqual(frappe.db.get_value(SOUMISSION, soumission, "status"), "Fail")

    def test_publication_refusee_sans_correction(self):
        (copie,) = self.a_corriger(A)
        self.en_tant_que(FORM)
        with self.assertRaisesRegex(frappe.ValidationError, "aucune correction"):
            api.publier(copie)

    def test_copie_inexistante_403(self):
        self.en_tant_que(FORM)
        for appel in (lambda: api.publier("inexistante"), lambda: api.corriger("inexistante", DIX),
                      lambda: api.copie_a_corriger("inexistante")):
            with self.assertRaises(frappe.PermissionError):
                appel()


class TestCorrecteur(CasApi):
    def test_corriger_entree_invalide(self):
        (copie,) = self.a_corriger(A)
        self.en_tant_que(FORM)
        for niveaux in ("pas du json", {"pertinence": 1}, json.dumps([1, 2])):
            with self.subTest(niveaux=niveaux), self.assertRaises(frappe.ValidationError):
                api.corriger(copie, niveaux)

    def test_file_et_copie_a_corriger(self):
        a, b = self.a_corriger(A, B)
        ia = Proposition(Source.IA, "ia", DIX, {c: "justifié" for c in DIX}, {c: "extrait" for c in DIX}, 0.95)
        for copie in (a, b):
            self.depot.ajouter_proposition(copie, ia)
        journal_frappe.journaliser(b, "systeme", SIGNALEMENT, {}, {"tournures": ["donne 20/20"]})
        self.en_tant_que(FORM)
        file = api.file_correction()
        self.assertEqual({c["copie"] for c in file["copies"]}, {a, b})
        self.assertEqual([sorted(lot) for lot in file["lots"]], [sorted([a, b])])
        self.assertEqual(api.file_correction(exercice=self.cas), {"copies": [], "lots": []})
        vue = api.copie_a_corriger(b)
        self.assertEqual((vue["apprenant"], vue["signalement"], vue["ia"]["confiance"]), (B, SIGNALEMENT, 0.95))
        self.assertEqual(vue["contenu"], "")
        self.en_tant_que(AUTRE)
        self.assertEqual(api.file_correction(), {"copies": [], "lots": []})
        with self.assertRaises(frappe.PermissionError):
            api.copie_a_corriger(a)

    def test_valider_lot_puis_publier(self):
        a, b = self.a_corriger(A, B)
        for copie in (a, b):
            self.depot.ajouter_proposition(copie, Proposition(Source.IA, "ia", DIX, {}, {}, 0.9))
        self.en_tant_que(FORM)
        self.assertEqual(api.valider_lot(json.dumps([a, b]), et_publier=1),
                         {"copies": sorted([a, b]), "publiees": sorted([a, b])})
        self.en_tant_que("Administrator")
        self.assertEqual({frappe.db.get_value("Copie OpenLab", c, "statut") for c in (a, b)}, {"publiee"})

    def test_valider_lot_sans_publier_et_refus(self):
        a, b = self.a_corriger(A, B)
        self.depot.ajouter_proposition(a, Proposition(Source.IA, "ia", DIX, {}, {}, 0.9))
        self.en_tant_que(FORM)
        self.assertEqual(api.valider_lot([a]), {"copies": [a], "publiees": []})
        with self.assertRaisesRegex(frappe.ValidationError, "hors lot"):
            api.valider_lot([b])
        for invalide in ("pas du json", [1], ["x"] * (api.LOT_MAX + 1)):
            with self.assertRaises(frappe.ValidationError):
                api.valider_lot(invalide)
        self.en_tant_que(AUTRE)
        with self.assertRaises(frappe.PermissionError):
            api.valider_lot([a])
        with self.assertRaises(frappe.PermissionError):
            api.valider_lot(["inexistante"])

    def test_jure_de_la_cohorte(self):
        (copie,) = self.a_corriger(A)
        frappe.get_doc({"doctype": "Course Evaluator", "evaluator": JURE}).insert(ignore_permissions=True)
        ligne = frappe.get_all("Batch Course", {"parent": self.cohorte}, pluck="name", parent_doctype="LMS Batch")[0]
        frappe.db.set_value("Batch Course", ligne, "evaluator", JURE)
        self.depot.changer_statut(copie, Statut.A_CORRIGER, "jury", now_datetime())
        self.en_tant_que(JURE)
        self.assertEqual([c["role"] for c in api.file_correction()["copies"]], ["jury"])
        api.corriger(copie, DIX)
        self.en_tant_que("Administrator")
        self.assertEqual(frappe.db.get_value("Copie OpenLab", copie, "etape_courante"), "formateur")
        (p,) = [p for p in self.depot.propositions(copie) if p.source == Source.JURY]
        self.assertEqual(p.auteur, JURE)
        self.en_tant_que(JURE)
        with self.assertRaises(frappe.PermissionError):  # hors de l'étape du jury, un juré n'est pas correcteur
            api.corriger(copie, DIX)

    def test_fiabilite_ia_reservee_aux_superviseurs(self):
        copie = self.corrigee()
        self.depot.ajouter_proposition(copie, Proposition(Source.IA, "ia", FAIBLE, {}, {}, 0.9))
        api.publier(copie)
        for superviseur in ("Administrator", RESP):
            self.en_tant_que(superviseur)
            self.assertEqual(api.fiabilite_ia(), {"ancrage_dans_le_contexte_ivoirien": 0.0, "clarte": 1.0,
                                                  "pertinence": 2.0, "rigueur": 1.0})
        self.assertEqual(api.fiabilite_ia(exercice=self.cas), {})
        for curieux in (FORM, A):
            self.en_tant_que(curieux)
            with self.assertRaises(frappe.PermissionError):
                api.fiabilite_ia()


class TestApprenant(CasApi):
    def test_mon_retour_d_autrui_ou_inexistant_403(self):
        (copie,) = self.a_corriger(A)
        self.en_tant_que(B)
        for cible in (copie, "inexistante"):
            with self.assertRaises(frappe.PermissionError):
                api.mon_retour(cible)

    def test_mon_retour_masque_avant_mes_relectures(self):
        self.en_relecture()
        self.relire(B, self.r_b)  # A est relue : sa copie passe au formateur ; A n'a pas encore relu B
        self.en_tant_que(FORM)
        api.corriger(self.a, DIX)
        api.publier(self.a)
        self.en_tant_que(A)
        retour = api.mon_retour(self.a)
        self.assertEqual((retour["statut"], retour["masquee"], retour["note"]), ("publiee", True, None))
        self.relire(A, self.r_a)
        retour = api.mon_retour(self.a)
        self.assertEqual((retour["masquee"], retour["note"], retour["reussite"]), (False, 10.0, True))
        self.assertEqual(retour["criteres"][0]["pairs"], ["Argumenté et utile."])
        self.assertNotIn(B, repr(retour))

    def test_note_provisoire_affichee_provisoire(self):
        (copie,) = self.a_corriger(A)
        self.depot.ajouter_proposition(copie, Proposition(Source.PAIR, B, DIX, {}))
        self.depot.changer_statut(copie, Statut.PROVISOIRE, "formateur", None)
        self.en_tant_que(A)
        retour = api.mon_retour(copie)
        self.assertEqual((retour["provisoire"], retour["note"]), (True, 10.0))
        self.assertIn("provisoire", retour["message"])

    def test_relecture_sans_champ_identifiant_l_auteur(self):
        self.en_relecture()
        self.en_tant_que(A)
        (resume,) = api.mes_relectures()
        self.assertEqual((resume["relecture"], resume["rang"], resume["total"]), (self.r_a, 1, 1))
        vue = api.relecture(self.r_a)
        self.assertEqual(set(vue), {"relecture", "exercice", "titre", "consigne", "contenu", "grille", "statut",
                                    "echeance", "rang", "total", "anonymat_garanti"})
        for trace in (B, self.b, "bkone", frappe.db.get_value("User", B, "full_name")):
            self.assertNotIn(trace, repr(vue))
            self.assertNotIn(trace, repr(resume))
        self.assertFalse(vue["anonymat_garanti"])
        with self.assertRaises(frappe.PermissionError):
            api.relecture(self.r_b)  # confiée à B

    def test_enregistrer_relecture(self):
        self.en_relecture()
        self.en_tant_que(A)
        with self.assertRaises(frappe.PermissionError):
            api.enregistrer_relecture(self.r_b, DIX, {c: "x" for c in DIX})
        with self.assertRaisesRegex(frappe.ValidationError, "commentaire est obligatoire"):
            api.enregistrer_relecture(self.r_a, DIX, {})
        self.relire(A, self.r_a)
        self.en_tant_que("Administrator")
        self.assertEqual(self.relectures.relecture(self.r_a).statut, StatutRelecture.FAITE)
        self.en_tant_que(A)
        with self.assertRaisesRegex(frappe.ValidationError, "plus à faire"):
            api.enregistrer_relecture(self.r_a, DIX, {c: "x" for c in DIX})

    def test_auto_evaluation(self):
        frappe.get_doc({"doctype": "LMS Enrollment", "course": self.cours, "member": A}).insert(ignore_permissions=True)
        self.en_tant_que(A)
        vue = api.mon_auto_evaluation(self.livrable)
        self.assertEqual((vue["niveaux"], vue["modifiable"]), (None, True))
        api.enregistrer_auto_evaluation(self.livrable, json.dumps(DIX))
        self.assertEqual(api.mon_auto_evaluation(self.livrable)["niveaux"], DIX)
        with self.assertRaises(frappe.ValidationError):
            api.enregistrer_auto_evaluation(self.livrable, {"pertinence": 9})
        self.en_tant_que(B)  # non inscrit au cours
        with self.assertRaises(frappe.PermissionError):
            api.mon_auto_evaluation(self.livrable)
        with self.assertRaises(frappe.PermissionError):
            api.enregistrer_auto_evaluation(self.livrable, DIX)


class TestGating(CasApi):
    """Publication pendant que l'apprenant doit encore une relecture : rien de la note ne sort."""

    def publiee_sous_gating(self):
        self.en_relecture()
        self.relire(B, self.r_b)  # la copie de A passe au formateur ; A n'a pas encore relu B
        self.en_tant_que("Administrator")
        self.soumission = frappe.db.get_value("Copie OpenLab", self.a, "soumission")
        self.statut_avant = frappe.db.get_value(SOUMISSION, self.soumission, "status")
        self.en_tant_que(FORM)
        api.corriger(self.a, DIX)
        api.publier(self.a)
        self.en_tant_que("Administrator")

    def lms(self):
        return frappe.db.get_value(SOUMISSION, self.soumission, ["status", "comments"], as_dict=True)

    def test_publication_sous_gating_ne_divulgue_rien(self):
        self.publiee_sous_gating()
        lms = self.lms()
        self.assertEqual(lms.status, self.statut_avant)
        self.assertIn(f'href="/espace/retour/{self.a}"', lms.comments)
        for fuite in ("10/20", "Note", "réussi", "Pass"):
            self.assertNotIn(fuite, lms.comments)
            self.assertNotIn(fuite, self.notifier.call_args.args[1])
        self.assertEqual(frappe.db.get_value("Copie OpenLab", self.a, "lms_differe"), 1)

    def test_liberee_quand_les_relectures_sont_faites(self):
        self.publiee_sous_gating()
        self.file.reset_mock()
        self.relire(A, self.r_a)
        self.file.assert_any_call("openlab_academy.entrypoints.evaluation.liberer_notes", apprenant=A,
                                  enqueue_after_commit=True)
        self.en_tant_que("Administrator")
        evaluation.liberer_notes(A)
        lms = self.lms()
        self.assertEqual(lms.status, "Pass")
        self.assertIn("10/20", lms.comments)
        self.assertEqual(frappe.db.get_value("Copie OpenLab", self.a, "lms_differe"), 0)
        self.assertIn("10/20", self.notifier.call_args.args[1])
        self.assertIn("note libérée", self.actions(self.a))

    def test_une_seule_liberation_quand_deux_chemins_listent_la_copie(self):
        self.publiee_sous_gating()
        DepotRelecturesFrappe().dispenser(self.a)
        listees = DepotCopiesFrappe().copies_differees()  # l'échéancier a déjà listé la copie
        self.assertIn(self.a, listees)
        self.notifier.reset_mock()
        evaluation.liberer_notes(A)  # la tâche de la relecture passe avant lui
        cas = evaluation.liberateur()
        self.assertEqual([cas.executer(c) for c in listees if c == self.a], [False])
        self.assertEqual(self.actions(self.a).count("note libérée"), 1)
        self.assertEqual(self.notifier.call_count, 1)

    def test_file_indisponible_l_echeancier_prendra_le_relais(self):
        self.file.side_effect = ConnectionError("redis")
        with mock.patch.object(evaluation.frappe, "log_error") as consigne:
            evaluation.liberer_plus_tard(A)
        consigne.assert_called_once()

    def test_liberee_par_l_echeancier_apres_dispense(self):
        self.publiee_sous_gating()
        evaluation.traiter_echeances()
        self.assertEqual(self.lms().status, self.statut_avant)  # relecture encore due : rien ne bouge
        DepotRelecturesFrappe().dispenser(self.a)
        evaluation.traiter_echeances()
        self.assertEqual(self.lms().status, "Pass")


class TestDelegations(CasApi):
    def test_deleguer_ses_corrections_puis_revoquer(self):
        self.en_tant_que(FORM)
        nom = api.deleguer(DELEG, str(now_datetime()), str(add_days(now_datetime(), 3)))
        d = frappe.db.get_value("Delegation OpenLab", nom, ["titulaire", "delegataire", "revoquee"], as_dict=True)
        self.assertEqual((d.titulaire, d.delegataire, d.revoquee), (FORM, DELEG, 0))
        self.en_tant_que(AUTRE)
        with self.assertRaises(frappe.PermissionError):
            api.revoquer(nom)
        self.en_tant_que(FORM)
        api.revoquer(nom)
        self.assertEqual(frappe.db.get_value("Delegation OpenLab", nom, "revoquee"), 1)
        self.en_tant_que("Administrator")
        actions = frappe.get_all(JOURNAL, {"copie": f"délégation:{nom}"}, pluck="action", order_by="creation")
        self.assertEqual(actions, ["délégation créée", "délégation révoquée"])

    def test_pour_autrui_reserve_aux_superviseurs(self):
        fin = str(add_days(now_datetime(), 3))
        self.en_tant_que(AUTRE)
        with self.assertRaises(frappe.PermissionError):
            api.deleguer(DELEG, str(now_datetime()), fin, titulaire=FORM)
        for superviseur in ("Administrator", RESP):
            self.en_tant_que(superviseur)
            self.assertTrue(api.deleguer(DELEG, str(now_datetime()), fin, titulaire=FORM))

    def test_apprenant_ni_delegue_ni_delegataire(self):
        fin = str(add_days(now_datetime(), 3))
        self.en_tant_que(A)
        with self.assertRaises(frappe.PermissionError):
            api.deleguer(DELEG, str(now_datetime()), fin)
        self.en_tant_que(FORM)
        with self.assertRaises(frappe.ValidationError):
            api.deleguer(A, str(now_datetime()), fin)
        for debut in ("pas une date", ""):
            with self.subTest(debut=debut), self.assertRaises(frappe.ValidationError):
                api.deleguer(DELEG, debut, fin)

    def test_delegation_par_cohorte_et_exercice(self):
        (copie,) = self.a_corriger(A)
        self.en_tant_que(FORM)
        api.deleguer(DELEG, str(add_days(now_datetime(), -1)), str(add_days(now_datetime(), 3)),
                     cohorte=self.cohorte, exercice=self.livrable)
        self.en_tant_que(DELEG)
        self.assertEqual([c["copie"] for c in api.file_correction()["copies"]], [copie])
        api.corriger(copie, DIX)


class TestAdaptateur(CasApi):
    def test_texte_lisible_jamais_en_html(self):
        (copie,) = self.a_corriger(A)
        frappe.db.set_value("Copie OpenLab", copie, {"contenu": "<p>Mon <b>texte</b> &amp; plus</p>", "source_url": ""})
        self.assertEqual(self.depot.texte_lisible(copie), "Mon texte & plus")
        frappe.db.set_value("Copie OpenLab", copie, {"contenu": "if a < b: <code>", "source_url": URL})
        self.assertEqual(self.depot.texte_lisible(copie), "if a < b: <code>")  # instantané de dépôt : brut

    def test_publier_sans_soumission_lms_fige_la_note(self):
        (copie,) = self.a_corriger(A)
        frappe.db.set_value("Copie OpenLab", copie, "soumission", "disparue")
        self.depot.publier(copie, 12.0, 20, True, "Note : 12/20.", "/espace/retour/x", False)
        self.assertEqual(self.depot.resultat(copie), (12.0, 20, True))


class TestGardes(CasApi):
    APPELS = {
        "mes_relectures": (), "relecture": ("R",), "enregistrer_relecture": ("R", "{}", "{}"),
        "mon_auto_evaluation": ("E",), "enregistrer_auto_evaluation": ("E", "{}"), "mon_retour": ("C",),
        "file_correction": (), "copie_a_corriger": ("C",), "corriger": ("C", "{}"), "valider_lot": ("[]",),
        "publier": ("C",), "deleguer": ("D", "2026-01-01", "2026-01-02"), "revoquer": ("D",), "fiabilite_ia": (),
    }

    def test_visiteur_refuse_partout(self):
        self.en_tant_que("Guest")
        for nom, args in self.APPELS.items():
            with self.subTest(point=nom), self.assertRaises(frappe.PermissionError):
                getattr(api, nom)(*args)

    def test_debit_par_utilisateur_sur_chaque_point(self):
        """Même adresse, deux comptes : chacun son compteur ; au-delà de la limite -> 429 (limites réduites à 3)."""
        requete = mock.Mock(method="POST")
        with mock.patch.object(frappe.local, "request", requete, create=True), \
                mock.patch.object(frappe.local, "request_ip", "10.0.0.7", create=True), \
                mock.patch.dict(api.LIMITES, dict.fromkeys(api.LIMITES, 3)):
            for nom, limite in api.LIMITES.items():
                for qui in (A, B):
                    frappe.cache.delete_value(api.cle_debit(nom, qui), make_keys=False)
                self.en_tant_que(A)
                with self.subTest(point=nom):
                    for _ in range(limite):
                        try:
                            getattr(api, nom)(*self.APPELS[nom])
                        except (frappe.PermissionError, frappe.ValidationError):
                            pass
                    with self.assertRaises(frappe.TooManyRequestsError):
                        getattr(api, nom)(*self.APPELS[nom])
                    self.en_tant_que(B)
                    try:
                        getattr(api, nom)(*self.APPELS[nom])
                    except (frappe.PermissionError, frappe.ValidationError):
                        pass
                frappe.local.message_log = []
        self.assertEqual(set(api.LIMITES), set(self.APPELS))  # lectures comprises

    def test_debit_non_compte_hors_requete(self):
        self.en_tant_que(A)
        frappe.cache.delete_value(api.cle_debit("publier", A), make_keys=False)
        with self.assertRaises(frappe.PermissionError):
            api.publier("C")
        self.assertFalse(frappe.cache.get(api.cle_debit("publier", A)))


class TestFileCorrection(CasApi):
    def test_apprenant_file_vide_sans_controle_par_copie(self):
        self.a_corriger(A, B)
        self.en_tant_que(A)
        with mock.patch.object(ConsulterCorrection, "_habilitation") as habilitation, \
                mock.patch.object(DepotCopiesFrappe, "titulaires") as titulaires, \
                mock.patch.object(frappe.db, "sql", wraps=frappe.db.sql) as requetes:
            self.assertEqual(api.file_correction(), {"copies": [], "lots": []})
        habilitation.assert_not_called()
        titulaires.assert_not_called()
        sur_les_copies = [c for c in requetes.call_args_list
                          if any(t in str(c.args[0]) for t in ("Copie OpenLab", "Proposition OpenLab", "Journal Note"))]
        self.assertEqual(len(sur_les_copies), 1)  # la seule liste préfiltrée, vide : aucune lecture par copie

    def test_destinataire_de_l_escalade(self):
        (copie,) = self.a_corriger(A)
        frappe.db.set_value("Copie OpenLab", copie, "escalade_a", AUTRE)
        self.en_tant_que(AUTRE)
        self.assertEqual([c["copie"] for c in api.file_correction()["copies"]], [copie])

    def test_formateur_du_cours_et_formateur_par_defaut(self):
        self.soumettre(self.livrable, A)  # sans cohorte : titulaires du cours, sinon formateur des réglages
        copie = self.copie_de(A)
        self.depot.changer_statut(copie, Statut.A_CORRIGER, "formateur", None)
        cours = frappe.get_doc("LMS Course", self.cours)
        cours.append("instructors", {"instructor": AUTRE})
        cours.save(ignore_permissions=True)
        self.en_tant_que(AUTRE)
        self.assertEqual([c["copie"] for c in api.file_correction()["copies"]], [copie])
        self.en_tant_que("Administrator")
        frappe.db.set_single_value("Reglages OpenLab Academy", "formateur", DELEG)
        self.en_tant_que(DELEG)
        self.assertEqual(api.file_correction()["copies"], [])  # le cours a un formateur : DELEG n'est pas titulaire
