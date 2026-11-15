"""Conversion entre les blocs EditorJS d'une rubrique et le HTML de l'éditeur riche qui l'ouvre."""
import unittest

from openlab_academy.infrastructure import html_blocs


def bloc(type_, **data):
    return {"type": type_, "data": data}


TITRE = bloc("header", text="Contenu du module", level=2)
PARAGRAPHE = bloc("paragraph", text="Un paragraphe avec <b>du gras</b> et un <a href=\"/files/x.pdf\">lien</a>.")
LISTE = bloc("list", style="unordered", items=[{"content": "Premier", "items": []},
                                               {"content": "Second", "items": []}])
LISTE_ORDONNEE = bloc("list", style="ordered", items=[{"content": "Un", "items": []}])
TABLEAU = bloc("table", withHeadings=True, content=[["Critère", "Poids"], ["Démo", "40 %"]])
CODE = bloc("codeBox", code="x = 1\nprint(x)", language="python")
IMAGE = bloc("image", url="/private/files/schema.svg", caption="Une légende",
             withBorder=False, withBackground=False, stretched=False)
DEVOIR = bloc("assignment", assignment="DEV-1")
QUIZ = bloc("quiz", quiz="QUIZ-1")

TOUS = [TITRE, PARAGRAPHE, LISTE, LISTE_ORDONNEE, TABLEAU, CODE, IMAGE, DEVOIR, QUIZ]  # tout ce qu'une rubrique produit


class TestAllerRetour(unittest.TestCase):
    def test_chaque_bloc_revient_identique(self):
        for b in TOUS:
            with self.subTest(b["type"]):
                self.assertEqual(html_blocs.vers_blocs(html_blocs.vers_html([b])), [b])

    def test_une_rubriques_entiere_revient_identique(self):
        self.assertEqual(html_blocs.vers_blocs(html_blocs.vers_html(TOUS)), TOUS)

    def test_bloc_hors_rubrique_n_entre_pas_dans_l_editeur(self):
        """Un type de bloc qu'une rubrique ne produit pas (vidéo d'ouverture, intégration) n'est pas du texte à
        éditer : il ne traverse pas l'éditeur, faute de quoi un repère libre permettrait de forger un bloc dont
        le texte échapperait à la liste blanche."""
        inattendu = bloc("embed", service="youtube", source="https://www.youtube.com/watch?v=aaaaaaaaaaa")
        self.assertEqual(html_blocs.vers_html([inattendu]), "")
        self.assertEqual(html_blocs.vers_blocs(html_blocs.vers_html([inattendu])), [])

    def test_repere_forge_sur_un_type_rendu_refuse(self):
        forge = ('<p data-bloc="paragraph" data-cle="paragraph" '
                 'data-valeur="&lt;img src=x onerror=alert(1)&gt;">x</p>')
        self.assertEqual(html_blocs.vers_blocs(forge), [])
        self.assertEqual(html_blocs.vers_blocs('<p data-bloc="quiz" data-cle="text" data-valeur="Q1">x</p>'), [])
        self.assertEqual(html_blocs.vers_blocs('<p data-bloc="quiz" data-cle="quiz" data-valeur="Q 1 &lt;b&gt;">x</p>'), [])


class TestVersHtml(unittest.TestCase):
    def test_titres_selon_le_niveau(self):
        self.assertEqual(html_blocs.vers_html([TITRE]), "<h2>Contenu du module</h2>")
        self.assertEqual(html_blocs.vers_html([bloc("header", text="Partie", level=3)]), "<h3>Partie</h3>")

    def test_liste_et_tableau_lisibles(self):
        self.assertEqual(html_blocs.vers_html([LISTE]), "<ul><li>Premier</li><li>Second</li></ul>")
        self.assertIn("<th>Critère</th>", html_blocs.vers_html([TABLEAU]))
        self.assertIn("<td>Démo</td>", html_blocs.vers_html([TABLEAU]))

    def test_exercice_rendu_en_repere_non_editable(self):
        self.assertEqual(html_blocs.vers_html([DEVOIR]),
                         '<p data-bloc="assignment" data-cle="assignment" data-valeur="DEV-1">'
                         'Devoir : DEV-1</p>')


class TestVersBlocs(unittest.TestCase):
    def test_paragraphe_simple(self):
        self.assertEqual(html_blocs.vers_blocs("<p>Du texte.</p>"),
                         [bloc("paragraph", text="Du texte.")])

    def test_balise_hors_liste_blanche_retiree_son_texte_conserve(self):
        self.assertEqual(html_blocs.vers_blocs("<p>Avant <span>dedans</span> après</p>"),
                         [bloc("paragraph", text="Avant dedans après")])

    def test_script_integralement_ecarte(self):
        self.assertEqual(html_blocs.vers_blocs("<p>Texte</p><script>alert(1)</script>"),
                         [bloc("paragraph", text="Texte")])

    def test_attribut_evenement_retire(self):
        rendu = html_blocs.vers_blocs('<p><b onmouseover="x()">gras</b></p>')
        self.assertEqual(rendu, [bloc("paragraph", text="<b>gras</b>")])

    def test_lien_javascript_refuse(self):
        rendu = html_blocs.vers_blocs('<p><a href="javascript:alert(1)">clic</a></p>')
        self.assertEqual(rendu, [bloc("paragraph", text="clic")])

    def test_lien_externe_refuse(self):
        """Une adresse de média ou de pièce ne sort pas du site : rien d'absolu dans un contenu de leçon."""
        rendu = html_blocs.vers_blocs('<p><a href="https://ailleurs.example/x">clic</a></p>')
        self.assertEqual(rendu, [bloc("paragraph", text="clic")])

    def test_image_hors_fichiers_prives_refusee(self):
        self.assertEqual(html_blocs.vers_blocs('<img src="https://ailleurs.example/x.svg">'), [])
        self.assertEqual(html_blocs.vers_blocs('<img src="/public/x.svg">'), [])

    def test_paragraphe_vide_ignore(self):
        self.assertEqual(html_blocs.vers_blocs("<p></p><p>  </p><p>Vrai</p>"),
                         [bloc("paragraph", text="Vrai")])

    def test_texte_nu_hors_balise_devient_un_paragraphe(self):
        """L'éditeur riche de Frappe laisse parfois une ligne sans balise : elle ne doit pas disparaître."""
        self.assertEqual(html_blocs.vers_blocs("Une ligne nue"),
                         [bloc("paragraph", text="Une ligne nue")])

    def test_caracteres_speciaux_echappes_une_seule_fois(self):
        self.assertEqual(html_blocs.vers_blocs("<p>a &amp; b &lt;c&gt;</p>"),
                         [bloc("paragraph", text="a &amp; b &lt;c&gt;")])

    def test_langage_de_code_inconnu_ramene_a_text(self):
        rendu = html_blocs.vers_blocs('<pre data-langage="brainfuck"><code>+++</code></pre>')
        self.assertEqual(rendu, [bloc("codeBox", code="+++", language="text")])

    def test_repere_d_exercice_relu(self):
        rendu = html_blocs.vers_blocs('<p data-bloc="quiz" data-cle="quiz" data-valeur="QUIZ-9">x</p>')
        self.assertEqual(rendu, [QUIZ | {"data": {"quiz": "QUIZ-9"}}])

    def test_repere_sans_valeur_ignore(self):
        self.assertEqual(html_blocs.vers_blocs('<p data-bloc="quiz" data-cle="quiz">x</p>'), [])


class TestRubriquesReelles(unittest.TestCase):
    """Garantie qui compte : ce que la publication écrit dans une partie se relit à l'identique après édition."""

    def test_aller_retour_sur_les_rubriques_d_une_seance(self):
        from openlab_academy.tests.test_editorjs import TestRubriques

        for rubrique in TestRubriques().rubriques():
            with self.subTest(rubrique.cle):
                blocs = list(rubrique.blocs)
                self.assertEqual(html_blocs.vers_blocs(html_blocs.vers_html(blocs)), blocs)

    def test_aller_retour_sur_les_rubriques_d_un_projet(self):
        from openlab_academy.infrastructure import editorjs
        from openlab_academy.domain.parcours import Figure, Section
        from openlab_academy.domain.reglages import Reglages
        from openlab_academy.tests.fabriques import projet

        p = projet(cours=(Section("Cadrer", ("Un paragraphe.",),
                                  figures=(Figure("schema.svg", "Une légende"),)),))
        for rubrique in editorjs.rubriques_projet(p, "D", Reglages(),
                                                  figures_urls={"schema.svg": "/private/files/schema.svg"}):
            with self.subTest(rubrique.cle):
                blocs = list(rubrique.blocs)
                self.assertEqual(html_blocs.vers_blocs(html_blocs.vers_html(blocs)), blocs)


class TestDecoupage(unittest.TestCase):
    """Un parcours publié avant les parties garde son contenu : ses rubriques se retrouvent en découpant la
    leçon telle qu'elle est en base, jamais en la régénérant depuis le fichier, qui a pu bouger depuis."""

    def test_une_rubrique_par_titre(self):
        from openlab_academy.infrastructure import editorjs
        rubriques = editorjs.decouper([
            TITRE, PARAGRAPHE,
            bloc("header", text="Première partie", level=3), bloc("paragraph", text="p"),
            bloc("header", text="Livrable", level=2), DEVOIR,
        ])
        self.assertEqual([(r.cle, r.titre) for r in rubriques],
                         [("contenu", "Contenu du module"), ("section-1", "Première partie"),
                          ("livrable", "Livrable")])

    def test_les_blocs_sont_conserves_a_l_identique(self):
        from openlab_academy.infrastructure import editorjs
        blocs = [TITRE, PARAGRAPHE, bloc("header", text="Livrable", level=2), DEVOIR]
        self.assertEqual([b for r in editorjs.decouper(blocs) for b in r.blocs], blocs)

    def test_blocs_avant_le_premier_titre(self):
        from openlab_academy.infrastructure import editorjs
        rubriques = editorjs.decouper([PARAGRAPHE, bloc("header", text="Contexte", level=2), PARAGRAPHE])
        self.assertEqual([r.cle for r in rubriques], ["entete", "contexte"])

    def test_contenu_vide(self):
        from openlab_academy.infrastructure import editorjs
        self.assertEqual(editorjs.decouper([]), [])
