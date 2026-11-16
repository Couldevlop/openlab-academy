"""Image de couverture d'un parcours : livrée avec l'application, jointe au cours, publique.

La vignette s'affiche au catalogue, donc avant toute inscription : le fichier est public, à l'inverse
des archives et des figures de leçon, réservées aux membres. Le nom vient du fichier de parcours et ne
peut pas être un chemin.
"""
import frappe
from frappe.tests.utils import FrappeTestCase

from openlab_academy.domain.parcours import Annonce
from openlab_academy.infrastructure import ressources_frappe
from openlab_academy.infrastructure.depot_frappe import DepotFrappe
from openlab_academy.domain.reglages import Reglages
from openlab_academy.infrastructure.yaml_source import FormatInvalide, _Lecteur
from openlab_academy.tests.fabriques import parcours, parcours_brut

COUVERTURE = "couverture-ia-agentique.jpg"
AUTRE_COUVERTURE = "couverture-developpeur-python.jpg"
TITRE = "Parcours couverture test"


class TestCouverture(FrappeTestCase):
    def setUp(self):
        self.depot = DepotFrappe(commit=False)

    def tearDown(self):
        frappe.db.rollback()

    def test_couverture_jointe_au_parcours_et_publique(self):
        cours = self.depot.creer(parcours(title=TITRE, couverture=COUVERTURE))
        adresse = frappe.db.get_value("LMS Course", cours, "image")
        self.assertTrue(adresse)
        fichier = frappe.db.get_value("File", {"file_url": adresse.split("?")[0]},
                                      ["is_private", "attached_to_doctype", "attached_to_name"], as_dict=True)
        self.assertEqual((fichier.is_private, fichier.attached_to_doctype, fichier.attached_to_name),
                         (0, "LMS Course", cours))

    def test_sans_couverture_aucune_image(self):
        cours = self.depot.creer(parcours(title=TITRE))
        self.assertFalse(frappe.db.get_value("LMS Course", cours, "image"))

    def test_republication_ne_duplique_pas_le_fichier(self):
        cours = self.depot.creer(parcours(title=TITRE, couverture=COUVERTURE))
        self.depot.remplacer(cours, parcours(title=TITRE, couverture=COUVERTURE))
        self.assertEqual(frappe.db.count("File", {"attached_to_doctype": "LMS Course",
                                                  "attached_to_name": cours}), 1)

    def test_une_nouvelle_couverture_remplace_l_ancienne(self):
        """Changer l'image d'un parcours ne laisse pas deux fichiers derrière elle."""
        cours = self.depot.creer(parcours(title=TITRE, couverture=COUVERTURE))
        self.depot.remplacer(cours, parcours(title=TITRE, couverture=AUTRE_COUVERTURE))
        fichiers = frappe.get_all("File", {"attached_to_doctype": "LMS Course", "attached_to_name": cours},
                                  ["file_url"])
        self.assertEqual(len(fichiers), 1)
        self.assertEqual(frappe.db.get_value("LMS Course", cours, "image").split("?")[0], fichiers[0].file_url)

    def test_adresse_de_couverture_marquee_par_le_contenu(self):
        """Une couverture redessinée garde son nom : sans ce marqueur, le navigateur garderait l'ancienne."""
        import hashlib
        cours = self.depot.creer(parcours(title=TITRE, couverture=COUVERTURE))
        empreinte = hashlib.md5(ressources_frappe.chemin(COUVERTURE).read_bytes()).hexdigest()
        self.assertTrue(frappe.db.get_value("LMS Course", cours, "image").endswith(f"?v={empreinte[:12]}"))

    def test_republication_ne_empile_pas_les_marqueurs(self):
        cours = self.depot.creer(parcours(title=TITRE, couverture=COUVERTURE))
        self.depot.remplacer(cours, parcours(title=TITRE, couverture=COUVERTURE))
        self.assertEqual(frappe.db.get_value("LMS Course", cours, "image").count("?"), 1)

    def test_parcours_a_inscrits_recoit_quand_meme_sa_couverture(self):
        """Un parcours que la publication laisse tel quel (inscrits) voit tout de même sa vitrine rafraîchie."""
        cours = self.depot.creer(parcours(title=TITRE))
        self.assertFalse(frappe.db.get_value("LMS Course", cours, "image"))
        self.depot.completer(cours, parcours(title=TITRE, couverture=COUVERTURE))
        self.assertTrue(frappe.db.get_value("LMS Course", cours, "image"))

    def test_fiche_retouchee_garde_sa_couverture(self):
        from openlab_academy.infrastructure.retouches_frappe import CHAMP
        cours = self.depot.creer(parcours(title=TITRE))
        frappe.db.set_value("LMS Course", cours, CHAMP, 1, update_modified=False)
        self.depot.completer(cours, parcours(title=TITRE, couverture=COUVERTURE))
        self.assertFalse(frappe.db.get_value("LMS Course", cours, "image"))

    def test_couverture_d_une_annonce(self):
        annonce = Annonce(title=TITRE, short_introduction="s", description="d", tags=("x",),
                          card_gradient="Blue", couverture=COUVERTURE)
        cours = self.depot.creer(annonce)
        self.assertTrue(frappe.db.get_value("LMS Course", cours, "image"))

    def test_image_absente_des_ressources_refusee(self):
        with self.assertRaises(ressources_frappe.RessourceInconnue):
            self.depot.creer(parcours(title=TITRE, couverture="absente.jpg"))

    def test_chemin_refuse_a_la_lecture(self):
        for nom in ("../secrets.jpg", "dossier/image.jpg", "image.exe"):
            with self.subTest(nom=nom):
                brut = parcours_brut()
                brut["couverture"] = nom
                with self.assertRaises(FormatInvalide):
                    _Lecteur("essai.yaml", Reglages()).parcours(brut)

    def test_couverture_lue_depuis_le_fichier(self):
        brut = parcours_brut()
        brut["couverture"] = COUVERTURE
        self.assertEqual(_Lecteur("essai.yaml", Reglages()).parcours(brut).couverture, COUVERTURE)
