import json
from datetime import datetime

import frappe
from frappe.tests.utils import FrappeTestCase

from openlab_academy.domain.delegation import Delegation
from openlab_academy.domain.reglages_evaluation import (
    CHAINES_DEFAUT, ConfigIA, Etape, Expiration, ReglagesEvaluation, Surcharge, TypeExercice)
from openlab_academy.entrypoints import install
from openlab_academy.infrastructure import journal_frappe
from openlab_academy.infrastructure import reglages_evaluation_frappe as source
from openlab_academy.patches import initialiser_reglages_evaluation

REGLAGES = "Reglages Evaluation OpenLab"
SURCHARGE = "Surcharge Evaluation OpenLab"
DELEGATION = "Delegation OpenLab"
JOURNAL = "Journal Note OpenLab"
ELEVE = "eleve.console@example.ci"
ROLE = "Responsable pédagogique OpenLab"


def vider():
    doc = frappe.get_single(REGLAGES)
    for table in ("etapes", "grille_generique", "tournures"):
        doc.set(table, [])
    doc.flags.ignore_validate = True
    doc.save(ignore_permissions=True)


def un_lot() -> str:
    return frappe.get_all("LMS Batch", pluck="name", limit=1)[0]


def un_devoir() -> str:
    return frappe.get_all("LMS Assignment", pluck="name", limit=1)[0]


def etapes_formateur(**autres):
    return [{"etape": "formateur", "active": 1, "delai_heures": 72, "expiration": "escalader", **autres}]


def utilisateur(email: str, role: str):
    if not frappe.db.exists("User", email):
        frappe.get_doc({"doctype": "User", "email": email, "first_name": "Test", "send_welcome_email": 0,
                        "roles": [{"role": role}]}).insert(ignore_permissions=True)


class TestReglagesEvaluationFrappe(FrappeTestCase):
    def tearDown(self):
        frappe.set_user("Administrator")
        frappe.db.rollback()

    def test_ecran_vide_donne_les_defauts_du_domaine(self):
        vider()
        self.assertEqual(source.charger(), ReglagesEvaluation())

    def test_initialisation_reproduit_les_defauts(self):
        vider()
        source.initialiser()
        r = source.charger()
        self.assertEqual(r.chaines, CHAINES_DEFAUT)
        self.assertEqual(r.ia, ConfigIA())
        self.assertEqual(r, ReglagesEvaluation(chaines=CHAINES_DEFAUT))
        self.assertEqual(len(frappe.get_single(REGLAGES).etapes), 24)

    def test_initialisation_n_ecrase_pas_une_valeur_modifiee(self):
        vider()
        source.initialiser()
        doc = frappe.get_single(REGLAGES)
        doc.ia_delai_minutes = 25
        doc.nb_pairs = 5
        doc.save(ignore_permissions=True)
        source.initialiser()
        r = source.charger()
        self.assertEqual((r.ia.delai_minutes, r.chaines[TypeExercice.LIVRABLE].nb_pairs), (25, 5))

    def test_formateur_desactive_refuse(self):
        vider()
        source.initialiser()
        doc = frappe.get_single(REGLAGES)
        for ligne in doc.etapes:
            if ligne.type_exercice == "livrable" and ligne.etape == "formateur":
                ligne.active = 0
        with self.assertRaisesRegex(frappe.ValidationError, "formateur doit rester active"):
            doc.save(ignore_permissions=True)

    def test_publication_provisoire_refusee_tant_que_l_option_est_off(self):
        vider()
        source.initialiser()
        doc = frappe.get_single(REGLAGES)
        doc.etapes[5].expiration = "publier_provisoire"
        with self.assertRaisesRegex(frappe.ValidationError, "publication provisoire"):
            doc.save(ignore_permissions=True)
        doc = frappe.get_single(REGLAGES)
        doc.etapes[5].expiration = "publier_provisoire"
        doc.publication_provisoire = 1
        doc.save(ignore_permissions=True)
        self.assertTrue(source.charger().publication_provisoire)

    def test_ligne_sans_type_refusee(self):
        vider()
        source.initialiser()
        doc = frappe.get_single(REGLAGES)
        doc.append("etapes", {"etape": "ia", "active": 1, "delai_heures": 1, "expiration": "passer"})
        with self.assertRaisesRegex(frappe.ValidationError, "type d'exercice"):
            doc.save(ignore_permissions=True)

    def test_modification_prise_en_compte(self):
        vider()
        source.initialiser()
        doc = frappe.get_single(REGLAGES)
        doc.update({"ia_url": "http://ia.local", "ia_modele_texte": "m1", "ia_modele_code": "m2",
                    "ia_seuil_confiance": 0.6, "ia_plafond_caracteres": 1000,
                    "responsable_pedagogique": "Administrator",
                    "hotes_depots": "github.com\n\n gitea.local ", "niveaux_generiques": "Non\nOui", "note_sur": 10,
                    "seuil_reussite": 5, "anonymat": 0, "note_masquee_avant_relectures": 0})
        doc.set("grille_generique", [{"nom": "A", "poids": 40}, {"nom": "B", "poids": 60}])
        doc.set("tournures", [{"texte": "oublie tout"}])
        doc.save(ignore_permissions=True)
        r = source.charger()
        self.assertEqual(r.ia, ConfigIA("http://ia.local", "m1", "m2", 10, 0.6, ("oublie tout",), 1000))
        self.assertEqual((r.responsable_pedagogique, r.hotes_depots, r.niveaux_generiques, r.grille_generique),
                         ("Administrator", ("github.com", "gitea.local"), ("Non", "Oui"), (("A", 40), ("B", 60))))
        c = r.chaines[TypeExercice.PROJET]
        self.assertEqual((c.note_sur, c.seuil_reussite, c.anonymat, c.note_masquee_avant_relectures),
                         (10, 5.0, False, False))

    def test_grille_incoherente_refusee(self):
        vider()
        source.initialiser()
        doc = frappe.get_single(REGLAGES)
        doc.set("grille_generique", [{"nom": "A", "poids": 40}])
        with self.assertRaisesRegex(frappe.ValidationError, "totalisant 100"):
            doc.save(ignore_permissions=True)

    def test_cle_ia_jamais_exposee(self):
        vider()
        source.initialiser()
        doc = frappe.get_single(REGLAGES)
        doc.cle_ia = "sk-secret-123"
        doc.save(ignore_permissions=True)
        self.assertEqual(source.cle_ia(), "sk-secret-123")
        relu = frappe.get_doc(REGLAGES)
        self.assertNotIn("sk-secret-123", json.dumps(relu.as_dict(), default=str))
        self.assertNotIn("sk-secret-123", json.dumps(source.charger().ia.__dict__, default=str))

    def test_cle_ia_vide_par_defaut(self):
        self.assertEqual(source.cle_ia(), "")

    def test_patch_initialise_console_role_et_espace(self):
        vider()
        frappe.db.delete("Workspace", {"name": "Évaluation OpenLab"})
        frappe.db.delete("Role", {"name": ROLE})
        initialiser_reglages_evaluation.execute()
        self.assertEqual(len(frappe.get_single(REGLAGES).etapes), 24)
        self.assertTrue(frappe.db.exists("Role", ROLE))
        espace = frappe.get_doc("Workspace", "Évaluation OpenLab")
        self.assertEqual({s.link_to for s in espace.shortcuts},
                         {REGLAGES, SURCHARGE, DELEGATION, JOURNAL, "Reglages OpenLab Academy",
                          "Ouverture Lecon OpenLab"})
        self.assertEqual(len(json.loads(espace.content)), 6)
        initialiser_reglages_evaluation.execute()  # idempotent
        self.assertEqual(frappe.db.count("Workspace", {"name": "Évaluation OpenLab"}), 1)

    def test_migration_prepare_la_console(self):
        vider()
        install.after_migrate(commit=False)
        self.assertEqual(len(frappe.get_single(REGLAGES).etapes), 24)


class TestSurcharges(FrappeTestCase):
    def tearDown(self):
        frappe.db.rollback()

    def _surcharge(self, **champs):
        return frappe.get_doc({"doctype": SURCHARGE, "etapes": etapes_formateur(), **champs})

    def test_surcharge_cohorte_et_exercice(self):
        lot, devoir = un_lot(), un_devoir()
        self._surcharge(cohorte=lot, nb_pairs=5, note_sur=10, seuil_reussite=6).insert()
        self._surcharge(exercice=devoir, anonymat=0).insert()
        surcharges = source.surcharges()
        self.assertEqual(len(surcharges), 2)
        s_lot = next(s for s in surcharges if s.cohorte == lot)
        self.assertEqual((s_lot.exercice, s_lot.chaine.nb_pairs, s_lot.chaine.note_sur), (None, 5, 10))
        self.assertEqual(s_lot.chaine.config(Etape.FORMATEUR).expiration, Expiration.ESCALADER)
        s_dev = next(s for s in surcharges if s.exercice == devoir)
        self.assertFalse(s_dev.chaine.anonymat)
        self.assertIsInstance(s_dev, Surcharge)

    def test_aucune_cible_refusee(self):
        with self.assertRaisesRegex(frappe.ValidationError, "cohorte ou un exercice"):
            self._surcharge().insert()

    def test_formateur_obligatoire_dans_une_surcharge(self):
        doc = self._surcharge(cohorte=un_lot())
        doc.etapes[0].active = 0
        with self.assertRaisesRegex(frappe.ValidationError, "formateur doit rester active"):
            doc.insert()

    def test_publication_provisoire_refusee_dans_une_surcharge(self):
        doc = self._surcharge(cohorte=un_lot())
        doc.etapes[0].expiration = "publier_provisoire"
        with self.assertRaisesRegex(frappe.ValidationError, "publication provisoire"):
            doc.insert()

    def test_ligne_etape_invalide_refusee(self):
        doc = self._surcharge(cohorte=un_lot())
        doc.etapes[0].delai_heures = -1
        with self.assertRaisesRegex(frappe.ValidationError, "délai négatif"):
            doc.insert()


class TestDelegations(FrappeTestCase):
    def tearDown(self):
        frappe.db.rollback()

    def _delegation(self, **champs):
        base = {"doctype": DELEGATION, "titulaire": "Administrator", "delegataire": "Guest",
                "debut": "2026-11-01 08:00:00", "fin": "2026-11-15 18:00:00"}
        return frappe.get_doc({**base, **champs})

    def test_delegation_mappee_vers_le_domaine(self):
        self._delegation(cohorte=un_lot()).insert()
        self._delegation(delegataire="Administrator", titulaire="Guest", revoquee=1).insert()
        d = next(x for x in source.delegations() if x.titulaire == "Administrator")
        self.assertEqual(d, Delegation("Administrator", "Guest", datetime(2026, 11, 1, 8), datetime(2026, 11, 15, 18),
                                       cohorte=un_lot()))
        self.assertTrue(any(x.revoquee for x in source.delegations()))

    def test_fin_avant_debut_refusee(self):
        with self.assertRaisesRegex(frappe.ValidationError, "fin doit suivre le début"):
            self._delegation(fin="2026-10-01 00:00:00").insert()

    def test_auto_delegation_refusee(self):
        with self.assertRaisesRegex(frappe.ValidationError, "titulaire et le délégataire"):
            self._delegation(delegataire="Administrator").insert()


class TestJournal(FrappeTestCase):
    def tearDown(self):
        frappe.set_user("Administrator")
        frappe.db.rollback()

    def test_journaliser_enregistre_l_action(self):
        journal_frappe.journaliser("COP-1", "Administrator", "note", {"note": 10}, {"note": 12}, au_nom_de="Guest")
        ligne = frappe.get_last_doc(JOURNAL)
        self.assertEqual((ligne.copie, ligne.acteur, ligne.au_nom_de, ligne.action),
                         ("COP-1", "Administrator", "Guest", "note"))
        self.assertEqual((json.loads(ligne.avant), json.loads(ligne.apres)), ({"note": 10}, {"note": 12}))
        self.assertTrue(ligne.horodatage)

    def test_au_nom_de_facultatif(self):
        journal_frappe.journaliser("COP-2", "Administrator", "ouverture", {}, {})
        self.assertFalse(frappe.get_last_doc(JOURNAL).au_nom_de)

    def test_modification_refusee_meme_pour_l_administrateur(self):
        journal_frappe.journaliser("COP-3", "Administrator", "note", {}, {})
        ligne = frappe.get_last_doc(JOURNAL)
        ligne.action = "falsifiee"
        with self.assertRaisesRegex(frappe.ValidationError, "non modifiable"):
            ligne.save()
        with self.assertRaisesRegex(frappe.ValidationError, "non modifiable"):
            ligne.save(ignore_permissions=True)

    def test_suppression_refusee_meme_pour_l_administrateur(self):
        journal_frappe.journaliser("COP-4", "Administrator", "note", {}, {})
        ligne = frappe.get_last_doc(JOURNAL)
        with self.assertRaisesRegex(frappe.ValidationError, "non modifiable"):
            frappe.delete_doc(JOURNAL, ligne.name, force=True)
        utilisateur("sm.console@example.ci", "System Manager")
        frappe.set_user("sm.console@example.ci")
        with self.assertRaises(frappe.PermissionError):
            frappe.delete_doc(JOURNAL, ligne.name)
        frappe.set_user("Administrator")
        self.assertTrue(frappe.db.exists(JOURNAL, ligne.name))


class TestDroitsConsole(FrappeTestCase):
    """OWASP A01 : aucun accès apprenant aux écrans de l'évaluation."""

    def setUp(self):
        utilisateur(ELEVE, "LMS Student")
        utilisateur("resp.console@example.ci", ROLE)
        journal_frappe.journaliser("COP-9", "Administrator", "note", {}, {})
        self.ligne = frappe.get_last_doc(JOURNAL).name
        self.surcharge = frappe.get_doc({"doctype": SURCHARGE, "cohorte": un_lot(),
                                         "etapes": etapes_formateur()}).insert().name
        self.delegation = frappe.get_doc({"doctype": DELEGATION, "titulaire": "Administrator", "delegataire": "Guest",
                                          "debut": "2026-11-01 08:00:00", "fin": "2026-11-02 08:00:00"}).insert().name

    def tearDown(self):
        frappe.set_user("Administrator")
        frappe.db.rollback()

    def _noms(self):
        return ((REGLAGES, REGLAGES), (SURCHARGE, self.surcharge), (DELEGATION, self.delegation),
                (JOURNAL, self.ligne))

    def test_apprenant_ne_lit_aucun_ecran(self):
        frappe.set_user(ELEVE)
        for doctype, nom in self._noms():
            with self.subTest(doctype=doctype):
                self.assertFalse(frappe.has_permission(doctype, "read"))
                with self.assertRaises(frappe.PermissionError):
                    frappe.get_doc(doctype, nom).check_permission("read")

    def test_apprenant_n_ecrit_aucun_ecran(self):
        frappe.set_user(ELEVE)
        for doctype, nom in self._noms():
            with self.subTest(doctype=doctype):
                doc = frappe.get_doc(doctype, nom)
                with self.assertRaises(frappe.PermissionError):
                    doc.save()
                with self.assertRaises(frappe.PermissionError):
                    frappe.delete_doc(doctype, nom)

    def test_apprenant_ne_cree_rien(self):
        frappe.set_user(ELEVE)
        with self.assertRaises(frappe.PermissionError):
            frappe.get_doc({"doctype": DELEGATION, "titulaire": "Administrator", "delegataire": "Guest",
                            "debut": "2026-11-01 08:00:00", "fin": "2026-11-02 08:00:00"}).insert()

    def test_responsable_pedagogique_lit_les_reglages_et_ecrit_les_delegations(self):
        frappe.set_user("resp.console@example.ci")
        self.assertTrue(frappe.has_permission(REGLAGES, "read"))
        self.assertFalse(frappe.has_permission(REGLAGES, "write"))
        self.assertTrue(frappe.has_permission(DELEGATION, "write"))
        self.assertFalse(frappe.has_permission(SURCHARGE, "write"))
        self.assertFalse(frappe.has_permission(JOURNAL, "write"))
