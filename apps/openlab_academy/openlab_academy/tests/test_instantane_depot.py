"""Instantané d'un dépôt public : lien validé (SSRF), API officielles seules, contenu plafonné."""
import traceback
import unittest
from unittest import mock

import requests

from openlab_academy.infrastructure.instantane_depot import (
    DepotIndisponible, DepotIntrouvable, InstantaneDepot, LienRefuse, Lien, client_pour, valider_lien)
from openlab_academy.tests.http_simule import SHA, Reponse, github

HOTES = ("github.com", "gitlab.com")
URL = "https://github.com/aya/livrable"
GET = "requests.get"


class TestValiderLien(unittest.TestCase):
    def test_liens_acceptes(self):
        self.assertEqual(valider_lien(URL, HOTES), Lien("github.com", ("aya", "livrable")))
        self.assertEqual(valider_lien("https://GitHub.com/aya/livrable.git/tree/main?x=1#y", HOTES),
                         Lien("github.com", ("aya", "livrable")))
        self.assertEqual(valider_lien("https://github.com:443/aya/livrable", HOTES).chemin, ("aya", "livrable"))
        self.assertEqual(valider_lien("https://gitlab.com/groupe/sous-groupe/projet/-/tree/main", HOTES),
                         Lien("gitlab.com", ("groupe", "sous-groupe", "projet")))

    def test_liens_refuses_sans_aucune_requete(self):
        refuses = {
            "http://github.com/aya/livrable": "HTTPS",
            "ftp://github.com/aya/livrable": "HTTPS",
            "https://127.0.0.1/aya/livrable": "adresse IP",
            "https://169.254.169.254/latest/meta-data": "adresse IP",
            "https://[::1]/aya/livrable": "adresse IP",
            "https://github.com.evil.ci/aya/livrable": "non autorisé",
            "https://evil.ci/github.com/aya": "non autorisé",
            "https://api.github.com/aya/livrable": "non autorisé",
            "https://github.com@evil.ci/aya/livrable": "identifiants",
            "https://jeton@github.com/aya/livrable": "identifiants",
            "https://github.com:8443/aya/livrable": "port",
            "https://github.com:abc/aya/livrable": "port",
            "https://github.com/aya": "chemin",
            "https://github.com/aya/..": "chemin",
            "https://github.com/aya/li%2Fvre": "chemin",
            "https://github.com/aya/livrable\nHost: evil": "mal formé",
            "https://github.com\\@evil.ci/aya/livrable": "mal formé",
            "": "HTTPS",
        }
        with mock.patch(GET) as get:
            for url, motif in refuses.items():
                with self.subTest(url=url), self.assertRaisesRegex(LienRefuse, motif):
                    valider_lien(url, HOTES)
            with self.assertRaisesRegex(LienRefuse, "HTTPS"):
                valider_lien(None, HOTES)
        get.assert_not_called()

    def test_ip_refusee_meme_si_listee_et_hebergeur_inconnu_refuse(self):
        with self.assertRaisesRegex(LienRefuse, "adresse IP"):
            valider_lien("https://10.0.0.1/aya/livrable", ("10.0.0.1",))
        with self.assertRaisesRegex(LienRefuse, "non pris en charge"):
            valider_lien("https://gitea.local/aya/livrable", ("gitea.local",))


class TestInstantaneGitHub(unittest.TestCase):
    def test_instantane_api_officielle_sans_redirection(self):
        with mock.patch(GET, side_effect=github()) as get:
            texte, commit = InstantaneDepot(HOTES, 60000).prendre(URL)
        self.assertEqual(commit, SHA)
        self.assertIn("Arborescence :\nREADME.md\nsrc/app.py\ntests/test_app.py", texte)
        self.assertIn("=== README.md ===\n# Livrable", texte)
        self.assertLess(texte.index("=== README.md"), texte.index("=== tests/test_app.py"))
        self.assertIn("=== src/app.py ===\nprint(1)", texte)
        for appel in get.call_args_list:
            self.assertTrue(appel.args[0].startswith("https://api.github.com/repos/aya/livrable"))
            self.assertIs(appel.kwargs["allow_redirects"], False)
            self.assertGreater(appel.kwargs["timeout"], 0)
        fichier = next(a for a in get.call_args_list if "/contents/" in a.args[0])
        self.assertEqual(fichier.kwargs["params"], {"ref": SHA})

    def test_ordre_de_lecture_des_fichiers_cles(self):
        fichiers = {"src/main.py": "code", "Dockerfile": "FROM x", ".env.example": "A=", "tests/test_a.py": "t",
                    ".github/workflows/ci.yml": "on: push", "package.json": "{}", "README.md": "lisez",
                    "src/binaire.py": "", "logo.png": "png"}
        base = "https://api.github.com/repos/aya/livrable/contents"
        routes = {f"{base}/src/binaire.py": Reponse(octets=b"\x00\x01")}
        with mock.patch(GET, side_effect=github(routes=routes, arbre=list(fichiers), fichiers=fichiers)) as get:
            texte, _ = InstantaneDepot(HOTES, 60000).prendre(URL)
        lus = [ligne[4:-4] for ligne in texte.splitlines() if ligne.startswith("=== ")]
        self.assertEqual(lus, ["README.md", "package.json", "tests/test_a.py", ".github/workflows/ci.yml",
                               ".env.example", "Dockerfile", "src/main.py"])
        self.assertNotIn(f"{base}/logo.png", [a.args[0] for a in get.call_args_list])

    def test_contenu_tronque_au_plafond(self):
        fichiers = {"README.md": "x" * 5000, "src/app.py": "y" * 5000}
        with mock.patch(GET, side_effect=github(fichiers=fichiers, arbre=list(fichiers))):
            texte, _ = InstantaneDepot(HOTES, 1000).prendre(URL)
        self.assertEqual(len(texte), 1000)
        self.assertIn("=== README.md ===", texte)

    def test_lecture_bornee_et_binaire_ignore(self):
        enorme = Reponse(octets=b"z" * 300000)
        binaire = Reponse(octets=b"\x89PNG\x00\x01")
        base = "https://api.github.com/repos/aya/livrable/contents"
        routes = {f"{base}/README.md": enorme, f"{base}/src/app.py": binaire}
        with mock.patch(GET, side_effect=github(routes=routes, arbre=["README.md", "src/app.py"])):
            texte, _ = InstantaneDepot(HOTES, 1000).prendre(URL)
        self.assertTrue(enorme.fermee)
        self.assertNotIn("PNG", texte)

    def test_fichiers_absents_ou_trop_gros_ignores_et_dossiers_lourds_exclus(self):
        arbre = ["README.md", "node_modules/x.js", "src/app.py"]
        base = "https://api.github.com/repos/aya/livrable"
        routes = {f"{base}/git/trees/{SHA}": Reponse(json={"tree": [
            {"path": "README.md", "type": "blob", "size": 10}, {"path": "node_modules/x.js", "type": "blob", "size": 1},
            {"path": "src/gros.py", "type": "blob", "size": 10 ** 9}, {"path": "src/app.py", "type": "blob"}]})}
        with mock.patch(GET, side_effect=github(routes=routes, arbre=arbre, fichiers={"README.md": "lisez-moi"})) as get:
            texte, _ = InstantaneDepot(HOTES, 60000).prendre(URL)
        demandes = [a.args[0] for a in get.call_args_list]
        self.assertNotIn(f"{base}/contents/node_modules/x.js", demandes)
        self.assertNotIn(f"{base}/contents/src/gros.py", demandes)
        self.assertIn(f"{base}/contents/src/app.py", demandes)  # 404 : ignoré
        self.assertNotIn("=== src/app.py", texte)

    def test_nombre_de_fichiers_et_duree_bornes(self):
        arbre = [f"src/m{i}.py" for i in range(50)]
        with mock.patch(GET, side_effect=github(arbre=arbre, fichiers={c: "x" for c in arbre})) as get:
            InstantaneDepot(HOTES, 60000, fichiers_max=3).prendre(URL)
        self.assertEqual(sum("/contents/" in a.args[0] for a in get.call_args_list), 3)
        temps = iter([0, 0, 100, 100])
        with mock.patch(GET, side_effect=github(arbre=arbre, fichiers={c: "x" for c in arbre})) as get:
            InstantaneDepot(HOTES, 60000, horloge=lambda: next(temps)).prendre(URL)
        self.assertEqual(sum("/contents/" in a.args[0] for a in get.call_args_list), 1)

    def test_depot_introuvable_prive_ou_vide(self):
        base = "https://api.github.com/repos/aya/livrable"
        cas = {"introuvable ou privé": {base: Reponse(404)}, "déplacé": {base: Reponse(301)},
               "vide": {f"{base}/commits/main": Reponse(409)}}
        for motif, routes in cas.items():
            with self.subTest(motif=motif), mock.patch(GET, side_effect=github(routes=routes)), \
                    self.assertRaisesRegex(DepotIntrouvable, motif):
                InstantaneDepot(HOTES, 1000).prendre(URL)
        with mock.patch(GET, side_effect=github(prive=True)), self.assertRaisesRegex(DepotIntrouvable, "privé"):
            InstantaneDepot(HOTES, 1000).prendre(URL)

    def test_reseau_ou_api_en_panne_indisponible(self):
        base = "https://api.github.com/repos/aya/livrable"
        cas = {"Timeout": requests.Timeout("lent"), "HTTP 500": Reponse(500), "HTTP 403": Reponse(403),
               "illisible": Reponse(texte="pas du json"), "inattendue": Reponse(json=["liste"])}
        for motif, reponse in cas.items():
            with self.subTest(motif=motif), mock.patch(GET, side_effect=github(routes={base: reponse})), \
                    self.assertRaisesRegex(DepotIndisponible, motif):
                InstantaneDepot(HOTES, 1000).prendre(URL)
        commit = {f"{base}/commits/main": Reponse(json={"sha": "../../evil"})}
        with mock.patch(GET, side_effect=github(routes=commit)), self.assertRaisesRegex(DepotIndisponible, "inattendue"):
            InstantaneDepot(HOTES, 1000).prendre(URL)

    def test_jeton_github_en_en_tete_jamais_divulgue(self):
        with mock.patch(GET, side_effect=github()) as get:
            InstantaneDepot(HOTES, 60000).prendre(URL)
        self.assertTrue(all("Authorization" not in a.kwargs["headers"] for a in get.call_args_list))
        with mock.patch(GET, side_effect=github()) as get:
            InstantaneDepot(HOTES, 60000, jeton="ghp_secret").prendre(URL)
        self.assertTrue(all(a.kwargs["headers"]["Authorization"] == "Bearer ghp_secret" for a in get.call_args_list))
        fichier = next(a for a in get.call_args_list if "/contents/" in a.args[0])
        self.assertEqual(fichier.kwargs["headers"]["Accept"], "application/vnd.github.raw+json")
        panne = requests.ConnectionError("Authorization: Bearer ghp_secret")
        with mock.patch(GET, side_effect=panne), self.assertRaises(DepotIndisponible) as attrape:
            InstantaneDepot(HOTES, 1000, jeton="ghp_secret").prendre(URL)
        self.assertNotIn("ghp_secret", "".join(traceback.format_exception(attrape.exception)))

    def test_jeton_github_jamais_envoye_a_gitlab(self):
        client = client_pour(Lien("gitlab.com", ("groupe", "projet")), 5, jeton="ghp_secret")
        with mock.patch(GET, return_value=Reponse(json={"visibility": "public", "default_branch": "main"})) as get:
            client.infos()
        self.assertNotIn("Authorization", get.call_args.kwargs["headers"])

    def test_lien_refuse_sans_requete(self):
        with mock.patch(GET) as get, self.assertRaises(LienRefuse):
            InstantaneDepot(HOTES, 1000).prendre("https://169.254.169.254/latest")
        get.assert_not_called()


class TestInstantaneGitLab(unittest.TestCase):
    API = "https://gitlab.com/api/v4/projects/groupe%2Fprojet"

    def routes(self, visibilite="public", pages=None):
        pages = pages or [[{"path": "README.md", "type": "blob"}, {"path": "src", "type": "tree"},
                           {"path": "src/main.go", "type": "blob"}]]
        table = {self.API: Reponse(json={"visibility": visibilite, "default_branch": "main"}),
                 f"{self.API}/repository/commits/main": Reponse(json={"id": SHA}),
                 f"{self.API}/repository/files/README.md/raw": Reponse(texte="# Projet"),
                 f"{self.API}/repository/files/src%2Fmain.go/raw": Reponse(texte="package main")}

        def get(url, params=None, **_):
            if url == f"{self.API}/repository/tree":
                return Reponse(json=pages[int(params["page"]) - 1])
            return table.get(url, Reponse(404))
        return get

    def test_instantane_gitlab(self):
        with mock.patch(GET, side_effect=self.routes()) as get:
            texte, commit = InstantaneDepot(HOTES, 60000).prendre("https://gitlab.com/groupe/projet")
        self.assertEqual(commit, SHA)
        self.assertIn("=== README.md ===\n# Projet", texte)
        self.assertIn("=== src/main.go ===\npackage main", texte)
        self.assertTrue(all(a.args[0].startswith(self.API) for a in get.call_args_list))

    def test_arborescence_paginee_et_bornee(self):
        pleine = [{"path": f"f{i}.txt", "type": "blob"} for i in range(100)]
        client = client_pour(Lien("gitlab.com", ("groupe", "projet")), 5)
        with mock.patch(GET, side_effect=self.routes(pages=[pleine, [{"path": "z.md", "type": "blob"}]])):
            self.assertEqual(len(client.arborescence(SHA)), 101)
        with mock.patch(GET, side_effect=self.routes(pages=[pleine] * 20)):
            self.assertEqual(len(client.arborescence(SHA)), 1000)

    def test_projet_prive_introuvable(self):
        with mock.patch(GET, side_effect=self.routes(visibilite="private")), \
                self.assertRaisesRegex(DepotIntrouvable, "privé"):
            InstantaneDepot(HOTES, 1000).prendre("https://gitlab.com/groupe/projet")
