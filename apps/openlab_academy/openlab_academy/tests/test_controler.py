"""Cas d'usage : contrôles automatiques d'une copie dans la chaîne de correction."""
from dataclasses import replace

from openlab_academy.application.chaine import SYSTEME
from openlab_academy.application.controler import ControlerCopie, EtapeIndisponible
from openlab_academy.application.soumettre_copie import Contenu
from openlab_academy.domain.copie import Proposition, Source, Statut
from openlab_academy.domain.reglages_evaluation import Etape
from openlab_academy.tests.test_chaine import Cas, chaine

URL = "https://github.com/aya/livrable"
SHA = "a" * 40


class Controleur:
    def __init__(self, motifs=(), erreur=None):
        self.motifs, self.erreur, self.appels = list(motifs), erreur, []

    def verifier(self, copie, grille, contenu):
        self.appels.append((copie.id, grille, contenu))
        if self.erreur:
            raise self.erreur
        return self.motifs


class Instantane:
    def __init__(self, resultat=None, erreur=None):
        self.resultat, self.erreur, self.appels = resultat, erreur, []

    def prendre(self, url):
        self.appels.append(url)
        if self.erreur:
            raise self.erreur
        return self.resultat


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

    def rendu_url_sans_instantane(self):
        self.m.contenus[self.a] = Contenu("", URL, "", "sig", "SUB1")

    def controler_avec(self, controleur, instantane):
        ControlerCopie(self.m, controleur, self.avancer, lambda *a: self.journal.append(a),
                       lambda *a: self.notes.append(a), instantane).executer(self.a)

    def test_instantane_manquant_repris_et_fige_avant_les_controles(self):
        self.rendu_url_sans_instantane()
        controleur, instantane = Controleur(), Instantane(("=== README.md ===\nLisez-moi", SHA))
        self.controler_avec(controleur, instantane)
        self.assertEqual(instantane.appels, [URL])
        fige = Contenu("=== README.md ===\nLisez-moi", URL, SHA, "sig", "SUB1")
        self.assertEqual(controleur.appels[0][2], fige)
        self.assertEqual(self.m.contenu(self.a), fige)
        self.assertEqual(self.etape(self.a), ("ia", Statut.CONTROLEE))

    def test_reprise_indisponible_etape_non_disponible_rien_de_fige(self):
        self.rendu_url_sans_instantane()
        controleur = Controleur()
        self.controler_avec(controleur, Instantane(erreur=EtapeIndisponible("délai total dépassé")))
        self.assertEqual((controleur.appels, self.m.contenu(self.a).texte), ([], ""))
        self.assertEqual(self.journal[-2][2:], ("contrôles non disponibles", {},
                                                {"etape": "controles", "cause": "délai total dépassé"}))
        self.assertEqual(self.etape(self.a), ("ia", Statut.CONTROLEE))

    def test_reprise_refusee_le_controleur_donne_le_motif(self):
        self.rendu_url_sans_instantane()
        controleur = Controleur(["dépôt introuvable ou privé"])
        self.controler_avec(controleur, Instantane(erreur=ValueError("dépôt introuvable ou privé")))
        self.assertEqual(controleur.appels[0][2].texte, "")
        self.assertEqual(self.etape(self.a), ("", Statut.RENVOYEE))

    def test_texte_ou_instantane_present_pas_de_reprise(self):
        instantane = Instantane(("x", SHA))
        self.controler_avec(Controleur(), instantane)  # copie texte
        self.m.contenus[self.a] = Contenu("déjà figé", URL, SHA, "sig", "SUB1")
        self.controler_avec(Controleur(), instantane)
        self.assertEqual(instantane.appels, [])

    def test_reprise_perimee_non_figee(self):
        self.rendu_url_sans_instantane()
        self.avancer.executer(self.a, Etape.CONTROLES)
        self.controler_avec(Controleur(), Instantane(("x", SHA)))
        self.assertEqual(self.m.contenu(self.a).texte, "")

    def test_signal_perime_ignore(self):
        self.avancer.executer(self.a, Etape.CONTROLES)
        avant = list(self.journal)
        self.controler(Controleur(["trop court"]))
        self.controler(Controleur(erreur=EtapeIndisponible("panne")))
        self.assertEqual((self.journal, self.m.propositions(self.a), self.notes), (avant, [], []))
        self.m.copies[self.a] = replace(self.m.copies[self.a], statut=Statut.PUBLIEE)
        self.controler(Controleur())
        self.assertEqual(self.journal, avant)
