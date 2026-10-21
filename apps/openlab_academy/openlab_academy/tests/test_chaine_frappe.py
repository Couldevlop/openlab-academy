"""Chaîne de correction sur de vraies soumissions : adaptateurs, tâches de fond, échéances horaires."""
import datetime
import json
from unittest import mock

import frappe
import requests
from frappe.utils import now_datetime

from openlab_academy import hooks
from openlab_academy.application.chaine import SYSTEME, Etat, FaireAvancer
from openlab_academy.application.pairs import EnregistrerRelecture, RelectureRefusee, StatutRelecture
from openlab_academy.domain.cohorte import Cohorte
from openlab_academy.domain.copie import Source, Statut
from openlab_academy.domain.reglages import Reglages
from openlab_academy.entrypoints import evaluation
from openlab_academy.infrastructure import journal_frappe
from openlab_academy.openlab_academy.doctype.copie_openlab import copie_openlab
from openlab_academy.openlab_academy.doctype.relecture_pair_openlab import relecture_pair_openlab
from openlab_academy.infrastructure.depot_cohortes_frappe import DepotCohortesFrappe
from openlab_academy.infrastructure.depot_relectures_frappe import DepotRelecturesFrappe
from openlab_academy.infrastructure.instantane_depot import InstantaneDepot
from openlab_academy.infrastructure.reglages_evaluation_frappe import REGLAGES, SourceReglagesFrappe
from openlab_academy.tests.test_depot_copies_frappe import A, B, Base
from openlab_academy.tests.http_simule import SHA, Reponse, github
from openlab_academy.tests.test_reglages_evaluation_frappe import etapes_formateur

COPIE = "Copie OpenLab"
JOURNAL = "Journal Note OpenLab"
CONTROLER = "openlab_academy.entrypoints.evaluation.controler"


class Cas(Base):
    def setUp(self):
        super().setUp()
        self.file = mock.patch.object(evaluation.frappe, "enqueue").start()
        self.commit = mock.patch.object(frappe.local.db, "commit").start()  # la tâche horaire valide par élément
        self.addCleanup(mock.patch.stopall)
        self.relectures = DepotRelecturesFrappe()

    def lot(self, formateur="Administrator", *membres):
        lot = DepotCohortesFrappe(formateur).creer(Cohorte.pilote(self.p, datetime.date(2026, 11, 2),
                                                                  Reglages().rythme("standard"), Reglages()))
        for membre in membres:
            frappe.get_doc({"doctype": "LMS Batch Enrollment", "batch": lot, "member": membre}).insert(
                ignore_permissions=True)
        return lot

    def copie_de(self, membre=A, devoir=None):
        return frappe.get_all(COPIE, {"apprenant": membre, "exercice": devoir or self.livrable}, pluck="name",
                              order_by="version desc", limit=1)[0]

    def ligne(self, copie_id):
        return frappe.db.get_value(COPIE, copie_id, ["statut", "etape_courante", "echeance", "escalade_a",
                                                     "relectures_dispensees"], as_dict=True)

    def actions(self, copie_id, acteur=SYSTEME):
        return frappe.get_all(JOURNAL, {"copie": copie_id, "acteur": acteur}, pluck="action", order_by="creation")

    def en_relecture(self):
        """A et B, dans la même cohorte de deux, ont rendu le livrable et passé les contrôles."""
        self.cohorte = self.lot("Administrator", A, B)
        self.soumettre(self.livrable, A)
        self.soumettre(self.livrable, B, "https://github.com/kone/livrable")
        self.a, self.b = self.copie_de(A), self.copie_de(B)
        for copie in (self.a, self.b):
            evaluation.controler(copie)


class TestDemarrage(Cas):
    def test_instantane_regle_par_la_console_et_pris_en_tache_de_fond(self):
        for champ, valeur in (("instantane_fichiers_max", 3), ("instantane_delai_s", 4),
                              ("instantane_budget_tache_s", 30), ("ia_plafond_caracteres", 5000)):
            frappe.db.set_single_value(REGLAGES, champ, valeur)
        with mock.patch.object(evaluation, "InstantaneDepot", wraps=InstantaneDepot) as instantane:
            self.soumettre(self.livrable, instantane=False)
            instantane.assert_not_called()  # le rendu n'attend jamais le réseau
            copie = self.copie_de()
            evaluation.controler(copie)  # les contrôles attendent l'instantané
            self.assertEqual(self.ligne(copie).etape_courante, "controles")
            evaluation.instantaner(copie)
        tache = instantane.call_args.kwargs
        self.assertEqual({k: tache[k] for k in ("plafond", "fichiers_max", "delai_s", "budget_s")},
                         {"plafond": 5000, "fichiers_max": 3, "delai_s": 4, "budget_s": 30})
        self.assertEqual(frappe.db.get_value(COPIE, copie, "instantane"), "indisponible")  # hors ligne
        self.assertEqual(self.actions(copie)[-1], "instantané indisponible")
        self.assertEqual(self.file.call_args_list[-1], mock.call(CONTROLER, copie_id=copie, enqueue_after_commit=True))

    def test_console_illisible_l_instantane_ne_reste_pas_en_attente(self):
        self.soumettre(self.livrable, instantane=False)
        copie = self.copie_de()
        with mock.patch.object(evaluation.reglages_evaluation_frappe, "jeton_depots", side_effect=RuntimeError):
            evaluation.instantaner(copie)
        self.assertEqual(frappe.db.get_value(COPIE, copie, "instantane"), "indisponible")

    def test_accuse_de_depot_horodate_en_utc(self):
        avant = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None, microsecond=0)
        self.soumettre(self.livrable, instantane=False)
        copie = self.copie_de()
        ligne = frappe.db.get_value(COPIE, copie, ["depose_le", "signature", "instantane"], as_dict=True)
        self.assertEqual(ligne.instantane, "en_cours")
        self.assertLessEqual(avant, ligne.depose_le)
        self.assertLessEqual(ligne.depose_le, avant + datetime.timedelta(minutes=1))
        accuse = frappe.get_all(JOURNAL, {"copie": copie, "action": "accusé de dépôt"}, ["acteur", "apres"])[0]
        self.assertEqual(accuse.acteur, A)
        self.assertEqual(json.loads(accuse.apres), {"depose_le": f"{ligne.depose_le:%Y-%m-%dT%H:%M:%S}Z",
                                                    "empreinte": ligne.signature, "algorithme": "SHA-256"})

    def test_rendus_rapproches_seul_le_dernier_est_photographie(self):
        frappe.db.set_single_value(REGLAGES, "remise_regroupement_s", 30)
        self.soumettre(self.livrable, instantane=False)
        ancienne = self.copie_de()
        s = frappe.get_doc("LMS Assignment Submission", {"member": A, "assignment": self.livrable})
        s.answer = "https://github.com/aya/livrable-v2"
        s.save(ignore_permissions=True)
        derniere = self.copie_de()
        self.soumettre(self.projet, instantane=False)
        projet = self.copie_de(devoir=self.projet)
        maintenant = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
        for copie, age in ((ancienne, 120), (derniere, 60), (projet, 5)):
            frappe.db.set_value(COPIE, copie, "depose_le", maintenant - datetime.timedelta(seconds=age))
        self.file.reset_mock()
        evaluation.instantaner_rendus()
        self.file.assert_called_once_with("openlab_academy.entrypoints.evaluation.instantaner", copie_id=derniere,
                                          queue="long", timeout=60 + evaluation.MARGE_S,
                                          job_id=f"openlab_instantane:{derniere}", deduplicate=True)

    def test_file_indisponible_la_minute_suivante_reprend(self):
        self.soumettre(self.livrable, instantane=False)
        frappe.db.set_single_value(REGLAGES, "remise_regroupement_s", 0)
        self.file.side_effect = RuntimeError("redis")
        with mock.patch.object(evaluation.frappe, "log_error") as consigne:
            evaluation.instantaner_rendus()
        consigne.assert_called_once()

    def test_debit_de_rendus_depasse_le_rendu_lms_est_refuse(self):
        frappe.db.set_single_value(REGLAGES, "remise_par_heure", 1)
        self.soumettre(self.livrable, instantane=False)
        with self.assertRaises(frappe.TooManyRequestsError):
            self.soumettre(self.projet, instantane=False)
        self.assertFalse(frappe.db.exists(COPIE, {"apprenant": A, "exercice": self.projet}))
        frappe.local.message_log = []

    def test_rendu_demarre_la_chaine(self):
        self.soumettre(self.livrable, instantane=False)
        copie = self.copie_de()
        self.assertEqual((self.ligne(copie).statut, self.ligne(copie).etape_courante), ("rendue", "controles"))
        self.file.assert_called_once_with(CONTROLER, copie_id=copie, enqueue_after_commit=True)
        self.assertEqual(self.actions(copie), ["étape suivante"])

    def test_demarrage_en_erreur_garde_la_copie_a_sa_premiere_etape(self):
        with mock.patch.object(FaireAvancer, "demarrer", side_effect=RuntimeError("panne")), \
                mock.patch.object(evaluation.frappe, "log_error") as consigne:
            self.soumettre(self.livrable)
        consigne.assert_called_once()
        ligne = self.ligne(self.copie_de())
        self.assertEqual((ligne.statut, ligne.etape_courante), ("rendue", "auto_evaluation"))
        self.assertIsNotNone(ligne.echeance)  # l'échéance horaire la fera avancer

    def test_surcharge_devenue_invalide_la_copie_est_creee(self):
        reglages = frappe.get_single("Reglages Evaluation OpenLab")
        reglages.publication_provisoire = 1
        reglages.save(ignore_permissions=True)
        frappe.get_doc({"doctype": "Surcharge Evaluation OpenLab", "exercice": self.livrable,
                        "etapes": etapes_formateur(expiration="publier_provisoire")}).insert()
        reglages = frappe.get_single("Reglages Evaluation OpenLab")
        reglages.publication_provisoire = 0  # la surcharge enregistrée devient dangereuse
        reglages.save(ignore_permissions=True)
        with mock.patch.object(evaluation.frappe, "log_error") as consigne:
            self.soumettre(self.livrable)
        consigne.assert_not_called()
        copie = self.copie_de()
        self.assertEqual(self.ligne(copie).etape_courante, "controles")  # chaîne du type livrable
        self.assertIn("chaîne invalide : chaîne du type appliquée", self.actions(copie))

    def test_tache_inconnue_refusee(self):
        with self.assertRaisesRegex(ValueError, "tâche inconnue"):
            evaluation.file("supprimer", "C1")

    def test_file_indisponible_ne_bloque_pas(self):
        self.file.side_effect = ConnectionError("redis")
        with mock.patch.object(evaluation.frappe, "log_error") as consigne:
            evaluation.file("controler", "C1")
        consigne.assert_called_once()

    def test_etapes_non_disponibles_font_avancer(self):
        self.soumettre(self.livrable)  # sans cohorte : pas de pairs
        copie = self.copie_de()
        evaluation.controler(copie)
        self.assertEqual((self.ligne(copie).statut, self.ligne(copie).etape_courante), ("controlee", "ia"))
        self.file.assert_called_with("openlab_academy.entrypoints.evaluation.pre_corriger", copie_id=copie,
                                     enqueue_after_commit=True, queue="long", timeout=10 * 60 + evaluation.MARGE_S)
        evaluation.controler(copie)  # signal périmé : ignoré
        evaluation.pre_corriger(copie)
        self.assertEqual((self.ligne(copie).statut, self.ligne(copie).etape_courante), ("a_corriger", "formateur"))
        self.assertEqual(self.actions(copie), ["étape suivante", "instantané indisponible", "contrôles non disponibles",
                                               "étape suivante", "pré-correction non disponible", "pairs sautés",
                                               "étape suivante"])

    def test_controles_conformes_sur_un_depot_public(self):
        self.http.side_effect = github()
        self.soumettre(self.livrable)
        copie = self.copie_de()
        evaluation.controler(copie)
        self.assertEqual((self.ligne(copie).statut, self.ligne(copie).etape_courante), ("controlee", "ia"))
        self.assertEqual(self.actions(copie), ["étape suivante", "instantané pris", "contrôles conformes",
                                               "étape suivante"])
        self.assertEqual([p.source for p in self.depot.propositions(copie)], [Source.CONTROLES])

    def test_jeton_des_depots_de_la_console_utilise(self):
        doc = frappe.get_single("Reglages Evaluation OpenLab")
        doc.jeton_depots = "ghp_console"
        doc.save(ignore_permissions=True)
        self.http.side_effect = github()
        self.soumettre(self.livrable)
        evaluation.controler(self.copie_de())
        self.assertTrue(self.http.call_args_list)
        self.assertTrue(all(a.kwargs["headers"]["Authorization"] == "Bearer ghp_console"
                            for a in self.http.call_args_list))
        self.assertNotIn("ghp_console", repr(frappe.get_all(JOURNAL, fields=["avant", "apres"])))

    def test_depot_prive_renvoie_la_copie_et_previent_l_apprenant(self):
        self.soumettre(self.livrable)
        copie = self.copie_de()
        self.http.side_effect = github(prive=True)
        evaluation.controler(copie)
        ligne = self.ligne(copie)
        self.assertEqual((ligne.statut, ligne.etape_courante, ligne.echeance), ("renvoyee", "", None))
        self.assertEqual(self.actions(copie)[-1], "copie renvoyée")
        sujets = frappe.get_all("Notification Log", {"for_user": A}, pluck="subject")
        self.assertTrue(any("dépôt introuvable ou privé" in s for s in sujets))

    def test_copie_texte_trop_courte_renvoyee(self):
        with mock.patch("openlab_academy.entrypoints.lms.avant_soumission_devoir"):  # verrou testé ailleurs
            self.soumettre(self.cas, reponse="Trop court.")
        copie = self.copie_de(devoir=self.cas)
        evaluation.controler(copie)
        self.assertEqual(self.ligne(copie).statut, "renvoyee")
        self.http.assert_not_called()

    def configurer_ia(self, cle="sk-console-789"):
        doc = frappe.get_single("Reglages Evaluation OpenLab")
        doc.update({"ia_url": "https://ia.openlab.ci", "ia_modele_texte": "texte-8b", "ia_modele_code": "code-8b",
                    "ia_delai_minutes": 3, "cle_ia": cle})
        doc.save(ignore_permissions=True)

    def a_l_etape_ia(self):
        """Le rendu n'attend pas le réseau ; l'instantané, pris en tâche de fond, fige le dépôt avant les contrôles."""
        self.soumettre(self.livrable, instantane=False)  # sans cohorte : pas de pairs
        copie = self.copie_de()
        self.assertEqual((self.depot.contenu(copie).texte, self.depot.contenu(copie).instantane.value), ("", "en_cours"))
        self.http.side_effect = github(fichiers={"README.md": "Le tableau de bord hebdomadaire réduit les ruptures."})
        evaluation.instantaner(copie)
        evaluation.controler(copie)
        self.assertEqual(self.depot.contenu(copie).commit, SHA)
        self.assertIn("tableau de bord hebdomadaire", self.depot.contenu(copie).texte)
        self.assertEqual(self.ligne(copie).etape_courante, "ia")
        return copie

    def test_secrets_illisibles_les_taches_avancent_sans_exception(self):
        self.soumettre(self.livrable)
        copie = self.copie_de()
        source = evaluation.reglages_evaluation_frappe
        with mock.patch.object(source, "jeton_depots", side_effect=RuntimeError("secret")), \
                mock.patch.object(source, "cle_ia", side_effect=RuntimeError("secret")):
            evaluation.controler(copie)
            self.assertEqual(self.ligne(copie).etape_courante, "ia")
            evaluation.pre_corriger(copie)
        self.assertEqual(self.ligne(copie).etape_courante, "formateur")
        self.assertEqual(self.actions(copie), ["étape suivante", "instantané indisponible", "contrôles non disponibles",
                                               "étape suivante", "pré-correction non disponible", "pairs sautés",
                                               "étape suivante"])

    def test_pre_correction_par_le_service_de_la_console(self):
        self.configurer_ia()
        copie = self.a_l_etape_ia()
        grille = self.depot.grille(copie)
        brut = json.dumps({"criteres": {c.code: {"niveau": 1, "justification": "ok", "citation": "tableau de bord"}
                                        for c in grille.criteres}, "confiance": 0.8})
        reponse = Reponse(json={"choices": [{"message": {"content": brut}}]})
        with mock.patch("requests.post", return_value=reponse) as post:
            evaluation.pre_corriger(copie)
        (url,), options = post.call_args
        self.assertEqual((url, options["json"]["model"], options["timeout"]),
                         ("https://ia.openlab.ci/v1/chat/completions", "code-8b", 180))
        self.assertEqual(options["headers"]["Authorization"], "Bearer sk-console-789")
        (p,) = [p for p in self.depot.propositions(copie) if p.source == Source.IA]
        self.assertEqual(p.confiance, 0.8)
        self.assertEqual(self.ligne(copie).etape_courante, "formateur")
        self.assertIn("pré-correction proposée", self.actions(copie))

    def test_service_en_panne_cle_jamais_consignee(self):
        self.configurer_ia()
        copie = self.a_l_etape_ia()
        panne = requests.ConnectionError("Authorization: Bearer sk-console-789")
        with mock.patch("requests.post", side_effect=panne), \
                mock.patch.object(evaluation.frappe, "log_error") as consigne:
            evaluation.pre_corriger(copie)
        consigne.assert_not_called()
        self.assertEqual(self.ligne(copie).etape_courante, "formateur")
        self.assertNotIn("sk-console-789", repr(frappe.get_all(JOURNAL, {"copie": copie}, ["action", "avant", "apres"])))
        self.assertIn("pré-correction non disponible", self.actions(copie))

    def test_isoler_annule_les_ecritures_de_l_action_en_erreur(self):
        self.soumettre(self.livrable)
        copie = self.copie_de()

        def action():
            frappe.db.set_value(COPIE, copie, "etape_courante", "ia")
            raise RuntimeError("panne")

        with mock.patch.object(evaluation.frappe, "log_error") as consigne:
            evaluation.isoler(action)
        consigne.assert_called_once()
        self.assertEqual(self.ligne(copie).etape_courante, "controles")


class TestPairsFrappe(Cas):
    def test_cohorte_de_deux_se_relit_et_avance(self):
        self.en_relecture()
        self.assertEqual(self.relectures.taille_cohorte(self.cohorte), 2)
        self.assertEqual(self.relectures.taille_cohorte(""), 0)
        self.assertEqual([c.id for c in self.relectures.copies_rendues(self.livrable, self.cohorte)], [self.a, self.b])
        relectures = self.relectures.relectures(self.livrable, self.cohorte)
        self.assertEqual({(r.copie, r.relecteur) for r in relectures}, {(self.a, B), (self.b, A)})
        self.assertEqual(self.ligne(self.a).statut, "en_relecture")
        etat = self.depot.etat(self.a)
        self.assertEqual(etat.butoir, etat.echeance + datetime.timedelta(days=4))  # 72 h, plafond de 7 jours
        self.assertEqual(self.relectures.echeances([self.a, self.b]), {self.a: etat.echeance,
                                                                       self.b: self.depot.etat(self.b).echeance})
        b_relit_a = next(r for r in relectures if r.copie == self.a)
        self.assertEqual(self.relectures.relecture(b_relit_a.id), b_relit_a)
        self.assertIsNone(self.relectures.relecture("inexistante"))
        uc = EnregistrerRelecture(evaluation.DepotCopiesFrappe(), self.relectures, evaluation.avanceur(),
                                  journal_frappe.journaliser)
        codes = [c.code for c in self.depot.grille(self.a).criteres]
        uc.executer(B, b_relit_a.id, {c: 1 for c in codes}, {c: "Argumenté." for c in codes})
        (p,) = [p for p in self.depot.propositions(self.a) if p.source == Source.PAIR]
        self.assertEqual((p.auteur, p.niveaux), (B, {c: 1 for c in codes}))
        self.assertEqual(self.relectures.relecture(b_relit_a.id).statut, StatutRelecture.FAITE)
        self.assertEqual((self.ligne(self.a).statut, self.ligne(self.a).etape_courante), ("a_corriger", "formateur"))
        self.assertIn("relecture", self.actions(self.a, acteur=B))

    def test_version_courante_seule_dans_le_vivier(self):
        self.en_relecture()
        s = frappe.get_doc("LMS Assignment Submission", {"member": A, "assignment": self.livrable})
        s.answer = "https://github.com/aya/livrable-v2"
        s.save(ignore_permissions=True)
        v2 = self.copie_de(A)
        self.assertNotEqual(v2, self.a)
        self.assertEqual([c.id for c in self.relectures.copies_rendues(self.livrable, self.cohorte)], [self.b, v2])

    def test_relectures_echues_et_dispense(self):
        self.en_relecture()
        self.assertEqual(self.relectures.relectures_echues(now_datetime()), [])
        plus_tard = now_datetime() + datetime.timedelta(days=4)
        echues = self.relectures.relectures_echues(plus_tard)
        self.assertEqual(len(echues), 2)
        self.relectures.changer_statut_relecture(echues[0].id, StatutRelecture.ANNULEE)
        self.assertEqual(len(self.relectures.relectures_echues(plus_tard)), 1)
        sans_delai = frappe.get_doc({"doctype": "Relecture Pair OpenLab", "copie": self.a, "relecteur": A}).insert(
            ignore_permissions=True).name
        self.assertIsNone(self.relectures.relecture(sans_delai).echeance)
        self.assertNotIn(sans_delai, [r.id for r in self.relectures.relectures_echues(plus_tard)])
        self.relectures.dispenser(self.a)
        self.assertEqual(self.ligne(self.a).relectures_dispensees, 1)

    def test_traiter_echeances_fait_avancer_la_chaine(self):
        self.en_relecture()
        passe = now_datetime() - datetime.timedelta(hours=1)
        frappe.db.set_value("Relecture Pair OpenLab", {"copie": self.a}, "echeance", passe)
        frappe.db.set_value(COPIE, self.a, "echeance", passe)
        evaluation.traiter_echeances()
        # premier dépassement : rappel à B, délai prolongé, la copie de A attend
        relecture = frappe.get_doc("Relecture Pair OpenLab", {"copie": self.a})
        self.assertEqual((relecture.statut, relecture.rappel), ("à_faire", 1))
        self.assertGreater(relecture.echeance, now_datetime())
        (note,) = frappe.get_all("Notification Log", {"for_user": B, "subject": ["like", "Rappel%"]},
                                 ["subject", "type"])
        self.assertEqual(note.type, "Alert")
        self.assertEqual(self.ligne(self.a).etape_courante, "pairs")
        self.assertEqual(self.actions(self.a)[-2:], ["rappel de relecture", "attente des relectures"])
        frappe.db.set_value("Relecture Pair OpenLab", relecture.name, "echeance", passe)
        frappe.db.set_value(COPIE, self.a, "echeance", passe)
        evaluation.traiter_echeances()
        # personne d'autre dans la cohorte : la relecture est annulée, B dispensé, la copie de A avance
        self.assertEqual(frappe.db.get_value("Relecture Pair OpenLab", {"copie": self.a}, "statut"), "annulée")
        self.assertEqual(self.ligne(self.b).relectures_dispensees, 1)
        self.assertEqual(self.ligne(self.a).etape_courante, "formateur")
        self.assertEqual(self.actions(self.a)[-4:], ["relecture annulée", "passer",
                                                     "pairs clos : relectures insuffisantes", "étape suivante"])
        self.assertEqual(self.ligne(self.b).etape_courante, "pairs")

    def test_double_envoi_d_une_relecture_enregistre_une_fois(self):
        self.en_relecture()
        (relecture,) = [r for r in self.relectures.relectures(self.livrable, self.cohorte) if r.copie == self.a]
        codes = [c.code for c in self.depot.grille(self.a).criteres]
        uc = EnregistrerRelecture(evaluation.DepotCopiesFrappe(), self.relectures, evaluation.avanceur())
        uc.executer(B, relecture.id, {c: 1 for c in codes}, {c: "Argumenté." for c in codes})
        with self.assertRaises(RelectureRefusee):
            uc.executer(B, relecture.id, {c: 1 for c in codes}, {c: "Argumenté." for c in codes})
        self.assertEqual(len([p for p in self.depot.propositions(self.a) if p.source == Source.PAIR]), 1)

    def test_paire_unique_en_base(self):
        self.en_relecture()
        echeance = now_datetime()
        self.assertIsNone(self.relectures.attribuer(self.a, B, echeance))  # B relit déjà la copie de A
        self.assertEqual(frappe.db.count("Relecture Pair OpenLab", {"copie": self.a, "relecteur": B}), 1)
        self.assertEqual(self.relectures.verrouiller_relecture("inexistante"), None)
        # insérée entre la vérification et l'insertion : l'unicité en base tranche, sans message à l'écran
        frappe.msgprint("message antérieur")
        with mock.patch.object(frappe.local.db, "exists", return_value=False):
            self.assertIsNone(self.relectures.attribuer(self.a, B, echeance))
        self.assertEqual(len(frappe.local.message_log), 1)  # seul le message d'unicité est retiré
        self.assertIn("message antérieur", str(frappe.local.message_log[0]))
        frappe.local.message_log.clear()
        self.assertEqual(frappe.db.count("Relecture Pair OpenLab", {"copie": self.a, "relecteur": B}), 1)
        relecture_pair_openlab.on_doctype_update()  # idempotent : la contrainte existe déjà
        self.assertTrue(frappe.db.sql("""select 1 from information_schema.TABLE_CONSTRAINTS
            where table_name='tabRelecture Pair OpenLab' and CONSTRAINT_NAME='unique_copie_relecteur'"""))

    def test_pre_correction_pendant_les_pairs_consignee_sans_avancer(self):
        self.en_relecture()
        evaluation.pre_corriger(self.a)
        self.assertEqual(self.ligne(self.a).etape_courante, "pairs")
        self.assertEqual(self.actions(self.a)[-1], "pré-correction non disponible")
        frappe.db.set_value(COPIE, self.a, "statut", "publiee")
        evaluation.pre_corriger(self.a)  # après publication : plus rien n'est consigné
        self.assertEqual(self.actions(self.a).count("pré-correction non disponible"), 1)

    def test_version_remplacee_hors_echeances(self):
        self.en_relecture()
        s = frappe.get_doc("LMS Assignment Submission", {"member": A, "assignment": self.livrable})
        s.answer = "https://github.com/aya/livrable-v2"
        s.save(ignore_permissions=True)
        ligne = self.ligne(self.a)
        self.assertEqual((ligne.statut, ligne.etape_courante, ligne.echeance), ("remplacee", "", None))
        self.assertNotIn(self.a, self.depot.copies_echues(now_datetime() + datetime.timedelta(days=365)))
        self.depot.verrouiller(self.a)

    def test_annuler_ne_touche_jamais_une_relecture_faite(self):
        self.en_relecture()
        faite = frappe.db.get_value("Relecture Pair OpenLab", {"copie": self.a}, "name")
        self.relectures.changer_statut_relecture(faite, StatutRelecture.FAITE)
        a_faire = frappe.get_doc({"doctype": "Relecture Pair OpenLab", "copie": self.a, "relecteur": A}).insert(
            ignore_permissions=True).name
        self.depot.annuler_relectures(self.a)
        self.assertEqual(self.relectures.relecture(faite).statut, StatutRelecture.FAITE)
        self.assertEqual(self.relectures.relecture(a_faire).statut, StatutRelecture.ANNULEE)

    def test_lectures_verrouillantes(self):
        self.en_relecture()
        lire = frappe.local.db.get_value
        with mock.patch.object(frappe.local.db, "get_value", side_effect=lire) as lecture:
            v = self.depot.verrouiller(self.a)
        self.assertTrue(lecture.call_args.kwargs["for_update"])
        self.assertEqual((v.copie.id, v.copie.statut, v.etat.etape), (self.a, Statut.EN_RELECTURE, "pairs"))
        lire_tout = frappe.local.db.get_values
        with mock.patch.object(frappe.local.db, "get_values", side_effect=lire_tout) as lecture:
            (r,) = self.relectures.relectures_copie(self.a)
        self.assertTrue(lecture.call_args.kwargs["for_update"])
        self.assertEqual((r.copie, r.relecteur), (self.a, B))

    def requetes(self, lecture):
        sql = frappe.local.db.sql
        with mock.patch.object(frappe.local.db, "sql", side_effect=sql) as requete:
            resultat = lecture()
        return resultat, " ".join(str(c.args[0]).lower() for c in requete.call_args_list)

    def test_lectures_verrouillantes_apres_le_verrou_de_la_copie(self):
        self.en_relecture()
        soumission = self.depot.contenu(self.a).soumission
        for lecture in (lambda v: self.depot.propositions(self.a, verrouillee=v),
                        lambda v: self.relectures.relectures(self.livrable, self.cohorte, verrouillee=v),
                        lambda v: self.depot.version_courante(soumission, verrouillee=v)):
            libre, sql_libre = self.requetes(lambda: lecture(False))
            verrouillee, sql_verrou = self.requetes(lambda: lecture(True))
            with self.subTest(lecture=lecture):
                self.assertEqual(verrouillee, libre)
                self.assertIn("for update", sql_verrou)
                self.assertNotIn("for update", sql_libre)

    def test_version_unique_par_soumission(self):
        self.en_relecture()
        doc = frappe.get_doc(COPIE, self.a)
        double = frappe.copy_doc(doc)
        with self.assertRaises(frappe.UniqueValidationError):
            double.insert(ignore_permissions=True)
        copie_openlab.on_doctype_update()  # idempotent : la contrainte existe déjà
        self.assertTrue(frappe.db.sql("""select 1 from information_schema.TABLE_CONSTRAINTS
            where table_name='tabCopie OpenLab' and CONSTRAINT_NAME='unique_soumission_version'"""))

    def test_tache_horaire_valide_chaque_element(self):
        evaluation.unite(lambda: None)
        self.commit.assert_called_once()
        with mock.patch.object(frappe.local.db, "rollback") as annule, \
                mock.patch.object(evaluation.frappe, "log_error") as consigne:
            evaluation.unite(lambda: 1 / 0)
        annule.assert_called_once_with()
        consigne.assert_called_once()
        self.assertEqual(self.commit.call_count, 2)  # l'erreur consignée est validée elle aussi
        with mock.patch.object(evaluation, "TraiterEcheances") as traiter:
            evaluation.traiter_echeances()
        self.assertIs(traiter.call_args.args[6], evaluation.unite)

    def test_hooks_echeancier(self):
        self.assertEqual(hooks.scheduler_events["hourly"], ["openlab_academy.entrypoints.evaluation.traiter_echeances"])
        self.assertEqual(hooks.scheduler_events["cron"],
                         {"* * * * *": ["openlab_academy.entrypoints.evaluation.instantaner_rendus"]})


class TestDepotChaineFrappe(Cas):
    def test_etat_grille_et_echeances(self):
        self.soumettre(self.livrable)
        copie = self.copie_de()
        etat = self.depot.etat(copie)
        self.assertEqual(etat.etape, "controles")
        self.assertEqual(etat.escalade_a, "")
        self.assertEqual(self.depot.grille(copie).criteres[0].code, "pertinence")
        self.assertEqual(self.depot.copies_echues(now_datetime()), [])
        self.assertIn(copie, self.depot.copies_echues(now_datetime() + datetime.timedelta(hours=2)))
        echeance = datetime.datetime(2027, 1, 1, 9, 0)
        self.depot.escalader(copie, "Administrator", echeance)
        self.assertEqual(self.depot.etat(copie), Etat("controles", echeance, "Administrator"))
        self.depot.changer_statut(copie, Statut.A_CORRIGER, "formateur", None)
        self.assertEqual(self.depot.etat(copie).echeance, None)
        self.assertNotIn(copie, self.depot.copies_echues(echeance))

    def test_titulaires_de_la_cohorte_du_cours_ou_des_reglages(self):
        self.lot(B, A)
        self.soumettre(self.livrable)
        self.assertEqual(self.depot.titulaires(self.copie_de()), {B})  # formateurs de la cohorte
        self.soumettre(self.livrable, B)  # B hors cohorte : formateurs du cours
        sans_lot = self.copie_de(B)
        self.assertEqual(self.depot.titulaires(sans_lot), {"Administrator"})
        cours = frappe.db.get_value("LMS Assignment", self.livrable, "course")
        frappe.db.delete("Course Instructor", {"parent": cours, "parenttype": "LMS Course"})
        with mock.patch.object(frappe.db, "get_single_value", return_value=A):
            self.assertEqual(self.depot.titulaires(sans_lot), {A})  # formateur des réglages
        with mock.patch.object(frappe.db, "get_single_value", return_value=None):
            self.assertEqual(self.depot.titulaires(sans_lot), set())

    def equipe(self, *membres, **champs):
        return frappe.get_doc({"doctype": "Equipe Correction OpenLab", **champs,
                               "membres": [{"utilisateur": u, "role": r} for u, r in membres]}).insert()

    def test_equipe_de_la_copie(self):
        lot = self.lot("Administrator", A)
        self.soumettre(self.livrable)
        copie = self.copie_de()
        self.assertEqual(self.depot.equipe(copie).provenance["titulaires"], "formateurs LMS")
        cours = frappe.db.get_value("LMS Assignment", self.livrable, "course")
        self.equipe((B, "suppleant"), cours=cours, responsable="Administrator")
        self.equipe((A, "titulaire"), exercice=self.livrable)
        equipe = self.depot.equipe(copie)
        self.assertEqual((equipe.titulaires, equipe.suppleants, equipe.responsable), ((A,), (B,), "Administrator"))
        self.assertEqual(self.depot.titulaires(copie), {A})
        self.assertEqual(equipe.provenance, {"titulaires": f"exercice {self.livrable}",
                                             "suppleants": f"cours {cours}", "responsable": f"cours {cours}"})
        self.assertEqual(SourceReglagesFrappe().reglages().responsable_pedagogique, frappe.get_single(
            "Reglages Evaluation OpenLab").responsable_pedagogique or "")
        self.assertIsNotNone(lot)

    def test_formateur_echu_escalade(self):
        lot = self.lot("Administrator", A)
        inactives = [{"etape": e, "active": 0, "delai_heures": 0, "expiration": "passer"}
                     for e in ("auto_evaluation", "controles", "ia", "pairs", "jury")]
        frappe.get_doc({"doctype": "Surcharge Evaluation OpenLab", "cohorte": lot,
                        "etapes": inactives + etapes_formateur()}).insert()
        self.equipe((B, "suppleant"), cohorte=lot)
        self.soumettre(self.livrable)
        copie = self.copie_de()
        self.assertEqual(self.ligne(copie).etape_courante, "formateur")
        frappe.db.set_value(COPIE, copie, "echeance", now_datetime() - datetime.timedelta(minutes=1))
        evaluation.traiter_echeances()
        self.assertEqual(self.ligne(copie).escalade_a, B)
        (entree,) = frappe.get_all(JOURNAL, {"copie": copie, "action": "escalader"}, ["acteur", "avant", "apres"])
        self.assertEqual(entree.acteur, SYSTEME)
        self.assertIn("Administrator", entree.avant)
        (sujet,) = frappe.get_all("Notification Log", {"for_user": B, "subject": ["like", "Une copie vous est%"]},
                                  pluck="subject")
        self.assertIn(f"/espace/correcteur/{copie}", sujet)

    def test_suppleant_de_l_equipe_sans_toucher_la_chaine(self):
        lot = self.lot("Administrator", A)
        self.equipe((B, "suppleant"), cohorte=lot)
        self.soumettre(self.livrable)
        copie = self.copie_de()
        self.assertEqual(self.ligne(copie).etape_courante, "controles")  # chaîne du livrable inchangée
        self.depot.changer_statut(copie, Statut.A_CORRIGER, "formateur", now_datetime() - datetime.timedelta(minutes=1))
        evaluation.traiter_echeances()
        self.assertEqual(self.ligne(copie).escalade_a, B)
