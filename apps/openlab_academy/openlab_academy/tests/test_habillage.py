import pathlib
import unittest

from werkzeug.test import EnvironBuilder
from werkzeug.wrappers import Request, Response

from openlab_academy import hooks
from openlab_academy.entrypoints import http
from openlab_academy.infrastructure.habillage import FEUILLE, LIEN, SCRIPT, SCRIPT_PAIEMENT, injecter

PAGE = "<html><head><title>x</title></head><body></body></html>"
CSS = pathlib.Path(__file__).parents[1] / "public" / "css" / "openlab.css"


def requete(chemin: str) -> Request:
    return Request(EnvironBuilder(path=chemin).get_environ())


class TestInjection(unittest.TestCase):
    def test_lien_insere_avant_fin_de_head(self):
        html = injecter(PAGE)
        self.assertIn(f"{LIEN}{SCRIPT}</head>", html)
        self.assertEqual(html.count(FEUILLE), 1)

    def test_idempotent(self):
        self.assertEqual(injecter(injecter(PAGE)), injecter(PAGE))

    def test_script_de_paiement_injecte_une_seule_fois(self):
        html = injecter(injecter(PAGE))
        self.assertEqual(SCRIPT, f'<script src="{SCRIPT_PAIEMENT}" defer></script>')
        self.assertEqual(html.count(SCRIPT_PAIEMENT), 1)
        self.assertIn(f"{SCRIPT}</head>", html)

    def test_script_ajoute_si_la_feuille_est_deja_la(self):
        html = injecter(PAGE.replace("</head>", f"{LIEN}</head>"))
        self.assertEqual((html.count(FEUILLE), html.count(SCRIPT_PAIEMENT)), (1, 1))

    def test_sans_head_inchange(self):
        self.assertEqual(injecter("<p>fragment</p>"), "<p>fragment</p>")


class TestHookAfterRequest(unittest.TestCase):
    def reponse(self, corps=PAGE, mimetype="text/html"):
        return Response(corps, mimetype=mimetype)

    def test_page_lms_habillee(self):
        r = self.reponse()
        http.after_request(r, requete("/lms/courses"))
        self.assertIn(FEUILLE, r.get_data(as_text=True))
        self.assertEqual(r.content_length, len(r.get_data()))

    def test_racine_lms_habillee(self):
        r = self.reponse()
        http.after_request(r, requete("/lms"))
        self.assertIn(FEUILLE, r.get_data(as_text=True))

    def test_autres_routes_intactes(self):
        for chemin, mimetype in (("/app/user", "text/html"), ("/lmsx", "text/html"),
                                 ("/api/method/ping", "application/json")):
            with self.subTest(chemin=chemin):
                r = self.reponse('{"a": 1}' if mimetype != "text/html" else PAGE, mimetype)
                avant = r.get_data()
                http.after_request(r, requete(chemin))
                self.assertEqual(r.get_data(), avant)

    def test_json_sous_lms_intact(self):
        r = self.reponse('{"head": "</head>"}', "application/json")
        http.after_request(r, requete("/lms/x"))
        self.assertNotIn(FEUILLE, r.get_data(as_text=True))

    def test_sans_reponse_ignore(self):
        """Redirection levée par before_request : Frappe appelle after_request sans réponse."""
        self.assertIsNone(http.after_request(None, requete("/lms/courses/x")))

    def test_reponse_en_flux_ignoree(self):
        r = Response(iter([PAGE]), mimetype="text/html")
        r.direct_passthrough = True
        http.after_request(r, requete("/lms"))
        self.assertTrue(r.direct_passthrough)

    def test_donnees_de_requete_jamais_reflechies(self):
        """OWASP A03 : le lien injecté est constant, la requête n'y est jamais recopiée."""
        r = self.reponse()
        http.after_request(r, requete("/lms/%3Cscript%3Ealert(1)%3C/script%3E?x=%22%3E%3Cimg"))
        corps = r.get_data(as_text=True)
        self.assertNotIn("<script>", corps)
        self.assertNotIn("<img", corps)
        self.assertEqual(corps, injecter(PAGE))


class TestCacheNavigateurVideAuChangementDUtilisateur(unittest.TestCase):
    """Le LMS garde ses documents dans le stockage du navigateur : sur un poste partagé, l'apprenant suivant verrait
    (et croirait modifier) le rendu du précédent. Connexion et déconnexion vident ce stockage."""

    def test_connexion_et_deconnexion_vident_le_stockage(self):
        for chemin in ("/api/method/login", "/api/method/logout", "/?cmd=web_logout"):
            with self.subTest(chemin=chemin):
                r = Response("{}", mimetype="application/json")
                http.after_request(r, requete(chemin))
                self.assertEqual(r.headers.get("Clear-Site-Data"), '"storage"')

    def test_autres_requetes_intactes(self):
        for chemin in ("/api/method/frappe.auth.get_logged_user", "/lms", "/?cmd=autre", "/login"):
            with self.subTest(chemin=chemin):
                r = Response("{}", mimetype="application/json")
                http.after_request(r, requete(chemin))
                self.assertNotIn("Clear-Site-Data", r.headers)


class TestHooksDeclares(unittest.TestCase):
    def test_hooks(self):
        self.assertEqual(hooks.after_request, ["openlab_academy.entrypoints.http.after_request"])
        self.assertEqual(hooks.before_request, ["openlab_academy.entrypoints.http.before_request"])
        self.assertEqual(hooks.after_install, "openlab_academy.entrypoints.install.after_install")
        self.assertIn(FEUILLE, hooks.web_include_css)
        self.assertIn(FEUILLE, hooks.app_include_css)


class TestScriptDePaiement(unittest.TestCase):
    def test_present_et_sans_dependance(self):
        js = (pathlib.Path(__file__).parents[1] / "public" / "js" / "paiement.js").read_text(encoding="utf-8")
        for jeton in ("ParcoursBloque", "/espace/paiement/", "clone()", "location.assign"):
            self.assertIn(jeton, js)
        self.assertNotIn("import ", js)


class TestFeuilleDeStyle(unittest.TestCase):
    def test_charte_openlab_academy(self):
        css = CSS.read_text(encoding="utf-8")
        for jeton in ("--ol-orange: #ec7623", "--ol-orange-dark: #c25a12", "--ol-orange-light: #f39a5b",
                      "--ol-navy: #001e48", "--ol-navy-soft: #244498", "--ol-sky: #2890c8", "--ol-sun: #fcd80f",
                      "--ol-ivory: #faf8f5", "--ol-mist: #eef1f6", "--ol-orange-deep: #b35210", "family=Montserrat", "family=Nunito+Sans", "JetBrains Mono"):
            self.assertIn(jeton, css)
        for ancien in ("Geist", "Bricolage", "#ff5a00", "#0b1b3d"):
            self.assertNotIn(ancien, css)

    def test_mode_sombre_prevu(self):
        css = CSS.read_text(encoding="utf-8")
        sombre = css[css.index('[data-theme="dark"] {'):]
        sombre = sombre[:sombre.index("}")]
        for jeton in ("--surface-base: var(--ol-night)", "--surface-gray-7:", "--ol-lien-survol:", "--ol-focus:"):
            self.assertIn(jeton, sombre)

    def test_logos_presents(self):
        images = CSS.parents[1] / "images"
        for nom in ("logo-email.png",):
            self.assertTrue((images / nom).read_bytes()[1:4] == b"PNG", nom)
        # logos vectoriels (redessin du logo officiel, docs/charte) : aucune image matricielle embarquée
        for nom in ("logo.svg", "logo-horizontal.svg"):
            svg = (images / nom).read_text(encoding="utf-8")
            self.assertIn("<path", svg)
            self.assertNotIn("data:image", svg)
