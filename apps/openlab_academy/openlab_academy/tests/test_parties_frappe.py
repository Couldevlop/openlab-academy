"""Les parties d'une séance : chaque rubrique s'édite seule, la leçon se réassemble depuis ses parties.

Une séance naît d'un fichier de parcours, mais chacune de ses rubriques est déposée dans son propre éditeur
riche, déjà remplie. Enregistrer une partie met la leçon à jour pour les apprenants, sans republier le
parcours et sans toucher aux autres parties ; la republication, elle, conserve les parties retouchées et
réécrit les autres depuis le fichier.
"""
import json

import frappe
from frappe.tests.utils import FrappeTestCase

from openlab_academy.domain.parcours import Bloc
from openlab_academy.infrastructure import parties_frappe
from openlab_academy.infrastructure.depot_frappe import DepotFrappe
from openlab_academy.tests.test_exercices_frappe import module

TITRE = "Parcours parties test"
CHAMP = parties_frappe.CHAMP
DOCTYPE = parties_frappe.DOCTYPE


def _parcours():
    from openlab_academy.tests.fabriques import parcours
    return parcours(title=TITRE, questions_par_quiz=5, blocs=(Bloc("B1", (module(),)),))


class _Socle(FrappeTestCase):
    def setUp(self):
        self.depot = DepotFrappe(commit=False)
        self.cours = self.depot.creer(_parcours())

    def tearDown(self):
        frappe.db.rollback()

    def republier(self):
        self.depot.remplacer(self.cours, _parcours())

    def lecon(self):
        return frappe.get_doc("Course Lesson", {"course": self.cours, "title": ["like", "01 ·%"]})

    def parties(self):
        return parties_frappe.parties(self.lecon().name)

    def partie(self, cle):
        return frappe.get_doc(DOCTYPE, {"lecon": self.lecon().name, "cle": cle})

    def retoucher(self, cle="contenu", texte="<p>Écrit dans l'application</p>"):
        partie = self.partie(cle)
        partie.contenu = texte
        partie.save(ignore_permissions=True)
        return partie.name

    def blocs_de_la_lecon(self):
        return json.loads(self.lecon().content)["blocks"]


class TestPublicationDesParties(_Socle):
    def test_une_partie_par_rubrique_dans_l_ordre_de_lecture(self):
        self.assertEqual([p.cle for p in self.parties()],
                         ["contenu", "livrable", "exercices", "mise-en-situation"])
        self.assertEqual([p.rang for p in self.parties()], [1, 2, 3, 4])

    def test_chaque_partie_arrive_pre_remplie(self):
        for partie in self.parties():
            self.assertTrue((partie.contenu or "").strip(), partie.cle)
            self.assertTrue(json.loads(partie.blocs), partie.cle)

    def test_aucune_partie_marquee_par_la_publication(self):
        self.assertEqual(frappe.db.count(DOCTYPE, {"lecon": self.lecon().name, CHAMP: 1}), 0)

    def test_la_lecon_est_l_assemblage_de_ses_parties(self):
        self.assertEqual(json.loads(parties_frappe.assembler(self.lecon().name))["blocks"],
                         self.blocs_de_la_lecon())

    def test_la_lecon_de_projet_a_aussi_ses_parties(self):
        enonce = frappe.get_doc("Course Lesson", {"course": self.cours, "title": ["like", "Énoncé%"]})
        self.assertIn("contexte", [p.cle for p in parties_frappe.parties(enonce.name)])

    def test_republication_ne_laisse_aucune_partie_sans_lecon(self):
        self.republier()
        for partie in frappe.get_all(DOCTYPE, ["lecon"]):
            self.assertTrue(frappe.db.exists("Course Lesson", partie.lecon), partie.lecon)


class TestEditionEnLigne(_Socle):
    def test_partie_enregistree_marquee(self):
        nom = self.retoucher()
        self.assertEqual(frappe.db.get_value(DOCTYPE, nom, CHAMP), 1)

    def test_la_lecon_suit_aussitot(self):
        self.retoucher()
        self.assertIn("Écrit dans l'application", self.lecon().content)

    def test_les_autres_parties_ne_bougent_pas(self):
        avant = {p.cle: p.contenu for p in self.parties()}
        self.retoucher()
        apres = {p.cle: p.contenu for p in self.parties()}
        self.assertNotEqual(avant["contenu"], apres["contenu"])
        for cle in ("livrable", "exercices", "mise-en-situation"):
            self.assertEqual(avant[cle], apres[cle])

    def test_la_lecon_n_est_pas_marquee_par_le_reassemblage(self):
        self.retoucher()
        self.assertFalse(frappe.db.get_value("Course Lesson", self.lecon().name, CHAMP))

    def test_enregistrement_sans_changement_ne_marque_rien(self):
        partie = self.partie("contenu")
        partie.titre = partie.titre
        partie.save(ignore_permissions=True)
        self.assertFalse(frappe.db.get_value(DOCTYPE, partie.name, CHAMP))

    def test_le_repere_d_exercice_reste_un_bloc(self):
        """La rubrique des exercices cite le quiz : son repère doit revenir en bloc, pas en texte."""
        partie = self.partie("exercices")
        self.assertIn('data-bloc="quiz"', partie.contenu)
        partie.contenu = partie.contenu.replace("Les exercices", "Les épreuves")
        partie.save(ignore_permissions=True)
        quiz = frappe.db.get_value("LMS Quiz", {"course": self.cours})
        self.assertIn({"type": "quiz", "data": {"quiz": quiz}}, self.blocs_de_la_lecon())
        self.assertIn("Les épreuves", self.lecon().content)

    def test_script_injecte_dans_une_partie_neutralise(self):
        """Le champ de l'éditeur échappe déjà la balise à l'enregistrement ; la relecture n'en refait jamais du
        HTML actif, et l'attribut d'événement tombe avec le reste de ce qui n'est pas en liste blanche."""
        self.retoucher(texte='<p>Texte</p><script>alert(1)</script><p onclick="x()">Suite</p>')
        contenu = self.lecon().content
        self.assertNotIn("<script", contenu)
        self.assertNotIn("onclick", contenu)
        self.assertIn("Suite", contenu)


class TestRepublication(_Socle):
    def test_la_partie_retouchee_survit(self):
        self.retoucher()
        self.republier()
        self.assertEqual(frappe.db.get_value(DOCTYPE, self.partie("contenu").name, CHAMP), 1)
        self.assertIn("Écrit dans l'application", self.partie("contenu").contenu)
        self.assertIn("Écrit dans l'application", self.lecon().content)

    def test_les_autres_parties_reviennent_du_fichier(self):
        self.retoucher(cle="livrable", texte="<p>Livrable réécrit</p>")
        self.republier()
        self.assertNotIn("Écrit dans l'application", self.partie("contenu").contenu)
        self.assertIn("Livrable réécrit", self.partie("livrable").contenu)

    def test_case_decochee_le_fichier_reprend_la_main(self):
        self.retoucher()
        frappe.db.set_value(DOCTYPE, self.partie("contenu").name, CHAMP, 0)
        self.republier()
        self.assertNotIn("Écrit dans l'application", self.lecon().content)

    def test_exercices_cites_par_une_partie_retouchee_repointes(self):
        partie = self.partie("livrable")
        partie.contenu = partie.contenu.replace("Livrable", "Rendu")
        partie.save(ignore_permissions=True)
        anciens = set(frappe.get_all("LMS Assignment", {"course": self.cours}, pluck="name"))
        self.republier()
        contenu = self.lecon().content
        for ancien in anciens:
            self.assertNotIn(ancien, contenu)
        devoirs = [b["data"]["assignment"] for b in self.blocs_de_la_lecon() if b["type"] == "assignment"]
        self.assertTrue(devoirs)
        for nom in devoirs:
            self.assertTrue(frappe.db.exists("LMS Assignment", nom))


class TestPrecedenceDeLaLecon(_Socle):
    """Une leçon retouchée en entier dans l'éditeur du LMS garde la main sur ses parties."""

    def retoucher_la_lecon(self):
        lecon = self.lecon()
        contenu = json.loads(lecon.content)
        contenu["blocks"].insert(0, {"type": "paragraph", "data": {"text": "Leçon réécrite en entier"}})
        lecon.content = json.dumps(contenu, ensure_ascii=False)
        lecon.save(ignore_permissions=True)

    def textes(self):
        """Le LMS resérialise le contenu d'une leçon à l'enregistrement : la comparaison se fait sur les blocs."""
        return [b["data"].get("text", "") for b in self.blocs_de_la_lecon()]

    def test_une_partie_enregistree_ne_reecrit_plus_la_lecon(self):
        self.retoucher_la_lecon()
        self.retoucher()
        textes = self.textes()
        self.assertIn("Leçon réécrite en entier", textes)
        self.assertNotIn("Écrit dans l'application", textes)

    def test_la_partie_reste_marquee_pour_plus_tard(self):
        self.retoucher_la_lecon()
        nom = self.retoucher()
        self.assertEqual(frappe.db.get_value(DOCTYPE, nom, CHAMP), 1)
        frappe.db.set_value("Course Lesson", self.lecon().name, CHAMP, 0)
        parties_frappe.appliquer(self.lecon().name)
        self.assertIn("Écrit dans l'application", self.lecon().content)


class TestRattrapage(_Socle):
    """Un parcours qu'une cohorte en cours interdit de republier reçoit quand même ses parties, découpées depuis
    le contenu qu'il porte déjà : les inscrits ne voient rien changer."""

    def setUp(self):
        super().setUp()
        self.avant = self.lecon().content
        parties_frappe.supprimer(self.lecon().name)

    def test_les_parties_sont_recreees_sans_toucher_a_la_lecon(self):
        self.assertTrue(parties_frappe.rattraper() >= 1)
        # le LMS resérialise le contenu à l'enregistrement : la comparaison porte sur les blocs
        self.assertEqual(json.loads(self.lecon().content)["blocks"], json.loads(self.avant)["blocks"])
        self.assertEqual([p.cle for p in self.parties()],
                         ["contenu", "livrable", "exercices", "mise-en-situation"])

    def test_les_parties_rattrapees_redonnent_la_lecon(self):
        parties_frappe.rattraper()
        self.assertEqual(json.loads(parties_frappe.assembler(self.lecon().name))["blocks"],
                         json.loads(self.avant)["blocks"])

    def test_une_lecon_qui_a_deja_ses_parties_n_est_pas_touchee(self):
        parties_frappe.rattraper()
        noms = {p.name for p in self.parties()}
        parties_frappe.rattraper()
        self.assertEqual({p.name for p in self.parties()}, noms)


class TestChampsFiges(_Socle):
    """Les blocs du fichier et l'identité d'une partie ne s'écrivent qu'à la publication : l'écran les affiche en
    lecture seule, mais c'est le document lui-même qui doit refuser, l'API écrivant ce qu'on lui donne."""

    def test_blocs_non_modifiables_hors_publication(self):
        partie = self.partie("contenu")
        avant = partie.blocs
        partie.blocs = json.dumps([{"type": "paragraph", "data": {"text": "<img src=x onerror=alert(1)>"}}])
        partie.save(ignore_permissions=True)
        self.assertEqual(frappe.db.get_value(DOCTYPE, partie.name, "blocs"), avant)
        self.assertNotIn("onerror", self.lecon().content)

    def test_cle_rang_et_lecon_non_modifiables(self):
        partie = self.partie("contenu")
        avant = (partie.cle, partie.rang, partie.lecon)
        partie.cle, partie.rang = "livrable", 99
        partie.save(ignore_permissions=True)
        partie.reload()
        self.assertEqual((partie.cle, partie.rang, partie.lecon), avant)

    def test_le_texte_et_le_titre_restent_modifiables(self):
        partie = self.partie("contenu")
        partie.contenu, partie.titre = "<p>Nouveau</p>", "Ouverture"
        partie.save(ignore_permissions=True)
        partie.reload()
        self.assertEqual((partie.titre, partie.contenu), ("Ouverture", "<p>Nouveau</p>"))
