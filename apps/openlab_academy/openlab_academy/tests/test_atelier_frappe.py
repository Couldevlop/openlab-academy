"""Atelier de code : la page exige une session, l'API ne remet que les fichiers texte du dépôt de la leçon.

Le serveur n'exécute rien et n'écrit rien : l'atelier tourne dans le navigateur de l'apprenant (OWASP A03).
L'accès est celui de la leçon, par trois barrières indépendantes — parcours refusé, parcours bloqué, leçon
inaccessible (OWASP A01) — et chacune est vérifiée seule ici, sinon une barrière tombée resterait masquée par
les deux autres. Le nom de l'archive ne vient jamais du client : il est relu sur la leçon.
"""
import dataclasses
import os
import pathlib
import tempfile
import zipfile
from unittest import mock

import frappe
from frappe.tests.utils import FrappeTestCase

from openlab_academy.domain.parcours import Bloc
from openlab_academy.domain.reglages import Reglages
from openlab_academy.entrypoints import atelier_api
from openlab_academy.infrastructure.depot_frappe import DepotFrappe
from openlab_academy.infrastructure.depot_ouvertures_frappe import CHAMP_DELAI
from openlab_academy.patches import delai_exercices_non_regle
from openlab_academy.tests.fabriques import parcours
from openlab_academy.tests.test_exercices_frappe import module
from openlab_academy.www import atelier

# archive réellement livrée avec l'application : cinq fichiers texte, aucun dossier, aucun corrigé
ARCHIVE = "depot-python-j01.zip"


def _parcours(titre, archive=""):
    seance = dataclasses.replace(module(), archive=archive)
    return parcours(title=titre, questions_par_quiz=5, blocs=(Bloc("B1", (seance,)),))


class TestAtelierApi(FrappeTestCase):
    def setUp(self):
        self.depot = DepotFrappe(commit=False, reglages=Reglages())
        self.cours = self.depot.creer(_parcours("Parcours atelier test", ARCHIVE))
        self.lecon = frappe.db.get_value("Course Lesson",
                                         {"course": self.cours, "title": ["like", "01 ·%"]})

    def tearDown(self):
        frappe.set_user("Administrator")
        frappe.db.rollback()

    # --- ce que l'atelier reçoit ---------------------------------------------------------------

    def test_ouvrir_remet_les_fichiers_texte_du_depot(self):
        vu = atelier_api.ouvrir(self.lecon)
        self.assertEqual(vu["lecon"], self.lecon)
        self.assertEqual(vu["archive"], ARCHIVE)
        self.assertTrue(vu["titre"].startswith("01 ·"))
        noms = [f["nom"] for f in vu["fichiers"]]
        self.assertEqual(noms, sorted(noms))
        self.assertIn("fiche.py", noms)
        self.assertIn("tests/test_j01.py", noms)
        fiche = next(f for f in vu["fichiers"] if f["nom"] == "fiche.py")
        self.assertIsInstance(fiche["contenu"], str)
        self.assertTrue(fiche["contenu"].strip())

    def test_rien_n_est_ecrit_en_base(self):
        avant = frappe.db.get_value("Course Lesson", self.lecon, "content")
        atelier_api.ouvrir(self.lecon)
        self.assertEqual(frappe.db.get_value("Course Lesson", self.lecon, "content"), avant)

    def test_titre_vide_rend_le_nom_de_la_lecon(self):
        frappe.db.set_value("Course Lesson", self.lecon, "title", "")
        self.assertEqual(atelier_api.ouvrir(self.lecon)["titre"], self.lecon)

    # --- les trois barrières, une par une ------------------------------------------------------

    def test_lecon_introuvable_refusee(self):
        with self.assertRaises(frappe.DoesNotExistError):
            atelier_api.ouvrir("lecon-qui-n-existe-pas")

    def test_parcours_refuse_pour_le_membre(self):
        with mock.patch.object(atelier_api.controle, "refus_pour", return_value="parcours fermé"):
            with self.assertRaises(frappe.PermissionError):
                atelier_api.ouvrir(self.lecon)

    def test_parcours_bloque_pour_le_membre(self):
        with mock.patch.object(atelier_api.controle, "bloque_pour", return_value=True):
            with self.assertRaises(frappe.PermissionError):
                atelier_api.ouvrir(self.lecon)

    def test_lecon_inaccessible_refusee(self):
        with mock.patch.object(atelier_api, "can_access_lesson", return_value=False):
            with self.assertRaises(frappe.PermissionError):
                atelier_api.ouvrir(self.lecon)

    def test_lecon_sans_depot(self):
        cours = self.depot.creer(_parcours("Parcours atelier sans depot"))
        lecon = frappe.db.get_value("Course Lesson", {"course": cours, "title": ["like", "01 ·%"]})
        with self.assertRaises(frappe.DoesNotExistError):
            atelier_api.ouvrir(lecon)

    # --- ce que l'atelier n'ouvre pas ----------------------------------------------------------

    def test_dossiers_corriges_fichiers_lourds_et_binaires_sont_ecartes(self):
        dossier = tempfile.TemporaryDirectory()
        self.addCleanup(dossier.cleanup)
        chemin = pathlib.Path(dossier.name) / "melange.zip"
        with zipfile.ZipFile(chemin, "w") as zip_:
            zip_.writestr("tri/", "")                                   # dossier
            zip_.writestr("corrige/solution.py", "print('triche')")     # corrigé du jour
            zip_.writestr("gros.py", "x" * (atelier_api.TAILLE_MAX + 1))  # trop gros pour être édité
            zip_.writestr("capture.png", b"\x89PNG")                    # pas du code
            zip_.writestr("b.py", "b = 2")
            zip_.writestr("a.md", "# a")
        with mock.patch.object(atelier_api.ressources_frappe, "chemin", return_value=chemin):
            fichiers = atelier_api.ouvrir(self.lecon)["fichiers"]
        self.assertEqual([f["nom"] for f in fichiers], ["a.md", "b.py"])

    def test_le_corrige_est_ecarte_meme_sous_un_dossier_de_tete(self):
        """Une archive de carnet range tout sous un dossier de tête : « corrige/ » s'y trouve décalé, et un
        simple début de chemin le laisserait passer — soit le corrigé servi à l'apprenant."""
        fichiers = self._fichiers_de({"carnet-01/corrige/solution.py": "print('triche')",
                                      "carnet-01/seance.py": "x = 1"})
        self.assertEqual([f["nom"] for f in fichiers], ["carnet-01/seance.py"])

    def test_le_carnet_jupyter_est_remis_a_l_atelier(self):
        """Le carnet s'exécute dans le navigateur, cellule par cellule : il doit donc être remis comme
        n'importe quel fichier de code, et pas seulement téléchargé en archive."""
        carnet = '{"nbformat": 4, "cells": [{"cell_type": "code", "source": ["x = 1"]}]}'
        fichiers = self._fichiers_de({"carnet-02/seance-02.ipynb": carnet})
        self.assertEqual([f["nom"] for f in fichiers], ["carnet-02/seance-02.ipynb"])
        self.assertEqual(fichiers[0]["contenu"], carnet)

    def _fichiers_de(self, entrees):
        """Remet les fichiers que l'atelier retiendrait d'une archive faite pour l'occasion."""
        dossier = tempfile.TemporaryDirectory()
        self.addCleanup(dossier.cleanup)
        chemin = pathlib.Path(dossier.name) / "fabrique.zip"
        with zipfile.ZipFile(chemin, "w") as zip_:
            for nom, contenu in entrees.items():
                zip_.writestr(nom, contenu)
        with mock.patch.object(atelier_api.ressources_frappe, "chemin", return_value=chemin):
            return atelier_api.ouvrir(self.lecon)["fichiers"]


class TestPageAtelier(FrappeTestCase):
    def tearDown(self):
        frappe.set_user("Administrator")
        frappe.db.rollback()

    def contexte(self, lecon=None):
        donnees = {"lecon": lecon} if lecon is not None else {}
        with mock.patch.object(frappe.local, "form_dict", frappe._dict(donnees)):
            return atelier.get_context(frappe._dict())

    def test_visiteur_refuse(self):
        frappe.set_user("Guest")
        with self.assertRaises(frappe.PermissionError):
            self.contexte("une-lecon")

    def test_contexte_porte_la_lecon_le_jeton_et_la_version(self):
        contexte = self.contexte("une-lecon")
        self.assertEqual(contexte.lecon, "une-lecon")
        self.assertEqual(contexte.no_cache, 1)
        self.assertTrue(contexte.csrf_token)
        self.assertEqual(contexte.version, atelier.version())

    def test_lecon_absente_donne_une_chaine_vide(self):
        self.assertEqual(self.contexte().lecon, "")

    def test_version_suit_le_plus_recent_des_paquets_servis(self):
        if not all(os.path.exists(paquet) for paquet in atelier.PAQUETS):
            self.assertEqual(atelier.version(), "0")  # paquet non construit : la page reste servie
            return
        attendu = max(os.path.getmtime(paquet) for paquet in atelier.PAQUETS)
        self.assertEqual(atelier.version(), str(int(attendu)))

    def test_le_carnet_compte_dans_l_empreinte(self):
        """Une correction du carnet seul doit sortir du cache du navigateur : elle change la version."""
        atelier_js, carnet_js = atelier.PAQUETS

        def plus_tard(chemin):
            return 2000.0 if chemin == carnet_js else 1000.0

        with mock.patch.object(os.path, "getmtime", side_effect=plus_tard):
            self.assertEqual(atelier.version(), "2000")

    def test_version_vaut_zero_quand_le_paquet_manque(self):
        with mock.patch.object(os.path, "getmtime", side_effect=OSError):
            self.assertEqual(atelier.version(), "0")


class TestPatchDelaiNonRegle(FrappeTestCase):
    """Le zéro des parcours déjà publiés voulait dire « rien de réglé » : il devient -1."""

    def setUp(self):
        self.cours = DepotFrappe(commit=False, reglages=Reglages()).creer(
            _parcours("Parcours delai patch test"))

    def tearDown(self):
        frappe.db.rollback()

    def delai(self):
        return frappe.db.get_value("LMS Course", self.cours, CHAMP_DELAI)

    def test_zero_devient_moins_un(self):
        frappe.db.set_value("LMS Course", self.cours, CHAMP_DELAI, 0)
        delai_exercices_non_regle.execute()
        self.assertEqual(self.delai(), -1)

    def test_delai_choisi_est_conserve(self):
        frappe.db.set_value("LMS Course", self.cours, CHAMP_DELAI, 30)
        delai_exercices_non_regle.execute()
        self.assertEqual(self.delai(), 30)

    def test_sans_la_colonne_le_patch_ne_fait_rien(self):
        frappe.db.set_value("LMS Course", self.cours, CHAMP_DELAI, 0)
        with mock.patch.object(frappe.db, "has_column", return_value=False):
            delai_exercices_non_regle.execute()
        self.assertEqual(self.delai(), 0)
