import json
from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, now_datetime

from openlab_academy.domain.delegation import Delegation
from openlab_academy.domain.reglages_evaluation import (
    CHAINES_DEFAUT, ConfigIA, Etape, Expiration, ReglagesEvaluation, TypeExercice)
from openlab_academy.entrypoints import install
from openlab_academy.infrastructure import journal_frappe
from openlab_academy.infrastructure import reglages_evaluation_frappe as source
from openlab_academy.patches import initialiser_reglages_evaluation, migrer_surcharges_partielles

REGLAGES = "Reglages Evaluation OpenLab"
SURCHARGE = "Surcharge Evaluation OpenLab"
DELEGATION = "Delegation OpenLab"
EQUIPE = "Equipe Correction OpenLab"
JOURNAL = "Journal Note OpenLab"
ELEVE = "eleve.console@example.ci"
ELEVE_CORRECTEUR = "eleve.correcteur.console@example.ci"
RESP_DELEG = "resp.delegation@example.ci"
CORRECTEUR_LMS = "correcteur.lms@example.ci"
ROLE = "Responsable pédagogique OpenLab"


def vider():
    doc = frappe.get_single(REGLAGES)
    for table in ("etapes", "parametres", "grille_generique", "tournures"):
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
        for ligne in doc.parametres:
            if ligne.type_exercice == "capstone":
                ligne.nb_pairs = 5
        doc.save(ignore_permissions=True)
        source.initialiser()
        r = source.charger()
        self.assertEqual((r.ia.delai_minutes, r.chaines[TypeExercice.CAPSTONE].nb_pairs,
                          r.chaines[TypeExercice.LIVRABLE].nb_pairs), (25, 5, 3))

    def test_site_existant_recoit_les_parametres_par_type(self):
        vider()
        source.initialiser()
        doc = frappe.get_single(REGLAGES)
        doc.set("parametres", [])
        doc.save(ignore_permissions=True)
        self.assertEqual(source.charger().chaines, CHAINES_DEFAUT)  # repli sur les défauts du domaine
        source.initialiser()
        self.assertEqual(len(frappe.get_single(REGLAGES).parametres), 4)

    def test_parametres_par_type_d_exercice(self):
        vider()
        source.initialiser()
        self.assertEqual(len(frappe.get_single(REGLAGES).parametres), 4)
        doc = frappe.get_single(REGLAGES)
        for ligne in doc.parametres:
            if ligne.type_exercice == "projet":
                ligne.update({"note_sur": 10, "seuil_reussite": 5, "anonymat": 0, "pairs_attente_max_jours": 2,
                              "pairs_minimum_releves": 0, "pairs_reattributions_max": 0})
        doc.save(ignore_permissions=True)
        chaines = source.charger().chaines
        self.assertEqual((chaines[TypeExercice.PROJET].note_sur, chaines[TypeExercice.PROJET].anonymat), (10, False))
        projet = chaines[TypeExercice.PROJET]
        self.assertEqual((projet.pairs_attente_max_jours, projet.pairs_minimum_releves,
                          projet.pairs_reattributions_max), (2, 0, 0))
        self.assertEqual(chaines[TypeExercice.LIVRABLE], CHAINES_DEFAUT[TypeExercice.LIVRABLE])

    def test_reglages_non_chaine_charges_meme_sans_etapes(self):
        vider()
        doc = frappe.get_single(REGLAGES)
        doc.update({"ia_url": "http://ia.local", "responsable_pedagogique": "Administrator",
                    "hotes_depots": "gitea.local", "publication_provisoire": 1})
        doc.save(ignore_permissions=True)
        r = source.charger()
        self.assertEqual((r.ia.url, r.responsable_pedagogique, r.hotes_depots, r.publication_provisoire),
                         ("http://ia.local", "Administrator", ("gitea.local",), True))
        self.assertEqual(r.chaines, {})
        self.assertEqual(r.chaine_pour(TypeExercice.PROJET, None, None, (), None), CHAINES_DEFAUT[TypeExercice.PROJET])

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
                    "ia_seuil_confiance": 0.6, "ia_plafond_caracteres": 1000, "contexte_ia_tokens": 8192,
                    "responsable_pedagogique": "Administrator",
                    "hotes_depots": "github.com\n\n gitea.local ", "niveaux_generiques": "Non\nOui",
                    "longueur_min_caracteres": 50})
        doc.set("grille_generique", [{"nom": "A", "poids": 40}, {"nom": "B", "poids": 60}])
        doc.set("tournures", [{"texte": "oublie tout"}])
        doc.set("parametres", [{"type_exercice": "projet", "nb_pairs": 2, "note_sur": 10, "seuil_reussite": 5,
                                "anonymat": 0, "note_masquee_avant_relectures": 0}])
        doc.save(ignore_permissions=True)
        r = source.charger()
        self.assertEqual(r.ia, ConfigIA("http://ia.local", "m1", "m2", 10, 0.6, ("oublie tout",), 1000, 8192))
        doc.contexte_ia_tokens = 0  # site antérieur au réglage : défaut du code
        doc.save(ignore_permissions=True)
        self.assertEqual(source.charger().ia.contexte_tokens, 4096)
        self.assertEqual((r.responsable_pedagogique, r.hotes_depots, r.niveaux_generiques, r.grille_generique),
                         ("Administrator", ("github.com", "gitea.local"), ("Non", "Oui"), (("A", 40), ("B", 60))))
        self.assertEqual(r.longueur_min_caracteres, 50)
        c = r.chaines[TypeExercice.PROJET]
        self.assertEqual((c.nb_pairs, c.note_sur, c.seuil_reussite, c.anonymat, c.note_masquee_avant_relectures),
                         (2, 10, 5.0, False, False))

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

    def test_longueur_minimale_completee_apres_migration(self):
        frappe.db.sql("delete from `tabSingles` where doctype=%s and field='longueur_min_caracteres'", REGLAGES)
        self.assertEqual(source.charger().longueur_min_caracteres, 0)  # champ vide : aucun minimum
        source.preparer()
        self.assertEqual(source.charger().longueur_min_caracteres, 200)
        frappe.db.set_single_value(REGLAGES, "longueur_min_caracteres", 0)
        source.preparer()  # une valeur réglée, même nulle, n'est jamais écrasée
        self.assertEqual(source.charger().longueur_min_caracteres, 0)

    def test_limites_de_la_console(self):
        champs = {"ia_citation_min_caracteres": 5, "instantane_fichiers_max": 3, "instantane_delai_s": 4,
                  "instantane_budget_tache_s": 30, "remise_par_heure": 7, "remise_regroupement_s": 0}
        vider()
        source.initialiser()
        self.assertEqual({c: frappe.db.get_single_value(REGLAGES, c) for c in champs},
                         {"ia_citation_min_caracteres": 8, "instantane_fichiers_max": 12, "instantane_delai_s": 10,
                          "instantane_budget_tache_s": 60, "remise_par_heure": 20, "remise_regroupement_s": 30})
        doc = frappe.get_single(REGLAGES)
        doc.update(champs)
        doc.save(ignore_permissions=True)
        r = source.charger()
        self.assertEqual((r.ia.citation_min_caracteres, r.instantane_fichiers_max, r.instantane_delai_s,
                          r.instantane_budget_tache_s, r.remise_par_heure, r.remise_regroupement_s),
                         (5, 3, 4, 30, 7, 0))
        for champ in champs:  # site antérieur au réglage : champ vide, défaut du domaine puis complété
            frappe.db.sql("delete from `tabSingles` where doctype=%s and field=%s", (REGLAGES, champ))
        self.assertEqual(source.charger().instantane_budget_tache_s, 60)
        self.assertEqual(source.charger().ia, ConfigIA())
        frappe.db.set_single_value(REGLAGES, "instantane_delai_s", 2)
        source.preparer()  # complète les champs absents, jamais une valeur réglée
        r = source.charger()
        self.assertEqual((r.ia.citation_min_caracteres, r.instantane_fichiers_max, r.instantane_delai_s,
                          r.instantane_budget_tache_s, r.remise_par_heure, r.remise_regroupement_s),
                         (8, 12, 2, 60, 20, 30))

    def test_resoumission_reglee_dans_la_console(self):
        vider()
        source.initialiser()
        self.assertEqual(source.charger().resoumission_jusqua.value, "debut_correction")
        frappe.db.set_single_value(REGLAGES, "resoumission_jusqua", "echeance")
        self.assertEqual(source.charger().resoumission_jusqua.value, "echeance")
        frappe.db.sql("delete from `tabSingles` where doctype=%s and field='resoumission_jusqua'", REGLAGES)
        self.assertEqual(source.charger().resoumission_jusqua.value, "debut_correction")  # site antérieur

    def test_cle_ia_vide_par_defaut(self):
        self.assertEqual(source.cle_ia(), "")

    def test_jeton_depots_chiffre_et_jamais_expose(self):
        self.assertEqual(source.jeton_depots(), "")
        doc = frappe.get_single(REGLAGES)
        doc.jeton_depots = "ghp_secret_456"
        doc.save(ignore_permissions=True)
        self.assertEqual(source.jeton_depots(), "ghp_secret_456")
        self.assertNotIn("ghp_secret_456", json.dumps(frappe.get_doc(REGLAGES).as_dict(), default=str))
        self.assertNotIn("ghp_secret_456", repr(source.charger()))

    def test_patch_initialise_console_role_et_espace(self):
        vider()
        frappe.db.delete("Workspace", {"name": "Évaluation OpenLab"})
        frappe.db.delete("Role", {"name": ROLE})
        initialiser_reglages_evaluation.execute()
        self.assertEqual(len(frappe.get_single(REGLAGES).etapes), 24)
        self.assertTrue(frappe.db.exists("Role", ROLE))
        espace = frappe.get_doc("Workspace", "Évaluation OpenLab")
        self.assertEqual({r.role for r in espace.roles}, {"System Manager", ROLE})
        self.assertEqual({s.link_to for s in espace.shortcuts},
                         {REGLAGES, SURCHARGE, DELEGATION, JOURNAL, "Reglages OpenLab Academy",
                          "Ouverture Lecon OpenLab", EQUIPE})
        self.assertEqual(len(json.loads(espace.content)), 7)
        initialiser_reglages_evaluation.execute()  # idempotent
        self.assertEqual(frappe.db.count("Workspace", {"name": "Évaluation OpenLab"}), 1)

    def test_espace_existant_sans_restriction_est_restreint(self):
        initialiser_reglages_evaluation.execute()
        espace = frappe.get_doc("Workspace", "Évaluation OpenLab")
        espace.set("roles", [])
        espace.save(ignore_permissions=True)
        initialiser_reglages_evaluation.execute()
        roles = {r.role for r in frappe.get_doc("Workspace", "Évaluation OpenLab").roles}
        self.assertEqual(roles, {"System Manager", ROLE})

    def test_espace_existant_recoit_les_ecrans_ajoutes(self):
        initialiser_reglages_evaluation.execute()
        espace = frappe.get_doc("Workspace", "Évaluation OpenLab")
        espace.set("shortcuts", [s for s in espace.shortcuts if s.link_to != EQUIPE])
        espace.content = json.dumps(json.loads(espace.content)[:6])
        espace.save(ignore_permissions=True)
        initialiser_reglages_evaluation.execute()
        espace = frappe.get_doc("Workspace", "Évaluation OpenLab")
        self.assertIn(EQUIPE, {s.link_to for s in espace.shortcuts})
        self.assertEqual(json.loads(espace.content)[-1]["data"]["shortcut_name"], EQUIPE)

    def test_initialiser_ne_sauvegarde_rien_si_tout_est_en_place(self):
        vider()
        source.initialiser()
        with patch("frappe.model.document.Document.save") as sauver:
            source.initialiser()
        sauver.assert_not_called()

    def test_parametres_en_double_refuses(self):
        vider()
        source.initialiser()
        doc = frappe.get_single(REGLAGES)
        doc.append("parametres", {"type_exercice": "projet", "nb_pairs": 1, "note_sur": 20, "seuil_reussite": 10})
        with self.assertRaisesRegex(frappe.ValidationError, "un seul jeu de paramètres"):
            doc.save(ignore_permissions=True)

    def test_migration_prepare_la_console(self):
        vider()
        install.after_migrate(commit=False)
        self.assertEqual(len(frappe.get_single(REGLAGES).etapes), 24)


class TestSurcharges(FrappeTestCase):
    """Surcharges partielles : un champ vide est hérité, seules les étapes citées sont remplacées."""

    def tearDown(self):
        frappe.db.rollback()

    def _surcharge(self, **champs):
        return frappe.get_doc({"doctype": SURCHARGE, **champs})

    def test_champs_vides_herites(self):
        lot, devoir = un_lot(), un_devoir()
        self._surcharge(cohorte=lot, nb_pairs="5", note_sur="10", seuil_reussite="6,5",
                        etapes=etapes_formateur()).insert()
        self._surcharge(exercice=devoir, anonymat="non").insert()
        surcharges = source.surcharges()
        s_lot = next(s for s in surcharges if s.cohorte == lot)
        self.assertEqual((s_lot.exercice, s_lot.options), (None, {"nb_pairs": 5, "note_sur": 10,
                                                                  "seuil_reussite": 6.5}))
        self.assertEqual([(c.etape, c.expiration) for c in s_lot.etapes], [(Etape.FORMATEUR, Expiration.ESCALADER)])
        s_dev = next(s for s in surcharges if s.exercice == devoir)
        self.assertEqual((s_dev.options, s_dev.etapes), ({"anonymat": False}, ()))
        chaine = source.charger().chaine_pour(TypeExercice.CAPSTONE, lot, devoir, surcharges, None)
        defaut = CHAINES_DEFAUT[TypeExercice.CAPSTONE]
        self.assertEqual((chaine.nb_pairs, chaine.anonymat, chaine.note_sur), (5, False, 10))
        self.assertEqual(chaine.config(Etape.JURY), defaut.config(Etape.JURY))  # étape non citée : héritée

    def test_deux_surcharges_sur_la_meme_cible_refusees(self):
        lot, devoir = un_lot(), un_devoir()
        self._surcharge(cohorte=lot, nb_pairs="3").insert()
        with self.assertRaisesRegex(frappe.ValidationError, "existe déjà"):
            self._surcharge(cohorte=lot, nb_pairs="2").insert()
        self._surcharge(cohorte=lot, exercice=devoir, nb_pairs="2").insert()
        with self.assertRaisesRegex(frappe.ValidationError, "existe déjà"):
            self._surcharge(cohorte=lot, exercice=devoir, nb_pairs="1").insert()
        doc = frappe.get_last_doc(SURCHARGE)
        doc.nb_pairs = "4"
        doc.save()  # se modifier soi-même reste possible

    def test_aucune_cible_ou_aucun_reglage_refuse(self):
        with self.assertRaisesRegex(frappe.ValidationError, "cohorte ou un exercice"):
            self._surcharge(nb_pairs="3").insert()
        with self.assertRaisesRegex(frappe.ValidationError, "au moins un réglage"):
            self._surcharge(cohorte=un_lot()).insert()

    def test_valeur_illisible_refusee(self):
        with self.assertRaisesRegex(frappe.ValidationError, "nb_pairs : valeur invalide"):
            self._surcharge(cohorte=un_lot(), nb_pairs="trois").insert()

    def test_formateur_obligatoire_dans_une_surcharge(self):
        doc = self._surcharge(cohorte=un_lot(), etapes=etapes_formateur())
        doc.etapes[0].active = 0
        with self.assertRaisesRegex(frappe.ValidationError, "formateur doit rester active"):
            doc.insert()

    def test_publication_provisoire_refusee_dans_une_surcharge(self):
        doc = self._surcharge(cohorte=un_lot(), etapes=etapes_formateur())
        doc.etapes[0].expiration = "publier_provisoire"
        with self.assertRaisesRegex(frappe.ValidationError, "publication provisoire"):
            doc.insert()

    def test_ligne_etape_invalide_refusee(self):
        doc = self._surcharge(cohorte=un_lot(), etapes=etapes_formateur())
        doc.etapes[0].delai_heures = -1
        with self.assertRaisesRegex(frappe.ValidationError, "délai négatif"):
            doc.insert()

    def test_pairs_bornes(self):
        self._surcharge(cohorte=un_lot(), pairs_attente_max_jours="0", pairs_reattributions_max="0").insert()
        (s,) = source.surcharges()
        self.assertEqual(s.options, {"pairs_attente_max_jours": 0, "pairs_reattributions_max": 0})
        with self.assertRaisesRegex(frappe.ValidationError, "pairs_minimum_releves"):
            self._surcharge(exercice=un_devoir(), cohorte=un_lot(), pairs_minimum_releves="9").insert()

    def test_combinaison_avec_une_autre_surcharge_refusee(self):
        lot, devoir = un_lot(), un_devoir()
        self._surcharge(cohorte=lot, pairs_minimum_releves="3").insert()
        with self.assertRaisesRegex(frappe.ValidationError,
                                    f"cohorte {lot} \\+ exercice {devoir}.*pairs_minimum_releves"):
            self._surcharge(exercice=devoir, nb_pairs="2").insert()
        self._surcharge(exercice=devoir, nb_pairs="4").insert()

    def test_reglage_global_qui_invaliderait_une_surcharge_refuse(self):
        reglages = frappe.get_single(REGLAGES)
        reglages.publication_provisoire = 1
        reglages.save(ignore_permissions=True)
        lot = un_lot()
        self._surcharge(cohorte=lot, etapes=etapes_formateur(expiration="publier_provisoire")).insert()
        reglages = frappe.get_single(REGLAGES)
        reglages.publication_provisoire = 0
        with self.assertRaisesRegex(frappe.ValidationError,
                                    f"invalideraient 1 surcharge\\(s\\) : cohorte {lot} .*provisoire"):
            reglages.save(ignore_permissions=True)
        reglages = frappe.get_single(REGLAGES)
        reglages.responsable_pedagogique = ""
        reglages.save(ignore_permissions=True)  # un réglage sans effet sur les surcharges reste enregistrable

    def test_surcharge_deja_invalide_ne_bloque_pas_le_reste_de_la_console(self):
        lot = un_lot()
        frappe.db.set_single_value(REGLAGES, "publication_provisoire", 1)
        self._surcharge(cohorte=lot, etapes=etapes_formateur(expiration="publier_provisoire")).insert()
        frappe.db.set_single_value(REGLAGES, "publication_provisoire", 0)  # hors console : déjà invalide
        reglages = frappe.get_single(REGLAGES)
        reglages.responsable_pedagogique = ""
        reglages.save(ignore_permissions=True)
        self._surcharge(exercice=un_devoir(), note_sur="10").insert()


class TestEquipes(FrappeTestCase):
    def setUp(self):
        utilisateur(RESP_DELEG, ROLE)
        utilisateur(CORRECTEUR_LMS, "Course Creator")

    def tearDown(self):
        frappe.db.rollback()

    def _equipe(self, membres=(), **champs):
        return frappe.get_doc({"doctype": EQUIPE, "membres": [{"utilisateur": u, "role": r} for u, r in membres],
                               **champs})

    def test_equipes_mappees_vers_le_domaine(self):
        lot = un_lot()
        self._equipe(responsable=RESP_DELEG).insert()
        self._equipe(((CORRECTEUR_LMS, "suppleant"), ("Administrator", "titulaire"), (RESP_DELEG, "suppleant")),
                     cohorte=lot).insert()
        globale, cohorte = sorted(source.equipes(), key=lambda e: e.niveau)
        self.assertEqual((globale.niveau, globale.responsable), (0, RESP_DELEG))
        self.assertEqual((cohorte.cohorte, cohorte.titulaires, cohorte.suppleants),
                         (lot, ("Administrator",), (CORRECTEUR_LMS, RESP_DELEG)))

    def test_regle_du_domaine_et_cible_unique(self):
        lot = un_lot()
        for doc, motif in ((self._equipe(cohorte=lot), "au moins"),
                           (self._equipe(((RESP_DELEG, "titulaire"),), cohorte=lot, exercice=un_devoir()),
                            "une seule cible"),
                           (self._equipe(((RESP_DELEG, "titulaire"), (RESP_DELEG, "suppleant")), cohorte=lot),
                            "deux fois")):
            with self.subTest(motif=motif), self.assertRaisesRegex(frappe.ValidationError, motif):
                doc.insert()
            frappe.local.message_log = []
        self._equipe(responsable=RESP_DELEG, cohorte=lot).insert()
        with self.assertRaisesRegex(frappe.ValidationError, "existe déjà"):
            self._equipe(responsable="Administrator", cohorte=lot).insert()

    def test_patch_surcharges_partielles_et_suppleants_dans_les_equipes(self):
        lot, devoir = un_lot(), un_devoir()
        avec_chaine = self._surcharge_ancienne(cohorte=lot, nb_pairs="3", anonymat="1", suppleant=CORRECTEUR_LMS,
                                               etapes=etapes_formateur())
        suppleant_seul = self._surcharge_ancienne(exercice=devoir, nb_pairs="3", note_sur="20",
                                                  suppleant=RESP_DELEG)
        migrer_surcharges_partielles.execute()
        doc = frappe.get_doc(SURCHARGE, avec_chaine)
        self.assertEqual((doc.nb_pairs, doc.anonymat, len(doc.etapes)), ("3", "oui", 6))
        self.assertEqual({e.etape for e in doc.etapes if e.active}, {"formateur"})  # les autres, jadis absentes
        self.assertFalse(frappe.db.exists(SURCHARGE, suppleant_seul))  # ne fixait aucune chaîne : vide, supprimée
        equipes = {(e.cohorte, e.exercice): e.suppleants for e in source.equipes()}
        self.assertEqual(equipes, {(lot, None): (CORRECTEUR_LMS,), (None, devoir): (RESP_DELEG,)})
        migrer_surcharges_partielles.execute()  # idempotent
        self.assertEqual(len(source.equipes()), 2)

    def test_patch_site_sans_colonne_suppleant(self):
        with patch.object(frappe.db, "has_column", return_value=False):
            migrer_surcharges_partielles.execute()
        self.assertEqual(source.equipes(), ())

    def _surcharge_ancienne(self, suppleant, anonymat=None, **champs):
        """Surcharge écrite par une version antérieure : suppléant en colonne, case à cocher 0 / 1."""
        doc = frappe.get_doc({"doctype": SURCHARGE, **champs})
        doc.flags.ignore_validate = True
        doc.insert()
        frappe.db.sql(f"update `tab{SURCHARGE}` set suppleant = %s, anonymat = %s where name = %s",
                      (suppleant, anonymat, doc.name))
        return doc.name


class TestDelegations(FrappeTestCase):
    """Écran de la console : la règle commune du domaine, le journal et les notifications (comme l'API)."""

    def setUp(self):
        utilisateur(RESP_DELEG, ROLE)
        utilisateur(CORRECTEUR_LMS, "Course Creator")
        utilisateur(ELEVE, "LMS Student")
        self.debut, self.fin = add_days(now_datetime(), -1).replace(microsecond=0), add_days(now_datetime(), 10)

    def tearDown(self):
        frappe.set_user("Administrator")
        frappe.db.rollback()

    def _delegation(self, **champs):
        base = {"doctype": DELEGATION, "titulaire": "Administrator", "delegataire": RESP_DELEG,
                "debut": self.debut, "fin": self.fin.replace(microsecond=0)}
        return frappe.get_doc({**base, **champs})

    def test_delegation_mappee_vers_le_domaine(self):
        lot, cours = un_lot(), frappe.get_all("LMS Course", pluck="name", limit=1)[0]
        self._delegation(cohorte=lot, cours=cours).insert()
        self._delegation(delegataire="Administrator", titulaire=RESP_DELEG, revoquee=1).insert()
        d = next(x for x in source.delegations() if x.titulaire == "Administrator")
        self.assertEqual(d, Delegation("Administrator", RESP_DELEG, self.debut, self.fin.replace(microsecond=0),
                                       cohorte=lot, cours=cours))
        self.assertTrue(any(x.revoquee for x in source.delegations()))

    def test_regle_commune_du_domaine(self):
        lot = un_lot()
        if not frappe.db.exists("LMS Batch Enrollment", {"batch": lot, "member": ELEVE}):
            frappe.get_doc({"doctype": "LMS Batch Enrollment", "batch": lot, "member": ELEVE}).insert(
                ignore_permissions=True)
        utilisateur(ELEVE_CORRECTEUR, "Course Creator")
        frappe.get_doc({"doctype": "LMS Batch Enrollment", "batch": lot, "member": ELEVE_CORRECTEUR}).insert(
            ignore_permissions=True)
        for champs, motif in (({"fin": self.debut}, "fin de la délégation doit suivre son début"),
                              ({"delegataire": "Administrator"}, "soi-même"),
                              ({"fin": None}, "date de fin"),
                              ({"delegataire": "Guest"}, "aucune habilitation"),
                              ({"delegataire": ELEVE_CORRECTEUR, "cohorte": lot}, "apprenant sur ce périmètre"),
                              ({"titulaire": ELEVE, "delegataire": RESP_DELEG}, "titulaire n'est pas correcteur")):
            with self.subTest(motif=motif), self.assertRaisesRegex(frappe.ValidationError, motif):
                self._delegation(**champs).insert()
            frappe.local.message_log = []

    def test_redelegation_refusee(self):
        self._delegation(delegataire=CORRECTEUR_LMS).insert()
        with self.assertRaisesRegex(frappe.ValidationError, "ne se délègue pas à nouveau"):
            self._delegation(titulaire=CORRECTEUR_LMS, delegataire=RESP_DELEG).insert()
        frappe.local.message_log = []

    def journal(self, nom):
        return frappe.get_all(JOURNAL, {"copie": f"délégation:{nom}"}, ["acteur", "action"], order_by="creation")

    def test_creation_modification_revocation_consignees_et_notifiees(self):
        doc = self._delegation().insert()
        doc.fin = add_days(self.fin, 2)
        doc.save()
        doc.save()  # rien de changé : rien à consigner
        with patch.object(source, "delegation_vers_domaine", side_effect=AssertionError("règle appliquée")):
            doc.revoquee = 1
            doc.save()  # une révocation est toujours possible
        self.assertEqual([(j.acteur, j.action) for j in self.journal(doc.name)],
                         [("Administrator", "délégation créée"), ("Administrator", "délégation modifiée"),
                          ("Administrator", "délégation révoquée")])
        for qui in ("Administrator", RESP_DELEG):
            sujets = frappe.get_all("Notification Log", {"for_user": qui, "subject": ["like", f"%{doc.name}%"]},
                                    pluck="subject")
            self.assertEqual(len(sujets), 3, qui)

    def test_revocation_par_l_api_passe_par_le_document(self):
        nom = source.DepotDelegationsFrappe().creer_delegation(
            Delegation("Administrator", RESP_DELEG, self.debut, self.fin, cours=None))
        source.DepotDelegationsFrappe().revoquer_delegation(nom)
        self.assertTrue(source.DepotDelegationsFrappe().delegation(nom).revoquee)
        self.assertEqual([j.action for j in self.journal(nom)], ["délégation créée", "délégation révoquée"])


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

    def test_horodatage_toujours_pose_par_le_serveur(self):
        frappe.get_doc({"doctype": JOURNAL, "copie": "COP-5", "acteur": "x", "action": "note",
                        "horodatage": "2001-01-01 00:00:00"}).insert(ignore_permissions=True)
        self.assertGreater(frappe.get_last_doc(JOURNAL).horodatage.year, 2020)

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
        self.delegation = frappe.get_doc({"doctype": DELEGATION, "titulaire": "Administrator",
                                          "delegataire": "resp.console@example.ci", "debut": now_datetime(),
                                          "fin": add_days(now_datetime(), 1)}).insert().name
        self.equipe = frappe.get_doc({"doctype": EQUIPE, "cohorte": un_lot(),
                                      "responsable": "resp.console@example.ci"}).insert().name

    def tearDown(self):
        frappe.set_user("Administrator")
        frappe.db.rollback()

    def _noms(self):
        return ((REGLAGES, REGLAGES), (SURCHARGE, self.surcharge), (DELEGATION, self.delegation),
                (JOURNAL, self.ligne), (EQUIPE, self.equipe))

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
        self.assertTrue(frappe.has_permission(EQUIPE, "read"))
        self.assertFalse(frappe.has_permission(EQUIPE, "write"))
