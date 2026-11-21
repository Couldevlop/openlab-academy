"""La table des domaines telle que l'administration la manipule, et ce qu'elle impose."""
import frappe
from frappe.tests.utils import FrappeTestCase

from openlab_academy.domain.domaine import DOMAINES_PAR_DEFAUT, DomaineInconnu
from openlab_academy.infrastructure import domaines_frappe

DOCTYPE = domaines_frappe.DOCTYPE


class _Socle(FrappeTestCase):
    def tearDown(self):
        frappe.db.rollback()

    def poser(self, cle="essai", libelle="Essai", teinte="#244498", rang=0):
        return frappe.get_doc({"doctype": DOCTYPE, "cle": cle, "libelle": libelle, "teinte": teinte,
                               "rang": rang}).insert(ignore_permissions=True)


class TestLeFormulaireRefuseCeQuiNeSeLitPas(_Socle):
    """La seule limite posée au choix de l'administration, et elle tient à l'accessibilité."""

    def test_une_teinte_trop_claire_est_refusee(self):
        for claire in ("#ffffff", "#fcd80f", "#f39a5b"):
            with self.subTest(claire):
                with self.assertRaises(frappe.ValidationError):
                    self.poser(cle=f"clair{claire[1:4]}", teinte=claire)

    def test_une_teinte_sombre_passe_et_se_range_en_minuscules(self):
        doc = self.poser(teinte="#B35210")
        self.assertEqual(doc.teinte, "#b35210")

    def test_une_cle_avec_accent_ou_espace_est_refusee(self):
        for mauvaise in ("cybersécurité", "deux mots", "avec/barre"):
            with self.subTest(mauvaise):
                with self.assertRaises(frappe.ValidationError):
                    self.poser(cle=mauvaise)

    def test_une_cle_en_majuscules_est_refusee(self):
        """« IA » et « ia » donneraient deux familles pour une seule."""
        with self.assertRaises(frappe.ValidationError):
            self.poser(cle="IA")

    def test_deux_domaines_ne_partagent_pas_une_cle(self):
        self.poser(cle="unique")
        with self.assertRaises(Exception):
            self.poser(cle="unique", libelle="Doublon")


class TestLaSemence(_Socle):
    def test_la_table_livree_contient_les_familles_semees(self):
        """La plateforme doit démarrer remplie : un catalogue sans famille n'a aucune couleur."""
        cles = domaines_frappe.cles()
        for domaine in DOMAINES_PAR_DEFAUT:
            with self.subTest(domaine.cle):
                self.assertIn(domaine.cle, cles)

    def test_semer_de_nouveau_ne_touche_a_rien(self):
        """Une migration ne doit ni rétablir un domaine supprimé ni écraser une teinte choisie."""
        frappe.db.set_value(DOCTYPE, "ia", "teinte", "#111111")
        domaines_frappe.preparer()
        self.assertEqual(frappe.db.get_value(DOCTYPE, "ia", "teinte"), "#111111")

    def test_les_domaines_sortent_dans_l_ordre_choisi(self):
        frappe.db.set_value(DOCTYPE, "ia", "rang", -5)
        self.assertEqual(domaines_frappe.tous()[0].cle, "ia")


class TestLeLienDuParcours(_Socle):
    def test_le_champ_du_parcours_pointe_vers_la_table(self):
        """Un lien, et non du texte libre : un libellé renommé suit tout seul."""
        champ = frappe.get_doc("Custom Field", {"dt": "LMS Course", "fieldname": domaines_frappe.CHAMP})
        self.assertEqual((champ.fieldtype, champ.options), ("Link", DOCTYPE))

    def test_une_cle_inconnue_est_refusee_a_la_publication(self):
        """La faute de frappe d'un fichier doit se voir à la publication, pas devenir une carte grise."""
        with self.assertRaises(DomaineInconnu) as leve:
            domaines_frappe.exiger("intelligence-artificielle")
        self.assertIn("intelligence-artificielle", str(leve.exception))

    def test_une_cle_connue_passe(self):
        self.assertEqual(domaines_frappe.exiger("ia"), "ia")

    def test_l_absence_de_domaine_reste_permise(self):
        self.assertEqual(domaines_frappe.exiger(""), "")

    def test_le_domaine_d_un_parcours_se_relit(self):
        cours = frappe.get_doc({"doctype": "LMS Course", "title": "Parcours a domaine",
                                "short_introduction": "s", "description": "d",
                                domaines_frappe.CHAMP: "ia"}).insert(ignore_permissions=True)
        domaine = domaines_frappe.du_parcours(cours.name)
        self.assertIsNotNone(domaine)
        self.assertEqual(domaine.cle, "ia")
        self.assertTrue(domaine.teinte.startswith("#"))

    def test_un_parcours_sans_domaine_ne_rend_rien(self):
        cours = frappe.get_doc({"doctype": "LMS Course", "title": "Parcours sans domaine",
                                "short_introduction": "s", "description": "d"}).insert(ignore_permissions=True)
        self.assertIsNone(domaines_frappe.du_parcours(cours.name))


class TestCeQuiPartDansUnePagePublique(_Socle):
    """La teinte finit dans un attribut `style` et le libellé dans du texte, sur une page ouverte à
    tous. L'application n'a pas l'autoéchappement de Jinja : ce qui sort d'ici doit être sain."""

    def test_une_teinte_ecrite_hors_formulaire_ne_sort_pas_telle_quelle(self):
        """`validate` ne s'exécute pas sur une écriture directe — un correctif, un import, un test.
        La carte retombe alors sur la couleur neutre plutôt que de porter n'importe quoi."""
        for injection in ('red; background: url(javascript:alert(1))', '"><script>alert(1)</script>',
                          'inherit', ''):
            with self.subTest(injection):
                frappe.db.set_value(DOCTYPE, "ia", "teinte", injection)
                teinte = domaines_frappe.par_cle()["ia"].teinte
                self.assertEqual(teinte, "")

    def test_une_teinte_valide_traverse_intacte(self):
        frappe.db.set_value(DOCTYPE, "ia", "teinte", "#5B2A86")
        self.assertEqual(domaines_frappe.par_cle()["ia"].teinte, "#5b2a86")

    def test_un_libelle_est_rendu_echappe_sur_le_catalogue(self):
        """Le libellé est saisi dans l'administration : il n'est pas digne de confiance pour autant,
        et la page qui le porte est publique."""
        from openlab_academy.www import catalogue_public
        frappe.db.set_value(DOCTYPE, "ia", "libelle", '<script>alert(1)</script>')
        cours = frappe.get_doc({"doctype": "LMS Course", "title": "Parcours pour échappement",
                                "short_introduction": "s", "description": "d", "published": 1,
                                domaines_frappe.CHAMP: "ia"}).insert(ignore_permissions=True).name
        cartes = catalogue_public.pour_les_cartes(catalogue_public.avec_offre(
            [c for c in catalogue_public.parcours_visibles() if c.name == cours]))
        rendu = frappe.render_template("templates/carte_parcours.html", {"carte": cartes[0],
                                                                         "_": lambda s: s})
        self.assertNotIn("<script>", rendu)
        self.assertIn("&lt;script&gt;", rendu)
