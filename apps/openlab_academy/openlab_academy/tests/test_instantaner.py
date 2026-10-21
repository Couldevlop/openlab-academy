"""Cas d'usage : instantané du dépôt rendu par lien, pris en tâche de fond après le rendu."""
from dataclasses import replace

from openlab_academy.application.chaine import SYSTEME
from openlab_academy.application.controler import EtapeIndisponible
from openlab_academy.application.instantaner import PrendreInstantane
from openlab_academy.application.soumettre_copie import Contenu
from openlab_academy.domain.copie import EtatInstantane, Statut
from openlab_academy.domain.reglages_evaluation import Etape
from openlab_academy.tests.test_chaine import Cas, chaine

URL = "https://github.com/aya/livrable"
SHA = "a" * 40
EN_COURS = Contenu("", URL, "", "sig", "SUB1", EtatInstantane.EN_COURS)


class Instantane:
    def __init__(self, resultat=("=== README.md ===\nLisez-moi", SHA), erreur=None):
        self.resultat, self.erreur, self.appels = resultat, erreur, []

    def prendre(self, url):
        self.appels.append(url)
        if self.erreur:
            raise self.erreur
        return self.resultat


class TestPrendreInstantane(Cas):
    def setUp(self):
        self.monter(yaml=chaine(Etape.CONTROLES, Etape.IA, Etape.FORMATEUR))
        self.a = self.rendre("a@x.ci")
        self.m.contenus[self.a] = EN_COURS
        self.file.clear()

    def prendre(self, instantane):
        PrendreInstantane(self.m, instantane, lambda *a: self.file.append(a),
                          lambda *a: self.journal.append(a)).executer(self.a)

    def test_instantane_fige_puis_l_etape_en_attente_relancee(self):
        instantane = Instantane()
        self.prendre(instantane)
        self.assertEqual(instantane.appels, [URL])
        self.assertEqual(self.m.contenu(self.a), replace(EN_COURS, texte="=== README.md ===\nLisez-moi", commit=SHA,
                                                        instantane=EtatInstantane.PRIS))
        self.assertEqual(self.journal[-1][1:], (SYSTEME, "instantané pris", {}, {"commit": SHA}))
        self.assertEqual(self.file, [("controler", self.a)])  # les contrôles attendaient l'instantané

    def test_hebergeur_indisponible_la_chaine_continue_sans_instantane(self):
        self.prendre(Instantane(erreur=EtapeIndisponible("délai total dépassé")))
        contenu = self.m.contenu(self.a)
        self.assertEqual((contenu.texte, contenu.instantane), ("", EtatInstantane.INDISPONIBLE))
        self.assertEqual(self.journal[-1][2:], ("instantané indisponible", {}, {"cause": "délai total dépassé"}))
        self.assertEqual(self.file, [("controler", self.a)])
        self.prendre(Instantane(erreur=RuntimeError("détail interne")))  # déjà tranché : rien de plus
        self.assertEqual(len([j for j in self.journal if j[2] == "instantané indisponible"]), 1)

    def test_erreur_imprevue_consignee_par_son_type_seul(self):
        self.prendre(Instantane(erreur=ValueError("dépôt introuvable ou privé")))
        self.assertEqual(self.journal[-1][4], {"cause": "ValueError"})

    def test_rien_a_prendre(self):
        for contenu in (Contenu("texte", "", "", "sig", "SUB1"), replace(EN_COURS, instantane=EtatInstantane.PRIS)):
            self.m.contenus[self.a] = contenu
            instantane = Instantane()
            self.prendre(instantane)
            self.assertEqual((instantane.appels, self.m.contenu(self.a)), ([], contenu))

    def test_version_remplacee_pendant_la_prise_rien_n_est_fige(self):
        instantane = Instantane()
        prendre = instantane.prendre

        def remplacee_pendant(url):  # un nouveau rendu remplace la copie pendant l'appel au dépôt
            self.m.copies[self.a] = replace(self.m.copies[self.a], statut=Statut.REMPLACEE)
            return prendre(url)
        instantane.prendre = remplacee_pendant
        self.prendre(instantane)
        self.assertEqual((self.m.contenu(self.a), self.file), (EN_COURS, []))

    def test_etape_sans_attente_pas_de_relance(self):
        self.avancer.executer(self.a, Etape.CONTROLES)
        self.avancer.executer(self.a, Etape.IA)
        self.file.clear()
        self.prendre(Instantane())
        self.assertEqual((self.m.contenu(self.a).instantane, self.file), (EtatInstantane.PRIS, []))

    def test_pre_correction_en_attente_relancee(self):
        self.avancer.executer(self.a, Etape.CONTROLES)
        self.file.clear()
        self.prendre(Instantane())
        self.assertEqual(self.file, [("pre_corriger", self.a)])
