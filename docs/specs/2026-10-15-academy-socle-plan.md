# OpenLab Academy — Socle : plan d'implémentation


**Objectif :** app Frappe `openlab_academy` (habillage, seed des 5 parcours avec devoirs + portfolio 10 projets + capstone, cohorte pilote) livrée dans une image Docker reproductible.

**Architecture :** app Frappe séparée installée à côté de `payments` + `lms` (aucun fork). Les parcours sont des données (`parcours/*.yaml`) validées par un module pur Python, puis écrites par un loader idempotent. Habillage par CSS injecté et réglages appliqués en `after_install`.

**Stack :** Frappe v15, Frappe LMS v2.66.0 (commit `aa8b53b0a7e940871cdb006962a212daccb52a09`), MariaDB 11.4, Redis, Python 3.14 (image bench), PyYAML 6, docker-compose v1.29.

**Spec :** `Openlab_Academy/docs/specs/2026-10-15-academy-socle-design.md` · Source contenu : `docs/specs/catalogue-source.txt`.

## Contraintes globales

- Aucune mention d'outil de génération comme auteur dans les commits, le code ou les fichiers.
- Compose compatible docker-compose **v1** : pas de clé `name:`, pas de `profiles:`.
- `.env*` gitignoré sauf `.env.example` ; aucun secret en dur hors `.env.example` (valeurs factices).
- Fourchettes de rémunération en k€ du catalogue **jamais reprises**.
- Interface en `fr`, fuseau `Africa/Abidjan`, devise `XOF`.
- Couleurs : orange `#ff5a00` (accent, < 15 % de surface), navy `#0b1b3d`, night `#0a0e1a`, ivory `#faf8f5` ; polices Geist / Bricolage Grotesque / JetBrains Mono.
- Par parcours : exactement **10 projets portfolio + 1 capstone** ; barème /20 : fonctionnel 40, qualité/tests 25, architecture 15, sécurité 10, documentation 10.
- Exigences qualité communes à toute fiche projet : README, tests ≥ 70 %, lint+format+typage, CI GitHub Actions verte, conteneurisation, secrets hors code (`.env.example`), OWASP de base, séparation domaine/infra, commits conventionnels, ADR.
- Commandes `docker exec` depuis Git Bash : préfixer `MSYS_NO_PATHCONV=1`.

## Points de vigilance (Review Focus)

1. Relance du seed sur un cours qui a des inscrits → ne rien supprimer, journaliser et passer (test `test_cours_avec_inscrits_intact`, Tâche 3).
2. YAML avec `apres_module` pointant un module inexistant → erreur explicite avant écriture (test `test_apres_module_inconnu`, Tâche 2).
3. Échec au milieu d'un parcours → les parcours précédents restent, celui en échec est annulé (test `test_echec_isole_par_parcours`, Tâche 3).
4. Caractères spéciaux (`'`, `&`, `<`) dans les textes YAML → rendus échappés dans le HTML des leçons (test `test_echappement_html`, Tâche 3).
5. Redémarrage du conteneur avec site existant → pas de ré-création du site ni perte de données (vérif. Tâche 9, étape 5).

---

## Environnement de dev (avant la Tâche 1)

Le conteneur POC `openlab-academy_frappe_1` (bench `/home/frappe/frappe-bench`, site `lms.localhost`) sert de banc de dev jusqu'à la Tâche 9. Synchronisation de l'app :

```bash
# Openlab_Academy/docker/dev-sync.sh
#!/usr/bin/env bash
set -euo pipefail
C=openlab-academy_frappe_1
B=/home/frappe/frappe-bench
SRC="$(cd "$(dirname "$0")/../apps/openlab_academy" && pwd)"
export MSYS_NO_PATHCONV=1
docker exec -u frappe "$C" rm -rf "$B/apps/openlab_academy"
docker cp "$SRC" "$C:$B/apps/openlab_academy"
docker exec -u root "$C" chown -R frappe:frappe "$B/apps/openlab_academy"
docker exec -u frappe -w "$B" "$C" bash -lc '
  ./env/bin/pip install -q -e apps/openlab_academy
  grep -qx openlab_academy sites/apps.txt || printf "\nopenlab_academy" >> sites/apps.txt'
```

Tests : `MSYS_NO_PATHCONV=1 docker exec -u frappe -w /home/frappe/frappe-bench openlab-academy_frappe_1 bash -lc "bench --site lms.localhost run-tests --app openlab_academy"` (une fois : `bench --site lms.localhost set-config allow_tests true`).

---

### Tâche 1 : squelette de l'app

**Fichiers :**
- Créer : `apps/openlab_academy/pyproject.toml`, `apps/openlab_academy/openlab_academy/{__init__.py,hooks.py,modules.txt,patches.txt}`, `apps/openlab_academy/openlab_academy/openlab_academy/__init__.py`, `apps/openlab_academy/openlab_academy/tests/__init__.py`, `docker/dev-sync.sh`, `Openlab_Academy/.gitignore`

**Interfaces :** produit le paquet `openlab_academy` installable (`bench install-app openlab_academy`).

- [ ] **1.1** `pyproject.toml` :
```toml
[project]
name = "openlab_academy"
authors = [{ name = "Openlab Consulting", email = "contact@openlabconsulting.com" }]
description = "Personnalisation OpenLab Academy pour Frappe LMS"
requires-python = ">=3.10"
readme = "README.md"
dynamic = ["version"]
dependencies = []

[build-system]
requires = ["flit_core >=3.4,<4"]
build-backend = "flit_core.buildapi"

[tool.bench.frappe-dependencies]
frappe = ">=15.0.0,<16.0.0"
```
- [ ] **1.2** `openlab_academy/__init__.py` : `__version__ = "0.1.0"`. `modules.txt` : `OpenLab Academy`. `patches.txt` : `[pre_model_sync]` puis `[post_model_sync]` (vide). `hooks.py` :
```python
app_name = "openlab_academy"
app_title = "OpenLab Academy"
app_publisher = "Openlab Consulting"
app_description = "Personnalisation OpenLab Academy pour Frappe LMS"
app_email = "contact@openlabconsulting.com"
app_license = "agpl-3.0"
required_apps = ["lms"]
```
- [ ] **1.3** `README.md` minimal (installation, `dev-sync.sh`, lancement des tests) ; `.gitignore` : `.env*`, `!.env.example`, `__pycache__/`, `*.pyc`, `poc/`.
- [ ] **1.4** Lancer `bash docker/dev-sync.sh` puis `bench --site lms.localhost install-app openlab_academy` ; attendu : `Installing openlab_academy...` sans erreur, `list-apps` liste `openlab_academy 0.1.0`.
- [ ] **1.5** Commit : `feat(academy): squelette de l'app Frappe openlab_academy`.

### Tâche 2 : schéma et validation des parcours (pur Python)

**Fichiers :**
- Créer : `openlab_academy/seed/__init__.py`, `openlab_academy/seed/schema.py`, `openlab_academy/tests/test_schema.py`, `openlab_academy/seed/parcours/00-fondamentaux-data-science.yaml` (fixture réelle : modules du Parcours 0 uniquement, portfolio rempli en Tâche 6)

**Interfaces :**
- Produit : `class SeedError(ValueError)` ; `load_dir(path: pathlib.Path) -> list[dict]` (charge tous les `*.yaml` triés, valide, retourne les parcours) ; `validate(parcours: dict, source: str) -> None`.
- Format YAML d'un parcours :
```yaml
title: Fondamentaux de la Data Science
short_introduction: "..."
description: "..."            # HTML autorisé
tags: [Data Science, Python]
card_gradient: Blue           # Red|Blue|Green|Amber|...
blocs:
  - title: "Bloc 1 — Outils & méthode (S1–S3)"
    modules:
      - num: "01"
        title: Écosystème & méthode
        contenu: "..."
        livrable: "..."
portfolio:                    # exactement 10
  - titre: "..."
    apres_module: "03"
    duree_h: 12
    niveau: guide             # guide | semi-guide | autonome
    contexte: "..."
    objectifs: ["..."]
    fonctionnalites: ["..."]
    stack: ["..."]
    criteres_acceptation: ["..."]
    exigences_specifiques: ["..."]   # s'ajoutent au socle commun
    livrables: ["..."]
capstone:                     # mêmes champs que portfolio, sans apres_module, duree_h ≈ 60
  titre: "..."
  ...
```

- [ ] **2.1** Test en échec `tests/test_schema.py` :
```python
import copy
import pathlib
import unittest

from openlab_academy.seed.schema import SeedError, load_dir, validate

PARCOURS_DIR = pathlib.Path(__file__).parents[1] / "seed" / "parcours"


def projet(num="01", niveau="guide"):
    return {
        "titre": "P", "apres_module": num, "duree_h": 12, "niveau": niveau,
        "contexte": "c", "objectifs": ["o"], "fonctionnalites": ["f"], "stack": ["s"],
        "criteres_acceptation": ["a"], "exigences_specifiques": [], "livrables": ["l"],
    }


def parcours_valide():
    cap = projet(); cap.pop("apres_module"); cap["duree_h"] = 60; cap["niveau"] = "autonome"
    return {
        "title": "T", "short_introduction": "s", "description": "d", "tags": ["x"],
        "blocs": [{"title": "B1", "modules": [{"num": "01", "title": "M", "contenu": "c", "livrable": "l"}]}],
        "portfolio": [projet() for _ in range(10)],
        "capstone": cap,
    }


class TestSchema(unittest.TestCase):
    def test_parcours_valide(self):
        validate(parcours_valide(), "t.yaml")

    def test_champ_manquant(self):
        p = parcours_valide(); del p["blocs"][0]["modules"][0]["livrable"]
        with self.assertRaisesRegex(SeedError, r"t\.yaml: blocs\[0\]\.modules\[0\]\.livrable"):
            validate(p, "t.yaml")

    def test_portfolio_pas_10(self):
        p = parcours_valide(); p["portfolio"].pop()
        with self.assertRaisesRegex(SeedError, r"portfolio: 10 projets attendus, 9 trouvés"):
            validate(p, "t.yaml")

    def test_apres_module_inconnu(self):
        p = parcours_valide(); p["portfolio"][4]["apres_module"] = "99"
        with self.assertRaisesRegex(SeedError, r"portfolio\[4\]\.apres_module: module '99' inexistant"):
            validate(p, "t.yaml")

    def test_niveau_invalide(self):
        p = parcours_valide(); p["portfolio"][0]["niveau"] = "facile"
        with self.assertRaisesRegex(SeedError, r"portfolio\[0\]\.niveau"):
            validate(p, "t.yaml")

    def test_salaire_interdit(self):
        p = parcours_valide(); p["description"] = "Rémunération visée : 35–55 k€"
        with self.assertRaisesRegex(SeedError, r"description: rémunération en k€ interdite"):
            validate(p, "t.yaml")

    def test_fichiers_reels_valides(self):
        self.assertTrue(load_dir(PARCOURS_DIR))
```
- [ ] **2.2** Lancer `bench --site lms.localhost run-tests --module openlab_academy.tests.test_schema` → échec à l'import.
- [ ] **2.3** Implémenter `seed/schema.py` :
```python
"""Validation des fichiers de parcours, sans dépendance à Frappe."""
import pathlib
import re

import yaml

NIVEAUX = {"guide", "semi-guide", "autonome"}
PROJET_CHAMPS = ("titre", "duree_h", "niveau", "contexte", "objectifs", "fonctionnalites",
                 "stack", "criteres_acceptation", "exigences_specifiques", "livrables")
SALAIRE = re.compile(r"\d+\s*k\s*€", re.IGNORECASE)


class SeedError(ValueError):
    pass


def _exiger(obj: dict, champs, chemin: str, source: str) -> None:
    for champ in champs:
        if obj.get(champ) in (None, "") and champ != "exigences_specifiques":
            raise SeedError(f"{source}: {chemin}{champ} manquant")
        if champ == "exigences_specifiques" and champ not in obj:
            raise SeedError(f"{source}: {chemin}{champ} manquant")


def _projet(p: dict, chemin: str, source: str, modules: set[str] | None) -> None:
    _exiger(p, PROJET_CHAMPS, f"{chemin}.", source)
    if p["niveau"] not in NIVEAUX:
        raise SeedError(f"{source}: {chemin}.niveau '{p['niveau']}' hors {sorted(NIVEAUX)}")
    if modules is not None:
        _exiger(p, ("apres_module",), f"{chemin}.", source)
        if str(p["apres_module"]) not in modules:
            raise SeedError(f"{source}: {chemin}.apres_module: module '{p['apres_module']}' inexistant")


def validate(parcours: dict, source: str) -> None:
    _exiger(parcours, ("title", "short_introduction", "description", "blocs", "portfolio", "capstone"), "", source)
    for champ in ("title", "short_introduction", "description"):
        if SALAIRE.search(str(parcours[champ])):
            raise SeedError(f"{source}: {champ}: rémunération en k€ interdite")
    modules: set[str] = set()
    for i, bloc in enumerate(parcours["blocs"]):
        _exiger(bloc, ("title", "modules"), f"blocs[{i}].", source)
        for j, m in enumerate(bloc["modules"]):
            _exiger(m, ("num", "title", "contenu", "livrable"), f"blocs[{i}].modules[{j}].", source)
            modules.add(str(m["num"]))
    if len(parcours["portfolio"]) != 10:
        raise SeedError(f"{source}: portfolio: 10 projets attendus, {len(parcours['portfolio'])} trouvés")
    for k, p in enumerate(parcours["portfolio"]):
        _projet(p, f"portfolio[{k}]", source, modules)
    _projet(parcours["capstone"], "capstone", source, None)


def load_dir(path: pathlib.Path) -> list[dict]:
    resultats = []
    for fichier in sorted(path.glob("*.yaml")):
        with fichier.open(encoding="utf-8") as f:
            data = yaml.safe_load(f)
        validate(data, fichier.name)
        resultats.append(data)
    return resultats
```
- [ ] **2.4** Créer `seed/parcours/00-fondamentaux-data-science.yaml` : métadonnées et 3 blocs / 10 modules recopiés de `catalogue-source.txt` (lignes 24–62), `portfolio` et `capstone` remplis provisoirement avec les 10 fiches de la Tâche 6 — **écrire directement les fiches réelles de la Tâche 6** pour éviter tout contenu factice (Tâche 6 se réduit alors à la relecture).
- [ ] **2.5** Lancer `dev-sync.sh` puis les tests → 7 tests PASS.
- [ ] **2.6** Commit : `feat(academy): schéma validé des parcours et Parcours 0`.

### Tâche 3 : loader idempotent (cours, chapitres, leçons, devoirs, projets)

**Fichiers :**
- Créer : `openlab_academy/seed/content.py`, `openlab_academy/seed/loader.py`, `openlab_academy/tests/test_loader.py`

**Interfaces :**
- Consomme : `load_dir`, `validate`, `SeedError` (Tâche 2).
- Produit : `run(path: pathlib.Path | None = None, commit: bool = True) -> dict[str, str]` (titre → `"cree"|"maj"|"ignore"|"echec"`) ; `upsert(parcours: dict) -> tuple[str, str]` (nom du cours, statut) ; `content.lecon_module(module) -> str`, `content.lecon_projet(projet, numero) -> str`, `content.consigne(projet) -> str` (HTML), `content.EXIGENCES_COMMUNES: list[str]`, `content.GRILLE: list[tuple[str, int]]`.

- [ ] **3.1** Tests en échec `tests/test_loader.py` :
```python
import copy

import frappe
from frappe.tests.utils import FrappeTestCase

from openlab_academy.seed import loader
from openlab_academy.tests.test_schema import parcours_valide


def compter(cours):
    chapitres = frappe.get_all("Course Chapter", {"course": cours}, pluck="name")
    lecons = frappe.db.count("Course Lesson", {"course": cours})
    devoirs = frappe.db.count("LMS Assignment", {"course": cours})
    return len(chapitres), lecons, devoirs


class TestLoader(FrappeTestCase):
    def setUp(self):
        self.p = parcours_valide()
        self.p["title"] = "Parcours de test seed"

    def test_creation(self):
        nom, statut = loader.upsert(self.p)
        self.assertEqual(statut, "cree")
        # 1 bloc + 10 projets + 1 capstone = 12 chapitres ; 1 module + 11 énoncés = 12 leçons ;
        # 1 devoir module + 11 devoirs projet = 12 devoirs
        self.assertEqual(compter(nom), (12, 12, 12))
        self.assertEqual(frappe.db.get_value("LMS Course", nom, "published"), 1)

    def test_idempotence(self):
        nom, _ = loader.upsert(self.p)
        nom2, statut = loader.upsert(self.p)
        self.assertEqual((nom2, statut), (nom, "maj"))
        self.assertEqual(compter(nom), (12, 12, 12))

    def test_mise_a_jour(self):
        nom, _ = loader.upsert(self.p)
        p2 = copy.deepcopy(self.p); p2["blocs"][0]["modules"][0]["title"] = "Module renommé"
        loader.upsert(p2)
        self.assertTrue(frappe.db.exists("Course Lesson", {"course": nom, "title": "01 · Module renommé"}))

    def test_cours_avec_inscrits_intact(self):
        nom, _ = loader.upsert(self.p)
        frappe.get_doc({"doctype": "LMS Enrollment", "course": nom, "member": "Administrator",
                        "member_type": "Student"}).insert(ignore_permissions=True)
        p2 = copy.deepcopy(self.p); p2["blocs"][0]["modules"][0]["title"] = "Ne doit pas apparaître"
        _, statut = loader.upsert(p2)
        self.assertEqual(statut, "ignore")
        self.assertFalse(frappe.db.exists("Course Lesson", {"course": nom, "title": "01 · Ne doit pas apparaître"}))

    def test_echappement_html(self):
        self.p["blocs"][0]["modules"][0]["contenu"] = "l'outil <script>x</script> & co"
        nom, _ = loader.upsert(self.p)
        contenu = frappe.db.get_value("Course Lesson", {"course": nom, "title": ["like", "01 ·%"]}, "content")
        self.assertIn("&lt;script&gt;", contenu)
        self.assertNotIn("<script>", contenu)

    def test_devoir_rattache_a_la_lecon(self):
        nom, _ = loader.upsert(self.p)
        lecon = frappe.get_doc("Course Lesson", {"course": nom, "title": ["like", "01 ·%"]})
        self.assertEqual(lecon.assessments[0].assessment_type, "LMS Assignment")
        self.assertIn('"type": "assignment"', lecon.content)

    def test_echec_isole_par_parcours(self):
        bon = copy.deepcopy(self.p)
        mauvais = copy.deepcopy(self.p); mauvais["title"] = "Parcours en échec"
        mauvais["blocs"][0]["modules"][0]["title"] = "x" * 300  # dépasse la longueur du champ titre
        statuts = loader.run_parcours([bon, mauvais], commit=False)
        self.assertEqual(statuts, {"Parcours de test seed": "cree", "Parcours en échec": "echec"})
        self.assertFalse(frappe.db.exists("LMS Course", {"title": "Parcours en échec"}))
```
- [ ] **3.2** Lancer les tests → échec à l'import.
- [ ] **3.3** `seed/content.py` (rendu Editor.js et HTML, échappement systématique) :
```python
import html
import json

EXIGENCES_COMMUNES = [
    "README : installation, architecture, choix techniques",
    "Tests automatisés, couverture ≥ 70 %",
    "Lint, formatage et typage vérifiés",
    "CI GitHub Actions verte",
    "Conteneurisé : démarre en une commande",
    "Secrets hors du code (.env.example fourni)",
    "Sécurité OWASP de base",
    "Architecture propre : domaine séparé de l'infrastructure",
    "Commits conventionnels",
    "Décisions documentées (ADR)",
]
GRILLE = [("Fonctionnel", 40), ("Qualité & tests", 25), ("Architecture", 15),
          ("Sécurité", 10), ("Documentation", 10)]
NIVEAU_LIBELLE = {"guide": "Guidé", "semi-guide": "Semi-guidé", "autonome": "Autonome"}


def _e(texte) -> str:
    return html.escape(str(texte), quote=False)


def _bloc(type_, **data) -> dict:
    return {"type": type_, "data": data}


def _liste(items) -> dict:
    return _bloc("list", style="unordered", items=[_e(i) for i in items])


def _doc(blocks) -> str:
    return json.dumps({"time": 0, "blocks": blocks, "version": "2.29.0"}, ensure_ascii=False)


def lecon_module(module: dict, devoir: str) -> str:
    return _doc([
        _bloc("header", text="Contenu du module", level=2),
        _bloc("paragraph", text=_e(module["contenu"])),
        _bloc("paragraph", text="Format : ~8 h — 40 % théorie, 60 % pratique."),
        _bloc("header", text="Livrable", level=2),
        _bloc("paragraph", text=f"<b>{_e(module['livrable'])}</b>"),
        _bloc("assignment", assignment=devoir),
    ])


def lecon_projet(projet: dict, devoir: str) -> str:
    blocks = [
        _bloc("paragraph", text=f"<b>{NIVEAU_LIBELLE[projet['niveau']]}</b> · ~{projet['duree_h']} h"),
        _bloc("header", text="Contexte", level=2), _bloc("paragraph", text=_e(projet["contexte"])),
        _bloc("header", text="Objectifs", level=2), _liste(projet["objectifs"]),
        _bloc("header", text="Fonctionnalités attendues", level=2), _liste(projet["fonctionnalites"]),
        _bloc("header", text="Stack", level=2), _liste(projet["stack"]),
        _bloc("header", text="Critères d'acceptation", level=2), _liste(projet["criteres_acceptation"]),
        _bloc("header", text="Exigences qualité", level=2),
        _liste(EXIGENCES_COMMUNES + list(projet["exigences_specifiques"])),
        _bloc("header", text="Livrables", level=2), _liste(projet["livrables"]),
        _bloc("header", text="Barème /20", level=2),
        _liste([f"{nom} : {poids} %" for nom, poids in GRILLE]),
        _bloc("assignment", assignment=devoir),
    ]
    return _doc(blocks)


def consigne_module(module: dict) -> str:
    return f"<p>{_e(module['livrable'])}</p><p>Rendez le lien vers votre dépôt Git ou document.</p>"


def consigne_projet(projet: dict) -> str:
    items = "".join(f"<li>{_e(c)}</li>" for c in projet["criteres_acceptation"])
    return (f"<p>Rendez l'URL du dépôt Git de « {_e(projet['titre'])} ».</p>"
            f"<p>Critères d'acceptation :</p><ul>{items}</ul>")
```
- [ ] **3.4** `seed/loader.py` :
```python
"""Écrit les parcours validés dans Frappe LMS, de façon idempotente."""
import pathlib

import frappe

from openlab_academy.seed import content
from openlab_academy.seed.schema import load_dir

PARCOURS_DIR = pathlib.Path(__file__).parent / "parcours"
INSTRUCTEUR = "Administrator"


def _purger(cours: str) -> None:
    for ch in frappe.get_all("Course Chapter", {"course": cours}, pluck="name"):
        frappe.db.delete("Course Lesson", {"chapter": ch})
        frappe.db.delete("Course Chapter", {"name": ch})
    frappe.db.delete("LMS Assignment", {"course": cours})


def _devoir(cours: str, titre: str, consigne: str) -> str:
    return frappe.get_doc({
        "doctype": "LMS Assignment", "title": titre[:140], "question": consigne,
        "type": "URL", "course": cours, "grade_assignment": 1,
    }).insert(ignore_permissions=True).name


def _chapitre(cours: str, titre: str, lecons: list[tuple[str, callable, str, str]]) -> str:
    """lecons : (titre, rendu(devoir) -> json, titre_devoir, consigne)."""
    chapitre = frappe.get_doc({"doctype": "Course Chapter", "course": cours, "title": titre}).insert(
        ignore_permissions=True)
    noms = []
    for titre_lecon, rendu, titre_devoir, consigne in lecons:
        devoir = _devoir(cours, titre_devoir, consigne)
        lecon = frappe.get_doc({
            "doctype": "Course Lesson", "course": cours, "chapter": chapitre.name,
            "title": titre_lecon, "content": rendu(devoir),
            "assessments": [{"assessment_type": "LMS Assignment", "assessment_name": devoir}],
        }).insert(ignore_permissions=True)
        noms.append(lecon.name)
    chapitre.reload()
    chapitre.set("lessons", [{"lesson": n} for n in noms])
    chapitre.save(ignore_permissions=True)
    return chapitre.name


def upsert(p: dict) -> tuple[str, str]:
    nom = frappe.db.get_value("LMS Course", {"title": p["title"]})
    if nom and frappe.db.count("LMS Enrollment", {"course": nom}):
        frappe.log_error(f"Seed ignoré : « {p['title']} » a des inscrits", "openlab_academy seed")
        return nom, "ignore"
    champs = {
        "title": p["title"], "short_introduction": p["short_introduction"], "description": p["description"],
        "tags": ",".join(p.get("tags", [])), "card_gradient": p.get("card_gradient", "Blue"),
        "published": 1, "enable_certification": 1,
    }
    if nom:
        statut = "maj"
        _purger(nom)
        cours = frappe.get_doc("LMS Course", nom)
        cours.update(champs)
        cours.set("chapters", [])
        cours.save(ignore_permissions=True)
    else:
        statut = "cree"
        cours = frappe.get_doc({"doctype": "LMS Course", "instructors": [{"instructor": INSTRUCTEUR}], **champs})
        cours.insert(ignore_permissions=True)
        nom = cours.name

    chapitres = []
    projets_par_module: dict[str, list[tuple[int, dict]]] = {}
    for i, pr in enumerate(p["portfolio"], start=1):
        projets_par_module.setdefault(str(pr["apres_module"]), []).append((i, pr))

    def chapitre_projet(pr: dict, prefixe: str) -> str:
        titre = f"{prefixe} — {pr['titre']}"
        return _chapitre(nom, titre, [(
            f"Énoncé — {pr['titre']}", lambda d, pr=pr: content.lecon_projet(pr, d),
            titre, content.consigne_projet(pr))])

    for bloc in p["blocs"]:
        lecons = [(f"{m['num']} · {m['title']}", lambda d, m=m: content.lecon_module(m, d),
                   f"Livrable {m['num']} — {m['title']}", content.consigne_module(m)) for m in bloc["modules"]]
        chapitres.append(_chapitre(nom, bloc["title"], lecons))
        for m in bloc["modules"]:
            for numero, pr in projets_par_module.get(str(m["num"]), []):
                chapitres.append(chapitre_projet(pr, f"Projet {numero}"))
    chapitres.append(chapitre_projet(p["capstone"], "Capstone"))

    cours = frappe.get_doc("LMS Course", nom)
    cours.set("chapters", [{"chapter": c} for c in chapitres])
    cours.save(ignore_permissions=True)
    return nom, statut


def run_parcours(parcours: list[dict], commit: bool = True) -> dict[str, str]:
    statuts = {}
    for p in parcours:
        frappe.db.savepoint("seed_parcours")
        try:
            _, statuts[p["title"]] = upsert(p)
            if commit:
                frappe.db.commit()
        except Exception:
            frappe.db.rollback(save_point="seed_parcours")
            frappe.log_error(title=f"openlab_academy seed : échec « {p['title']} »")
            statuts[p["title"]] = "echec"
    return statuts


def run(path: str | None = None, commit: bool = True) -> dict[str, str]:
    statuts = run_parcours(load_dir(pathlib.Path(path) if path else PARCOURS_DIR), commit=commit)
    print(statuts)
    return statuts
```
- [ ] **3.5** `dev-sync.sh` + tests `test_loader` → 7 PASS. Frappe rejette un `Data` > 140 caractères (`CharacterLengthExceededError`) : c'est le déclencheur d'échec du test d'isolation. S'il ne lève pas, utiliser `mauvais["portfolio"][0]["niveau"] = "inconnu"` (→ `KeyError` dans `content.lecon_projet`) — ajuster le test, pas le loader.
- [ ] **3.6** Seed réel : `bench --site lms.localhost execute openlab_academy.seed.loader.run` → `{'Fondamentaux de la Data Science': 'maj'}` (le cours POC existe déjà). Vérifier `/lms/courses/fondamentaux-de-la-data-science` : blocs et projets intercalés.
- [ ] **3.7** Commit : `feat(academy): loader idempotent des parcours, devoirs et portfolio`.

### Tâche 4 : réglages plateforme et habillage OpenLab

**Fichiers :**
- Créer : `openlab_academy/install.py`, `openlab_academy/public/css/openlab.css`, `openlab_academy/public/images/logo.svg`, `openlab_academy/tests/test_install.py`
- Modifier : `openlab_academy/hooks.py`

**Interfaces :** produit `install.after_install() -> None` (réglages + `loader.run()`), `install.appliquer_reglages() -> None`.

- [ ] **4.1** Test en échec :
```python
import frappe
from frappe.tests.utils import FrappeTestCase

from openlab_academy.install import appliquer_reglages


class TestInstall(FrappeTestCase):
    def test_reglages(self):
        appliquer_reglages()
        s = frappe.get_single("System Settings")
        self.assertEqual((s.language, s.time_zone, s.currency), ("fr", "Africa/Abidjan", "XOF"))
        self.assertEqual(frappe.db.get_single_value("Website Settings", "app_name"), "OpenLab Academy")
        self.assertEqual(frappe.db.get_single_value("LMS Settings", "default_currency"), "XOF")

    def test_css_injecte(self):
        from openlab_academy import hooks
        self.assertIn("/assets/openlab_academy/css/openlab.css", hooks.web_include_css)
```
- [ ] **4.2** `install.py` :
```python
import frappe

from openlab_academy.seed import loader


def appliquer_reglages() -> None:
    if not frappe.db.exists("Currency", "XOF"):
        frappe.get_doc({"doctype": "Currency", "currency_name": "XOF", "symbol": "FCFA",
                        "fraction_units": 0, "enabled": 1}).insert(ignore_permissions=True)
    frappe.db.set_value("Currency", "XOF", "enabled", 1)
    s = frappe.get_single("System Settings")
    s.update({"language": "fr", "time_zone": "Africa/Abidjan", "currency": "XOF",
              "date_format": "dd-mm-yyyy", "country": "Cote d'Ivoire"})
    s.save(ignore_permissions=True)
    w = frappe.get_single("Website Settings")
    w.update({"app_name": "OpenLab Academy", "app_logo": "/assets/openlab_academy/images/logo.svg",
              "favicon": "/assets/openlab_academy/images/logo.svg"})
    w.save(ignore_permissions=True)
    lms = frappe.get_single("LMS Settings")
    lms.update({"default_currency": "XOF", "certifications": 1, "batches": 1, "courses": 1})
    lms.save(ignore_permissions=True)


def after_install() -> None:
    appliquer_reglages()
    loader.run()
```
  Si `country` « Cote d'Ivoire » est refusé, lire le nom exact : `frappe.db.get_value("Country", {"code": "ci"})`.
- [ ] **4.3** `hooks.py` : ajouter `after_install = "openlab_academy.install.after_install"`, `app_include_css = ["/assets/openlab_academy/css/openlab.css"]`, `web_include_css = ["/assets/openlab_academy/css/openlab.css"]`.
- [ ] **4.4** `openlab.css` : `@import` Google Fonts (Geist, Bricolage Grotesque, JetBrains Mono) ; `:root` tokens `--ol-*` de la spec ; surcharge des variables frappe-ui (identifier les noms réels dans `apps/lms/frontend/node_modules/frappe-ui/src/style.css` / tailwind preset — ex. `--primary`, couleurs `gray-900` des boutons primaires) ; titres en Bricolage Grotesque, corps en Geist, `code` en JetBrains Mono ; boutons primaires navy, accents/progression orange. Le front LMS (`/lms`) est une SPA Vue : si `web_include_css` n'y est pas chargé, ajouter le hook `lms` documenté (`lms_head_html` / injection via `website_context`) après lecture de `apps/lms/lms/www/lms.py`.
- [ ] **4.5** `logo.svg` : wordmark « OpenLab Academy » (texte navy, « Lab » orange, police système), 160×32.
- [ ] **4.6** `dev-sync.sh`, `bench build --app openlab_academy`, tests → PASS ; capture visuelle `/lms` et `/lms/courses/...` (orange < 15 %).
- [ ] **4.7** Commit : `feat(academy): réglages fr/XOF et habillage OpenLab`.

### Tâche 5 : cohorte pilote

**Fichiers :** Créer `openlab_academy/seed/cohorte.py`, `openlab_academy/tests/test_cohorte.py` ; modifier `install.py` (`after_install` appelle `cohorte.creer_pilote()`).

**Interfaces :** produit `cohorte.creer_pilote(debut: datetime.date | None = None) -> str` (nom du `LMS Batch`, idempotent par titre).

- [ ] **5.1** Test en échec :
```python
import frappe
from frappe.tests.utils import FrappeTestCase

from openlab_academy.seed import cohorte, loader


class TestCohorte(FrappeTestCase):
    def test_pilote(self):
        loader.run(commit=False)
        nom = cohorte.creer_pilote()
        self.assertEqual(cohorte.creer_pilote(), nom)
        b = frappe.get_doc("LMS Batch", nom)
        self.assertEqual(b.courses[0].course, frappe.db.get_value("LMS Course", {"title": cohorte.COURS}))
        self.assertEqual((b.paid_batch, b.timezone, b.medium), (0, "Africa/Abidjan", "Online"))
```
- [ ] **5.2** `seed/cohorte.py` :
```python
import datetime

import frappe

TITRE = "Promo 1 — Fondamentaux Data Science"
COURS = "Fondamentaux de la Data Science"
SEMAINES = 25  # 10 modules + 10 semaines projet (~12 h) + 3 capstone + 2 marge


def creer_pilote(debut: datetime.date | None = None) -> str:
    existant = frappe.db.get_value("LMS Batch", {"title": TITRE})
    if existant:
        return existant
    debut = debut or datetime.date.today() + datetime.timedelta(days=14)
    return frappe.get_doc({
        "doctype": "LMS Batch", "title": TITRE, "published": 1, "medium": "Online",
        "start_date": debut, "end_date": debut + datetime.timedelta(weeks=SEMAINES),
        "start_time": "18:30:00", "end_time": "20:30:00", "timezone": "Africa/Abidjan",
        "description": "Cohorte pilote du socle commun, en soirée.",
        "batch_details": "<p>1 module par semaine, semaines projet intercalées, capstone devant jury.</p>",
        "instructors": [{"instructor": "Administrator"}],
        "courses": [{"course": frappe.db.get_value("LMS Course", {"title": COURS})}],
        "allow_self_enrollment": 1, "certification": 1, "evaluation": 1,
    }).insert(ignore_permissions=True).name
```
- [ ] **5.3** Tests PASS ; `bench --site lms.localhost execute openlab_academy.seed.cohorte.creer_pilote` ; cohorte visible sur `/lms/batches`.
- [ ] **5.4** Commit : `feat(academy): cohorte pilote Promo 1`.

### Tâches 6 à 8 bis : contenu des 5 parcours (portfolio + capstone)

Pour chaque parcours : un fichier `seed/parcours/NN-<slug>.yaml` ; modules recopiés de `catalogue-source.txt` (sans rémunération) ; 10 fiches projet + capstone complètes au format de la Tâche 2. Règles de rédaction :
- `contexte` : cas réel Côte d'Ivoire / Afrique de l'Ouest, avec données ouvertes ou générables (citer la source ou fournir un générateur).
- `fonctionnalites` : périmètre d'un produit utilisable, pas un exercice.
- `stack` : outils actuels 2026 (uv, ruff, pyright/mypy, Pydantic v2, FastAPI, pytest, Polars, DuckDB, dbt, Dagster/Airflow, Docker Compose, GitHub Actions…).
- `criteres_acceptation` : ≥ 5, vérifiables, dont « démarre avec `docker compose up` », « tests et CI verts », « démo de bout en bout ».
- Niveaux : projets 1–3 `guide`, 4–7 `semi-guide`, 8–10 `autonome` ; capstone `autonome`, `duree_h: 60`.
- Cyber : tout exercice offensif uniquement sur lab fourni/possédé, rappel légal dans `contexte`.

Après chaque fichier : `dev-sync.sh`, `test_schema` PASS, `loader.run` → statut `cree`/`maj`, contrôle visuel, commit `feat(academy): contenu du parcours <nom>`.

**Tâche 6 — Parcours 0 · Fondamentaux de la Data Science** (relecture de la fiche écrite en 2.4)
| # | apres_module | Projet |
|---|---|---|
| 1 | 03 | Calculateur de budget ménage en FCFA (CLI Python testée) |
| 2 | 04 | Rapport statistique des prix des denrées sur les marchés d'Abidjan |
| 3 | 05 | Test A/B d'un SMS de relance de paiement Mobile Money (simulation + inférence) |
| 4 | 06 | Régression linéaire from scratch (NumPy) : loyers à Cocody |
| 5 | 07 | Pipeline de nettoyage de données publiques (INS / data.gouv.ci) packagé |
| 6 | 08 | Dashboard Streamlit pluviométrie × production de cacao |
| 7 | 09 | Base DuckDB des ventes d'une PME + requêtes analytiques + API lecture |
| 8 | 10 | Scoring de risque de microcrédit (scikit-learn, pipeline, évaluation) |
| 9 | 10 | Segmentation des clients d'un opérateur télécom (clustering) |
| 10 | 10 | Prédiction de rendement agricole servie en API FastAPI conteneurisée |
| C | — | Observatoire data d'un secteur au choix : étude complète + application de restitution |

**Tâche 7 — Parcours I · Développeur Python** (`01-developpeur-python.yaml`)
| # | apres_module | Projet |
|---|---|---|
| 1 | 02 | Carnet de contacts CLI persistant (JSON) |
| 2 | 03 | Convertisseur FCFA/EUR/USD modulaire avec taux via API |
| 3 | 04 | Gestion de stock d'une boutique (POO, domaine riche) |
| 4 | 05 | Rapprochement de relevés Mobile Money (CSV) robuste |
| 5 | 06 | Bibliothèque de validation : téléphones CI, CNI, IBAN UEMOA |
| 6 | 07 | Package publié `fcfa` : formatage et montants en lettres |
| 7 | 08 | Moteur de réservation de cars interurbains, tests + CI |
| 8 | 09 | Agrégateur asynchrone météo/prix agricoles (httpx, rate limit) |
| 9 | 10 | API de gestion scolaire (FastAPI, SQLAlchemy 2, Alembic) |
| 10 | 11 | Pipeline d'analyse des ventes d'un e-commerce |
| C | — | SaaS de gestion de tontines : API, auth, front minimal, Docker, CI |

**Tâche 8 — Parcours II · AI Engineer** (`02-ai-engineer.yaml`)
| # | apres_module | Projet |
|---|---|---|
| 1 | 01 | Client async typé et testé pour une API publique |
| 2 | 02 | Passerelle LLM multi-fournisseurs avec retry et suivi des coûts en FCFA |
| 3 | 03 | Extracteur structuré de factures et reçus (sorties JSON validées) |
| 4 | 04 | Assistant documentaire Code du travail ivoirien (RAG hybride + citations) |
| 5 | 05 | Benchmark pgvector vs Qdrant sur un corpus juridique OHADA |
| 6 | 06 | Agent service client e-commerce connecté à 3 outils |
| 7 | 07 | Serveur MCP exposant l'ERP d'une PME |
| 8 | 08 | Instruction multi-agents d'un dossier de crédit avec validation humaine |
| 9 | 10 | Suite d'évals en CI pour l'assistant RAG du projet 4 |
| 10 | 12 | Assistant agricole WhatsApp avec guardrails et observabilité |
| C | — | Copilote IA métier en production : RAG, agents, evals, guardrails, observabilité |

**Tâche 8 bis — Parcours III · Data Engineer** (`03-data-engineer.yaml`) et **Parcours IV · Ingénieur Cybersécurité** (`04-cybersecurite.yaml`) — un commit par fichier.

Data Engineer :
| # | apres_module | Projet |
|---|---|---|
| 1 | 01 | Modèle SQL et requêtes analytiques du transport urbain abidjanais |
| 2 | 02 | Ingestion idempotente d'API open data vers Parquet (Polars) |
| 3 | 04 | Entrepôt en étoile d'un distributeur (DuckDB) |
| 4 | 05 | Projet dbt complet : tests, documentation, snapshots |
| 5 | 06 | Traitement Spark de transactions Mobile Money à volume |
| 6 | 07 | Suivi de colis en temps réel avec Kafka |
| 7 | 08 | Orchestration du pipeline de bout en bout (Airflow ou Dagster) |
| 8 | 09 | Plateforme data locale conteneurisée (Postgres, MinIO, orchestrateur) |
| 9 | 11 | Lakehouse cloud BigQuery/Snowflake à coûts maîtrisés |
| 10 | 12 | Qualité et observabilité des données avec alertes |
| C | — | Plateforme data d'une filière (cacao/anacarde) : batch + stream, modélisation, qualité, dashboard |

Cybersécurité :
| # | apres_module | Projet |
|---|---|---|
| 1 | 01 | Analyseur de trafic réseau (Scapy) sur lab |
| 2 | 02 | Durcissement Linux automatisé (Ansible) + rapport CIS |
| 3 | 03 | Scanner de ports et bannières asynchrone en Python |
| 4 | 04 | Application vulnérable puis corrigée (OWASP Top 10) + tests de sécurité |
| 5 | 06 | Détection d'intrusion sur PCAP (Suricata/Zeek, règles maison) |
| 6 | 07 | Audit d'une application web de démo + rapport professionnel |
| 7 | 08 | Pentest interne d'un lab + rapport et plan de remédiation |
| 8 | 09 | Lab Active Directory : attaque, détection, durcissement |
| 9 | 10 | SOC maison : Wazuh/Elastic, règles Sigma, tableaux de bord |
| 10 | 11 | Audit et correction IaC cloud (Terraform + Checkov/Prowler) |
| C | — | Réponse à incident complète sur rançongiciel simulé dans une PME : détection, investigation, remédiation, playbooks |

(Splunk remplacé par Wazuh/Elastic, sans licence.)

### Tâche 9 : image Docker figée et compose

**Fichiers :** Créer `docker/Dockerfile`, `docker/docker-compose.yml`, `docker/entrypoint.sh`, `docker/.env.example` ; supprimer `poc/` en fin de tâche.

- [ ] **9.1** `Dockerfile` :
```dockerfile
FROM frappe/bench@sha256:1b27bb30ab18b0a50b5264f44988335bfe8e280a68b45d0ff2daf72ca6ddb85f
USER frappe
WORKDIR /home/frappe
ARG LMS_REF=aa8b53b0a7e940871cdb006962a212daccb52a09
RUN bench init --frappe-branch version-15 --skip-redis-config-generation --skip-assets frappe-bench
WORKDIR /home/frappe/frappe-bench
RUN bench get-app --skip-assets payments --branch version-15 \
 && bench get-app --skip-assets lms https://github.com/frappe/lms \
 && cd apps/lms && git fetch --depth 1 origin "$LMS_REF" && git checkout "$LMS_REF"
COPY --chown=frappe:frappe apps/openlab_academy apps/openlab_academy
RUN ./env/bin/pip install -e apps/openlab_academy \
 && printf "frappe\npayments\nlms\nopenlab_academy" > sites/apps.txt \
 && (cd apps/lms && yarn install --network-timeout 600000) \
 && bench build
RUN sed -i '/redis/d;/watch/d' Procfile
COPY --chown=frappe:frappe docker/entrypoint.sh /home/frappe/entrypoint.sh
EXPOSE 8000 9000
ENTRYPOINT ["bash", "/home/frappe/entrypoint.sh"]
```
- [ ] **9.2** `entrypoint.sh` :
```bash
#!/usr/bin/env bash
set -euo pipefail
cd /home/frappe/frappe-bench
bench set-mariadb-host mariadb
bench set-redis-cache-host redis://redis:6379
bench set-redis-queue-host redis://redis:6379
bench set-redis-socketio-host redis://redis:6379
if [ ! -f "sites/${SITE_NAME}/site_config.json" ]; then
  bench new-site "$SITE_NAME" --mariadb-root-password "$DB_ROOT_PASSWORD" \
    --admin-password "$ADMIN_PASSWORD" --mariadb-user-host-login-scope='%'
  for app in payments lms openlab_academy; do bench --site "$SITE_NAME" install-app "$app"; done
fi
bench use "$SITE_NAME"
exec bench start
```
- [ ] **9.3** `docker-compose.yml` (v1, contexte = `Openlab_Academy/`) :
```yaml
version: "3.7"
services:
  mariadb:
    image: mariadb:11.4
    command: [--character-set-server=utf8mb4, --collation-server=utf8mb4_unicode_ci, --skip-character-set-client-handshake]
    environment:
      MARIADB_ROOT_PASSWORD: ${DB_ROOT_PASSWORD}
    volumes: [mariadb-data:/var/lib/mysql]
  redis:
    image: redis:7.4-alpine
  app:
    build: { context: .., dockerfile: docker/Dockerfile }
    image: openlab-academy:0.1.0
    env_file: .env
    depends_on: [mariadb, redis]
    ports: ["8000:8000", "9000:9000"]
    volumes: [sites:/home/frappe/frappe-bench/sites]
volumes:
  mariadb-data:
  sites:
```
  Attention : le volume `sites` masque `sites/apps.txt` et `sites/assets` construits dans l'image au premier montage seulement si le volume est vide (Docker copie alors le contenu de l'image) — vérifier à l'étape 9.5 que `apps.txt` et `assets/` sont présents.
- [ ] **9.4** `.env.example` : `SITE_NAME=academy.localhost`, `DB_ROOT_PASSWORD=changeme`, `ADMIN_PASSWORD=changeme`. Copier en `.env` local (non versionné).
- [ ] **9.5** Arrêter le POC (`docker-compose -p openlab-academy stop` dans `poc/`, libère 8000). Build en premier plan : `docker-compose -p ol-academy -f docker/docker-compose.yml build` (lancé par l'utilisateur via `!` si la mémoire est juste) ; puis `up -d` ; attendu : `http://localhost:8000/lms` (Host `academy.localhost`) habillé, 5 parcours, cohorte. `docker-compose ... restart app` → site conservé, pas de `new-site` dans les logs.
- [ ] **9.6** Supprimer `poc/` (après accord utilisateur, `down -v` du POC) ; commit `feat(academy): image Docker figée et compose reproductible`.

### Tâche 10 : vérification de bout en bout

- [ ] **10.1** Sur l'image finale : créer un utilisateur apprenant (`/signup` ou Desk), l'inscrire à la Promo 1, ouvrir le module 01, rendre le devoir (URL), ouvrir un énoncé de projet.
- [ ] **10.2** Côté Administrator : la soumission apparaît dans `/lms/assignment-submissions`, notable.
- [ ] **10.3** `bench --site academy.localhost run-tests --app openlab_academy` → tout PASS (après `set-config allow_tests true`).
- [ ] **10.4** Mettre à jour le README (lancement, seed, ajout d'un parcours) ; commit `docs(academy): guide d'exploitation du socle`.
