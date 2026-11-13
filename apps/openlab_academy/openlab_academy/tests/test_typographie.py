"""Le contenu pédagogique s'écrit avec la ponctuation ordinaire.

Le tiret cadratin employé en incise est la marque la plus visible d'un texte produit par un modèle. Il
n'apporte rien que les deux points, la virgule, le point-virgule, la parenthèse ou une seconde phrase ne
fassent mieux, et il trahit la rédaction devant un lecteur professionnel.

Le test porte sur la prose, c'est-à-dire sur les phrases que l'apprenant lit : le texte des parcours et les
paragraphes et listes que le rendu fabrique. Un tiret séparant un numéro d'un titre (« Livrable 01 — M »)
est une ponctuation de libellé, pas une incise : il reste permis.
"""
import json
import unittest

from openlab_academy.domain.parcours import Parcours
from openlab_academy.domain.reglages import Reglages
from openlab_academy.infrastructure import editorjs
from openlab_academy.infrastructure.yaml_source import PARCOURS_DIR, charger_dossier

CADRATIN = "—"
DEMI_CADRATIN = "–"
PROSE = ("paragraph", "list")


def _parcours():
    return [p for p in charger_dossier(PARCOURS_DIR) if isinstance(p, Parcours)]


def _textes_du_parcours(p: Parcours):
    yield from (p.short_introduction, p.description, *p.tags)
    for bloc in p.blocs:
        for m in bloc.modules:
            yield from (m.contenu, m.livrable, m.mise_en_situation, m.travaux_pratiques or "")
            for section in m.cours:
                yield from (section.titre, *section.paragraphes)
                for t in section.tableaux:
                    yield from (t.titre, *t.entetes, *(c for ligne in t.lignes for c in ligne))
                for f in section.figures:
                    yield f.legende
            for q in m.quiz:
                yield from (q.enonce, q.explication, *q.options)
    for projet in (*(p.portfolio or ()), p.capstone):
        if projet is None:
            continue
        yield from (projet.contexte, *projet.objectifs, *projet.fonctionnalites, *projet.stack,
                    *projet.criteres_acceptation, *projet.exigences_specifiques, *projet.livrables)
        for section in projet.cours:
            yield from (section.titre, *section.paragraphes)
            for t in section.tableaux:
                yield from (t.titre, *t.entetes, *(c for ligne in t.lignes for c in ligne))
            for f in section.figures:
                yield f.legende


def _prose_rendue(p: Parcours, reglages: Reglages):
    """Les phrases que le rendu ajoute de lui-même, invisibles dans le YAML."""
    modules = [m for bloc in p.blocs for m in bloc.modules]
    # les figures exigent une adresse servie par le site ; la prose ne dépend pas de laquelle
    porteurs = [*modules, *(section for m in modules for section in m.cours),
                p.capstone, *p.capstone.cours]
    urls = {f.nom: f"/private/files/{f.nom}" for porteur in porteurs for f in porteur.figures}
    documents = [editorjs.lecon_module(m, "D", p.heures_par_module, figures_urls=urls) for m in modules]
    documents += [editorjs.lecon_projet(p.capstone, "D", reglages, urls)]
    for document in documents:
        for bloc in json.loads(document)["blocks"]:
            if bloc["type"] not in PROSE:
                continue
            if "text" in bloc["data"]:
                yield bloc["data"]["text"]
            for entree in bloc["data"].get("items", ()):
                yield entree["content"] if isinstance(entree, dict) else entree


class TestPonctuationDuContenu(unittest.TestCase):
    def _verifier(self, origine: str, texte: str):
        with self.subTest(origine, texte=texte[:70]):
            self.assertNotIn(CADRATIN, texte)
            self.assertNotIn(DEMI_CADRATIN, texte)

    def test_aucune_incise_au_tiret_dans_les_parcours(self):
        for parcours in _parcours():
            for texte in _textes_du_parcours(parcours):
                self._verifier(parcours.title, texte)

    def test_aucune_incise_au_tiret_dans_la_prose_fabriquee(self):
        reglages = Reglages()
        for parcours in _parcours():
            for texte in _prose_rendue(parcours, reglages):
                self._verifier(parcours.title, texte)
