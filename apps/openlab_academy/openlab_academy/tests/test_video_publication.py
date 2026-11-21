"""La vidéo d'une séance : résolution de son adresse, et refus de publier une vidéo absente.

Le contrôle est la raison d'être de ce lot. Sans lui, une erreur de frappe dans un fichier de parcours
publie un lecteur vide, et personne ne s'en aperçoit avant qu'un apprenant ne tombe dessus — c'est-à-dire
trop tard. Il vaut mieux qu'une publication échoue bruyamment.

Rien ici ne touche la base : `videos_frappe` ne lit que le disque, et c'est un dossier temporaire qu'on
lui donne.
"""
import pathlib
import tempfile
import unittest

from openlab_academy.domain.parcours import ParcoursInvalide, valider_video
from openlab_academy.infrastructure import depot_frappe, videos_frappe
from openlab_academy.infrastructure.depot_frappe import DepotFrappe
from openlab_academy.infrastructure.yaml_source import depuis_dict
from openlab_academy.tests.fabriques import parcours_brut

INTRO = "06-ia-agentique/s01-intro.mp4"
DEMO = "01-developpeur-python/s03-demo-2.mp4"


class TestLaFormeDUneVideo(unittest.TestCase):
    """La règle de nommage de `docs/produire-une-video.md` décide de toute la chaîne de montage : c'est
    elle qui permet au contrôle de retrouver le fichier."""

    def test_un_chemin_d_atelier_a_la_regle_passe(self):
        for chemin in (INTRO, DEMO, "00-fondamentaux-data-science/s18-demo-10.mp4"):
            with self.subTest(chemin):
                self.assertEqual(valider_video(chemin), chemin)

    def test_une_adresse_https_passe(self):
        self.assertEqual(valider_video("https://video.openlab.ci/s01.mp4"),
                         "https://video.openlab.ci/s01.mp4")

    def test_rien_vaut_rien(self):
        self.assertEqual(valider_video(""), "")
        self.assertEqual(valider_video(None), "")

    def test_une_remontee_de_dossier_est_refusee(self):
        """OWASP A01 : la valeur vient d'un fichier de parcours, elle ne doit désigner que l'atelier."""
        for chemin in ("../../etc/passwd", "06-ia/../../secret.mp4", "/etc/passwd",
                       "06-ia-agentique/s01-intro.mp4/../../x.mp4"):
            with self.subTest(chemin), self.assertRaises(ParcoursInvalide):
                valider_video(chemin)

    def test_une_adresse_en_clair_est_refusee(self):
        """Une vidéo de cours servie en http se laisse remplacer en chemin."""
        with self.assertRaises(ParcoursInvalide):
            valider_video("http://video.openlab.ci/s01.mp4")

    def test_un_schema_qui_n_est_pas_une_adresse_est_refuse(self):
        for valeur in ("javascript:alert(1)", "data:video/mp4;base64,AAAA", "file:///etc/passwd"):
            with self.subTest(valeur), self.assertRaises(ParcoursInvalide):
                valider_video(valeur)

    def test_le_brut_de_captation_est_refuse(self):
        """`.mkv` est le format de captation d'OBS : il n'est pas lisible par un navigateur, et sa
        présence dans un parcours signale qu'on a publié avant de monter."""
        with self.assertRaises(ParcoursInvalide):
            valider_video("06-ia-agentique/s01-intro.mkv")

    def test_un_blanc_en_bordure_est_refuse(self):
        for valeur in (" " + INTRO, INTRO + "\n", INTRO + " "):
            with self.subTest(repr(valeur)), self.assertRaises(ParcoursInvalide):
                valider_video(valeur)


class TestLAdresseServie(unittest.TestCase):
    def setUp(self):
        self.dossier = tempfile.TemporaryDirectory()
        self.racine = pathlib.Path(self.dossier.name)
        self.addCleanup(self.dossier.cleanup)

    def poser(self, chemin: str) -> None:
        fichier = self.racine / chemin
        fichier.parent.mkdir(parents=True, exist_ok=True)
        fichier.write_bytes(b"\x00\x00\x00\x18ftypmp42")

    def test_une_video_presente_rend_son_adresse_publique(self):
        self.poser(INTRO)
        self.assertEqual(videos_frappe.adresse(INTRO, racine=self.racine),
                         videos_frappe.PREFIXE + INTRO)

    def test_une_adresse_complete_passe_telle_quelle_sans_toucher_au_disque(self):
        """Une vidéo hébergée ailleurs n'est pas la nôtre : on ne peut pas vérifier qu'elle existe, et
        on ne prétend pas le faire."""
        adresse = "https://video.openlab.ci/s01.mp4"
        self.assertEqual(videos_frappe.adresse(adresse, racine=self.racine), adresse)

    def test_une_video_absente_refuse_la_publication(self):
        with self.assertRaises(videos_frappe.VideoAbsente) as refus:
            videos_frappe.adresse(INTRO, racine=self.racine)
        self.assertIn(INTRO, str(refus.exception))

    def test_un_dossier_portant_le_nom_d_une_video_ne_passe_pas_pour_elle(self):
        (self.racine / INTRO).mkdir(parents=True)
        with self.assertRaises(videos_frappe.VideoAbsente):
            videos_frappe.adresse(INTRO, racine=self.racine)

    def test_rien_ne_rend_rien(self):
        self.assertEqual(videos_frappe.adresse("", racine=self.racine), "")

    def test_la_sortie_du_dossier_est_barree_une_seconde_fois(self):
        """Le domaine a déjà refusé ces valeurs. On les repasse ici : deux barrières, comme pour les
        archives — un appelant futur pourrait court-circuiter la première."""
        for chemin in ("../s01-intro.mp4", "/etc/passwd", "06-ia/../../s01-intro.mp4"):
            with self.subTest(chemin), self.assertRaises(videos_frappe.VideoAbsente):
                videos_frappe.adresse(chemin, racine=self.racine)

    def test_un_lien_qui_sort_du_dossier_ne_passe_pas(self):
        """Un lien symbolique posé dans l'atelier ne doit pas servir de passerelle vers le disque."""
        dehors = pathlib.Path(tempfile.mkdtemp())
        self.addCleanup(lambda: [f.unlink() for f in dehors.iterdir()] and None)
        cible = dehors / "secret.mp4"
        cible.write_bytes(b"x")
        lien = self.racine / INTRO
        lien.parent.mkdir(parents=True, exist_ok=True)
        try:
            lien.symlink_to(cible)
        except (OSError, NotImplementedError):
            self.skipTest("liens symboliques indisponibles sur ce poste")
        with self.assertRaises(videos_frappe.VideoAbsente):
            videos_frappe.adresse(INTRO, racine=self.racine)


class TestCeQuUnParcoursReference(unittest.TestCase):
    def parcours(self, *videos):
        brut = parcours_brut()
        modules = brut["blocs"][0]["modules"]
        while len(modules) < len(videos):
            modules.append({**modules[0], "num": f"{len(modules) + 1:02d}"})
        for module, video in zip(modules, videos):
            if video:
                module["video"] = video
        return depuis_dict(brut, "t.yaml")

    def test_une_seance_sans_video_ne_compte_pas(self):
        self.assertEqual(self.parcours().videos(), ())

    def test_les_videos_viennent_dans_l_ordre_des_seances(self):
        self.assertEqual(self.parcours(INTRO, DEMO).videos(), (INTRO, DEMO))

    def test_une_meme_video_citee_deux_fois_n_est_comptee_qu_une(self):
        """Deux séances peuvent partager une démo ; le contrôle n'a pas à la chercher deux fois."""
        self.assertEqual(self.parcours(INTRO, INTRO).videos(), (INTRO,))


class TestLeManquantSeDit(unittest.TestCase):
    def setUp(self):
        self.dossier = tempfile.TemporaryDirectory()
        self.racine = pathlib.Path(self.dossier.name)
        self.addCleanup(self.dossier.cleanup)

    def test_les_videos_manquantes_sont_toutes_nommees_d_un_coup(self):
        """Une publication qui s'arrête à la première absence oblige à recommencer autant de fois qu'il
        manque de vidéos. On les nomme toutes."""
        (self.racine / "06-ia-agentique").mkdir(parents=True)
        (self.racine / INTRO).write_bytes(b"x")
        manquantes = videos_frappe.manquantes([INTRO, DEMO, "https://ailleurs.ci/x.mp4", ""],
                                              racine=self.racine)
        self.assertEqual(manquantes, (DEMO,))

    def test_aucune_manquante_quand_tout_est_la(self):
        (self.racine / INTRO).parent.mkdir(parents=True)
        (self.racine / INTRO).write_bytes(b"x")
        self.assertEqual(videos_frappe.manquantes([INTRO, ""], racine=self.racine), ())


class TestLaPublicationRefuseUneVideoAbsente(unittest.TestCase):
    """Le garde-fou du lot. Il s'exécute AVANT la purge du parcours : echouer apres avoir detruit le
    contenu existant laisserait le catalogue dans un etat pire qu'avant."""

    def parcours_avec(self, *videos):
        brut = parcours_brut()
        modules = brut["blocs"][0]["modules"]
        while len(modules) < len(videos):
            modules.append({**modules[0], "num": f"{len(modules) + 1:02d}"})
        for module, video in zip(modules, videos):
            module["video"] = video
        return depuis_dict(brut, "t.yaml")

    def test_un_parcours_sans_video_passe(self):
        DepotFrappe._refuser_videos_absentes(self.parcours_avec())  # ne lève pas

    def test_une_video_absente_du_serveur_arrete_la_publication(self):
        with self.assertRaises(videos_frappe.VideoAbsente) as refus:
            DepotFrappe._refuser_videos_absentes(self.parcours_avec(INTRO))
        self.assertIn(INTRO, str(refus.exception))

    def test_toutes_les_absentes_sont_nommees_dans_le_meme_refus(self):
        with self.assertRaises(videos_frappe.VideoAbsente) as refus:
            DepotFrappe._refuser_videos_absentes(self.parcours_avec(INTRO, DEMO))
        self.assertIn(INTRO, str(refus.exception))
        self.assertIn(DEMO, str(refus.exception))

    def test_une_video_hebergee_ailleurs_ne_bloque_rien(self):
        DepotFrappe._refuser_videos_absentes(self.parcours_avec("https://video.openlab.ci/s01.mp4"))

    def test_le_controle_precede_la_purge_dans_le_remplacement(self):
        source = pathlib.Path(depot_frappe.__file__).read_text(encoding="utf-8")
        corps = source.split("def _remplacer(")[1].split("@staticmethod")[0]
        self.assertLess(corps.index("_refuser_videos_absentes"), corps.index("self._purger("))


class TestLeFichierDeParcoursALeDernierMot(unittest.TestCase):
    """Même règle que les retouches : ce qu'on a posé à la main dans l'application reste tant que le
    fichier ne le reprend pas."""

    def module(self, video=""):
        brut = parcours_brut()
        brut["blocs"][0]["modules"][0]["video"] = video
        return depuis_dict(brut, "t.yaml").blocs[0].modules[0]

    def test_sans_cle_video_la_valeur_posee_a_la_main_est_conservee(self):
        self.assertEqual(DepotFrappe._video_de(self.module(), "/files/pose-a-la-main.mp4"),
                         "/files/pose-a-la-main.mp4")

    def test_avec_une_cle_video_le_fichier_reprend_la_main(self):
        adresse = "https://video.openlab.ci/s01.mp4"
        self.assertEqual(DepotFrappe._video_de(self.module(adresse), "/files/pose-a-la-main.mp4"), adresse)

    def test_une_cle_video_absente_du_serveur_leve_plutot_que_de_poser_un_lecteur_vide(self):
        with self.assertRaises(videos_frappe.VideoAbsente):
            DepotFrappe._video_de(self.module(INTRO), "")
