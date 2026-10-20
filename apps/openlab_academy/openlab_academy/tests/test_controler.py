"""Cas d'usage : contrôles automatiques d'une copie dans la chaîne de correction."""
from dataclasses import replace

from openlab_academy.application.chaine import SYSTEME
from openlab_academy.application.controler import ControlerCopie, EtapeIndisponible
from openlab_academy.domain.copie import Proposition, Source, Statut
from openlab_academy.domain.reglages_evaluation import Etape
from openlab_academy.tests.test_chaine import Cas, chaine


class Controleur:
    def __init__(self, motifs=(), erreur=None):
        self.motifs, self.erreur, self.appels = list(motifs), erreur, []

    def verifier(self, copie, grille, contenu):
        self.appels.append((copie.id, grille, contenu))
        if self.erreur:
            raise self.erreur
        return self.motifs


class TestControlerCopie(Cas):
    def setUp(self):
        self.monter(yaml=chaine(Etape.CONTROLES, Etape.IA, Etape.FORMATEUR))
        self.a = self.rendre("a@x.ci")

    def controler(self, controleur):
        ControlerCopie(self.m, controleur, self.avancer, lambda *a: self.journal.append(a),
                       lambda *a: self.notes.append(a)).executer(self.a)

    def test_controles_conformes_font_avancer(self):
        controleur = Controleur()
        self.controler(controleur)
        self.assertEqual(controleur.appels, [(self.a, self.m.grille(self.a), self.m.contenu(self.a))])
        self.assertEqual(self.m.propositions(self.a), [Proposition(Source.CONTROLES, SYSTEME, {}, {})])
        self.assertEqual(self.etape(self.a), ("ia", Statut.CONTROLEE))
        self.assertIn("contrôles conformes", self.actions())
        self.assertEqual(self.notes, [])

    def test_echec_bloquant_renvoie_la_copie_avec_ses_motifs(self):
        self.controler(Controleur(["copie trop courte", "fichier attendu absent : README"]))
        self.assertEqual(self.m.propositions(self.a), [Proposition(
            Source.CONTROLES, SYSTEME, {}, {"motif_1": "copie trop courte", "motif_2": "fichier attendu absent : README"})])
        self.assertEqual(self.etape(self.a), ("", Statut.RENVOYEE))
        self.assertIsNone(self.m.etat(self.a).echeance)
        self.assertEqual(self.journal[-1][1:], (SYSTEME, "copie renvoyée", {"statut": "rendue"},
                                                {"motifs": ["copie trop courte", "fichier attendu absent : README"]}))
        ((destinataire, message),) = self.notes
        self.assertEqual(destinataire, "a@x.ci")
        self.assertIn("copie trop courte ; fichier attendu absent : README", message)
        self.assertNotIn(("pre_corriger", self.a), self.file)

    def test_controles_indisponibles_la_copie_avance(self):
        self.controler(Controleur(erreur=EtapeIndisponible("hébergeur injoignable (Timeout)")))
        self.assertEqual(self.etape(self.a), ("ia", Statut.CONTROLEE))
        self.assertEqual(self.m.propositions(self.a), [])
        self.assertEqual(self.journal[-2][1:], (SYSTEME, "contrôles non disponibles", {},
                                                {"etape": "controles", "cause": "hébergeur injoignable (Timeout)"}))

    def test_erreur_imprevue_consignee_par_son_type_seul(self):
        self.controler(Controleur(erreur=RuntimeError("détail interne")))
        self.assertEqual(self.etape(self.a), ("ia", Statut.CONTROLEE))
        self.assertEqual(self.journal[-2][4], {"etape": "controles", "cause": "RuntimeError"})

    def test_signal_perime_ignore(self):
        self.avancer.executer(self.a, Etape.CONTROLES)
        avant = list(self.journal)
        self.controler(Controleur(["trop court"]))
        self.controler(Controleur(erreur=EtapeIndisponible("panne")))
        self.assertEqual((self.journal, self.m.propositions(self.a), self.notes), (avant, [], []))
        self.m.copies[self.a] = replace(self.m.copies[self.a], statut=Statut.PUBLIEE)
        self.controler(Controleur())
        self.assertEqual(self.journal, avant)
