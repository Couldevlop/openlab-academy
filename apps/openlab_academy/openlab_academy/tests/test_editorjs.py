import json
import unittest

from openlab_academy.domain.parcours import Module
from openlab_academy.domain.reglages import CritereBareme, Reglages
from openlab_academy.infrastructure import editorjs
from openlab_academy.tests.fabriques import projet


REGLAGES = Reglages()


def blocs(contenu: str) -> list[dict]:
    return json.loads(contenu)["blocks"]


def texte(contenu: str) -> str:
    return json.dumps(blocs(contenu), ensure_ascii=False)


class TestRenduModule(unittest.TestCase):
    def test_structure_et_devoir_embarque(self):
        b = blocs(editorjs.lecon_module(Module("01", "M", "Le contenu", "Le livrable"), "DEV-1", 8))
        self.assertEqual([x["type"] for x in b], ["header", "paragraph", "paragraph", "header", "paragraph", "assignment"])
        self.assertEqual(b[1]["data"]["text"], "Le contenu")
        self.assertEqual(b[-1]["data"], {"assignment": "DEV-1"})

    def test_travaux_pratiques_rendus_entre_le_contenu_et_le_livrable(self):
        m = Module("01", "M", "Le contenu", "Le livrable", travaux_pratiques="Déroulé de la séance")
        b = blocs(editorjs.lecon_module(m, "DEV-1", 3))
        self.assertEqual([x["type"] for x in b],
                         ["header", "paragraph", "paragraph", "header", "paragraph", "header", "paragraph",
                          "assignment"])
        self.assertEqual(b[3]["data"]["text"], "Travaux pratiques")
        self.assertEqual(b[4]["data"]["text"], "Déroulé de la séance")
        self.assertEqual(b[5]["data"]["text"], "Livrable")

    def test_travaux_pratiques_decoupes_en_paragraphes(self):
        m = Module("01", "M", "c", "l",
                   travaux_pratiques="Déroulé.\nDéfi : agir.\n\nIndices : lire.")
        b = blocs(editorjs.lecon_module(m, "D", 3))
        self.assertEqual([x["type"] for x in b],
                         ["header", "paragraph", "paragraph", "header", "paragraph", "paragraph", "paragraph",
                          "header", "paragraph", "assignment"])
        self.assertEqual([x["data"]["text"] for x in b[4:7]], ["Déroulé.", "Défi : agir.", "Indices : lire."])

    def test_lien_de_l_archive_en_fin_de_travaux_pratiques(self):
        m = Module("01", "M", "c", "l", travaux_pratiques="Déroulé.", archive="socle.zip")
        b = blocs(editorjs.lecon_module(m, "D", 3, archive_url="/private/files/socle.zip"))
        self.assertEqual([x["type"] for x in b],
                         ["header", "paragraph", "paragraph", "header", "paragraph", "paragraph", "header",
                          "paragraph", "assignment"])
        self.assertIn('<a href="/private/files/socle.zip">socle.zip</a>', b[5]["data"]["text"])

    def test_aucun_lien_sans_adresse_servie(self):
        m = Module("01", "M", "c", "l", travaux_pratiques="Déroulé.", archive="socle.zip")
        self.assertNotIn("socle.zip", texte(editorjs.lecon_module(m, "D", 3)))

    def test_adresse_d_archive_non_servie_refusee(self):
        """OWASP A03 : seule une adresse de fichier privé du site est transformée en lien."""
        m = Module("01", "M", "c", "l", travaux_pratiques="Déroulé.", archive="socle.zip")
        for url in ("javascript:alert(1)", "https://ailleurs.example/socle.zip", "/private/files/../secrets.zip",
                    "/files/socle.zip"):
            with self.subTest(url), self.assertRaises(ValueError):
                editorjs.lecon_module(m, "D", 3, archive_url=url)

    def test_aucune_section_travaux_pratiques_sans_contenu(self):
        rendu = texte(editorjs.lecon_module(Module("01", "M", "c", "l", travaux_pratiques="   "), "D", 3))
        self.assertNotIn("Travaux pratiques", rendu)

    def test_travaux_pratiques_echappes(self):
        """OWASP A03 : le support de séance est une donnée, jamais du HTML actif."""
        rendu = texte(editorjs.lecon_module(
            Module("01", "M", "c", "l", travaux_pratiques="<script>alert(1)</script>"), "D", 3))
        self.assertNotIn("<script>", rendu)
        self.assertIn("&lt;script&gt;", rendu)

    def test_xss_neutralise(self):
        """OWASP A03 : aucun HTML actif issu des données."""
        rendu = editorjs.lecon_module(Module("01", "M", "<script>alert(1)</script>", '<img onerror="x">'), "D", 8)
        self.assertNotIn("<script>", texte(rendu))
        self.assertNotIn("<img", texte(rendu))
        self.assertIn("&lt;script&gt;", texte(rendu))


class TestRenduProjet(unittest.TestCase):
    def test_enonce_complet(self):
        rendu = texte(editorjs.lecon_projet(projet(exigences_specifiques=("Spécifique",)), "D", REGLAGES))
        for attendu in ("Guidé", "~12 h", "Contexte", "Fonctionnalités attendues", "Critères d'acceptation",
                        "couverture ≥ 70 %", "Spécifique", "Fonctionnel : 40 %", "Documentation : 10 %"):
            self.assertIn(attendu, rendu)
        self.assertEqual(blocs(editorjs.lecon_projet(projet(), "D", REGLAGES))[-1]["data"], {"assignment": "D"})

    def test_listes_au_format_attendu_par_nested_list(self):
        """Le LMS rend les listes avec @editorjs/nested-list : chaque entree est un objet {content, items}.
        Une chaine nue s'affiche 'undefined' dans la lecon."""
        listes = [b for b in blocs(editorjs.lecon_projet(projet(), "D", REGLAGES)) if b["type"] == "list"]
        self.assertTrue(listes)
        for bloc in listes:
            for entree in bloc["data"]["items"]:
                self.assertIsInstance(entree, dict)
                self.assertIsInstance(entree.get("content"), str)
                self.assertEqual(entree.get("items"), [])

    def test_xss_neutralise_dans_toutes_les_listes(self):
        p = projet(contexte="<svg onload=x>", objectifs=("<b>o</b>",), stack=("<i>s</i>",),
                   criteres_acceptation=("<a href=javascript:x>",))
        rendu = texte(editorjs.lecon_projet(p, "D", REGLAGES))
        for interdit in ("<svg", "<b>o", "<i>", "<a href"):
            self.assertNotIn(interdit, rendu)

    def test_exigences_et_bareme_lus_dans_les_reglages(self):
        reglages = Reglages(exigences_communes=("Exigence maison",),
                            bareme=(CritereBareme("Démo", 70), CritereBareme("<Code>", 30)))
        rendu = texte(editorjs.lecon_projet(projet(), "D", reglages))
        self.assertIn("Exigence maison", rendu)
        self.assertNotIn("couverture ≥ 70 %", rendu)
        self.assertIn("Démo : 70 %", rendu)
        self.assertIn("&lt;Code&gt; : 30 %", rendu)


class TestDureeModule(unittest.TestCase):
    def test_duree_affichee_selon_les_reglages(self):
        rendu = texte(editorjs.lecon_module(Module("01", "M", "c", "l"), "D", 6))
        self.assertIn("Format : ~6 h", rendu)


class TestConsignes(unittest.TestCase):
    def test_consigne_module(self):
        self.assertIn("Le &lt;livrable&gt;", editorjs.consigne_module(Module("01", "M", "c", "Le <livrable>")))

    def test_consigne_projet_echappee(self):
        c = editorjs.consigne_projet(projet(titre="<x>", criteres_acceptation=("a & b", "<c>")))
        self.assertIn("« &lt;x&gt; »", c)
        self.assertIn("<li>a &amp; b</li><li>&lt;c&gt;</li>", c)


class TestBlocVideo(unittest.TestCase):
    ID = "dQw4w9WgXcQ"

    def test_youtube_watch_et_court(self):
        attendu = {"type": "embed", "data": {
            "service": "youtube", "source": f"https://www.youtube.com/watch?v={self.ID}", "embed": self.ID,
            "width": 580, "height": 320, "caption": ""}}
        for url in (f"https://www.youtube.com/watch?v={self.ID}", f"https://youtube.com/watch?v={self.ID}",
                    f"https://www.youtube.com/watch?v={self.ID}&t=42", f"https://youtu.be/{self.ID}"):
            with self.subTest(url=url):
                self.assertEqual(editorjs.bloc_video(url), attendu)

    def test_vimeo(self):
        self.assertEqual(editorjs.bloc_video("https://vimeo.com/123456789"), {"type": "embed", "data": {
            "service": "vimeo", "source": "https://vimeo.com/123456789",
            "embed": "https://player.vimeo.com/video/123456789", "width": 580, "height": 320, "caption": ""}})

    def test_url_d_integration_reconstruite_pas_recopiee(self):
        bloc = editorjs.bloc_video(f"https://www.youtube.com/watch?v={self.ID}&autoplay=1&x=<b>")
        self.assertNotIn("autoplay", json.dumps(bloc))
        self.assertNotIn("<b>", json.dumps(bloc))

    def test_fichier_local_et_distant(self):
        for url, ext in (("/files/cours/intro.mp4", "mp4"), ("https://cdn.exemple.ci/v/a-b_c.webm", "webm"),
                         ("/files/Cours.MP4", "mp4")):
            with self.subTest(url=url):
                self.assertEqual(editorjs.bloc_video(url), {"type": "upload", "data": {
                    "file_url": url, "file_type": ext, "quizzes": []}})

    def test_refus(self):
        for url in ("javascript:alert(1)", "http://exemple.ci/v.mp4", "data:video/mp4;base64,AA",
                    "https://www.youtube.com/watch?v=<script>", "", None, "   ", "intro.mp4", "files/intro.mp4",
                    "/files/../etc/passwd.mp4", "/files/a b.mp4", "/files/a.mp4?x=1", "/files/a.exe",
                    "https://exemple.ci/a.mp4?x=1", "https://exemple.ci/a.mp4#x", "https://u:p@exemple.ci/a.mp4",
                    "https://exemple.ci/a\"onerror=x.mp4", "https://exemple.ci/a.mp4\n",
                    "https://evil.com/watch?v=dQw4w9WgXcQ", "https://www.youtube.com.evil.com/watch?v=dQw4w9WgXcQ",
                    "https://evil.com/youtu.be/dQw4w9WgXcQ", "https://youtu.be/dQw4w9WgXcQ/x",
                    "https://youtu.be/dQw4w9WgXcQ12", "https://www.youtube.com/watch?v=dQw4w9WgXc",
                    "https://www.youtube.com/watch?v=dQw4w9WgXcQ&v=aaaaaaaaaaa", "http://www.youtube.com/watch?v=dQw4w9WgXcQ",
                    "https://vimeo.com/abc", "https://vimeo.com/123/456", "https://player.vimeo.com/video/123",
                    "https://www.youtube.com:8080/watch?v=dQw4w9WgXcQ", "https://dailymotion.com/video/x7", "/files/%2e%2e/x.mp4", "/files/%2E%2E/x.mp4", "/FILES/x.mp4",
                    "/files/x.ogg", "https://cdn.exemple.ci/x.ogg", "https://youtube.com@evil.example/watch?v=dQw4w9WgXcQ",
                    "HTTPS://WWW.YOUTUBE.COM/watch?v=dQw4w9WgXcQ", "HTTPS://cdn.exemple.ci/x.mp4"):
            with self.subTest(url=url):
                self.assertIsNone(editorjs.bloc_video(url))

    def test_insertion_en_tete(self):
        bloc = editorjs.bloc_video("/files/a.mp4")
        existant = editorjs.lecon_module(Module("01", "M", "c", "l"), "D", 8)
        rendu = json.loads(editorjs.avec_video_en_tete(existant, bloc))
        self.assertEqual(rendu["blocks"][0], bloc)
        self.assertEqual(rendu["blocks"][1:], json.loads(existant)["blocks"])
        self.assertEqual(rendu["version"], "2.29.0")

    def test_insertion_contenu_vide_ou_illisible(self):
        bloc = editorjs.bloc_video("/files/a.mp4")
        self.assertEqual([b for b in json.loads(editorjs.avec_video_en_tete(None, bloc))["blocks"]], [bloc])
        self.assertEqual(json.loads(editorjs.avec_video_en_tete("", bloc))["blocks"], [bloc])
        for brut in ("pas du json", "[1]", '{"blocks": "x"}', '{"time": 0}'):
            with self.subTest(brut=brut):
                self.assertEqual(editorjs.avec_video_en_tete(brut, bloc), brut)
        self.assertEqual(editorjs.avec_video_en_tete("{}", None), "{}")
