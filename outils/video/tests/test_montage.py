"""Les trois scripts de montage : tout ce qui décide, éprouvé sans captation ni ffmpeg.

Aucun test ici n'ouvre une vidéo. C'est voulu : un outil qu'on ne peut éprouver qu'avec un fichier de
800 Mo sous la main n'est jamais éprouvé. Les appels à `ffmpeg`, `whisper.cpp` et `remotion` sont rangés en
bout de chaîne, et ce sont les seules lignes que ces tests ne couvrent pas.
"""
import pathlib
import re
import sys
import tempfile
import unittest

RACINE = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RACINE))

import decouper  # noqa: E402
import habiller  # noqa: E402
import sous_titrer  # noqa: E402
from decouper import Intervalle  # noqa: E402
from sous_titrer import Replique  # noqa: E402

JOURNAL = """
Input #0, matroska,webm, from 'brut/s01-intro.mkv':
  Duration: 00:12:34.56, start: 0.000000, bitrate: 6100 kb/s
[silencedetect @ 0x1] silence_start: 3.2
[silencedetect @ 0x1] silence_end: 5.6 | silence_duration: 2.4
[silencedetect @ 0x1] silence_start: 40.0
[silencedetect @ 0x1] silence_end: 42.5 | silence_duration: 2.5
"""


class TestCeQueFfmpegARaconte(unittest.TestCase):
    def test_les_silences_sont_lus_par_paires(self):
        self.assertEqual(decouper.lire_silences(JOURNAL),
                         (Intervalle(3.2, 5.6), Intervalle(40.0, 42.5)))

    def test_un_silence_qui_court_jusqu_a_la_fin_reste_ouvert(self):
        """`silencedetect` n'écrit pas de `silence_end` pour un silence qui finit avec le fichier. On ne
        lui invente pas une borne : l'appelant la ferme avec la durée, qu'il connaît."""
        silences = decouper.lire_silences("silence_start: 10.0\n")
        self.assertEqual(len(silences), 1)
        self.assertEqual(silences[0].fin, float("inf"))

    def test_la_duree_est_lue_dans_l_en_tete(self):
        self.assertAlmostEqual(decouper.lire_duree(JOURNAL), 754.56, places=2)

    def test_sans_en_tete_la_duree_vaut_zero(self):
        self.assertEqual(decouper.lire_duree("rien du tout"), 0.0)

    def test_un_journal_vide_ne_donne_aucun_silence(self):
        self.assertEqual(decouper.lire_silences(""), ())


class TestCeQuOnGarde(unittest.TestCase):
    def test_les_silences_sont_retires_et_les_bords_rendus(self):
        """La marge laisse respirer : on coupe 0,15 s après le début du silence et on reprend 0,15 s avant
        sa fin. Couper au ras produit un montage qui avale les fins de mots."""
        gardes = decouper.segments_parlants((Intervalle(3.2, 5.6),), duree=10.0, marge=0.15)
        self.assertEqual(len(gardes), 2)
        self.assertAlmostEqual(gardes[0].fin, 3.35)
        self.assertAlmostEqual(gardes[1].debut, 5.45)
        self.assertEqual((gardes[0].debut, gardes[1].fin), (0.0, 10.0))

    def test_une_captation_sans_silence_est_gardee_entiere(self):
        self.assertEqual(decouper.segments_parlants((), duree=30.0), (Intervalle(0.0, 30.0),))

    def test_les_miettes_entre_deux_silences_sont_abandonnees(self):
        """Deux silences séparés de 0,2 s : ce qui reste entre eux n'est pas de la parole."""
        gardes = decouper.segments_parlants((Intervalle(1.0, 2.0), Intervalle(2.2, 3.0)),
                                            duree=5.0, marge=0.0, minimum=0.4)
        self.assertNotIn(Intervalle(2.0, 2.2), gardes)

    def test_un_silence_qui_depasse_la_duree_est_borne_par_elle(self):
        gardes = decouper.segments_parlants((Intervalle(8.0, float("inf")),), duree=10.0, marge=0.0)
        self.assertEqual(gardes, (Intervalle(0.0, 8.0),))

    def test_les_silences_desordonnes_sont_remis_dans_l_ordre(self):
        desordre = (Intervalle(40.0, 42.0), Intervalle(3.0, 5.0))
        self.assertEqual(decouper.segments_parlants(desordre, duree=60.0, marge=0.0),
                         decouper.segments_parlants(tuple(reversed(desordre)), duree=60.0, marge=0.0))


class TestLesReprises(unittest.TestCase):
    """Trois coups sur le micro : ce qui précède est la phrase ratée, ce qui suit est la bonne."""

    def test_la_phrase_ratee_est_retiree(self):
        garde = decouper.retirer_reprises((Intervalle(0.0, 60.0),), (30.0,), retour=10.0)
        self.assertEqual(garde, (Intervalle(0.0, 20.0), Intervalle(30.0, 60.0)))

    def test_on_ne_retire_jamais_plus_que_le_retour_demande(self):
        """Au-delà, on mangerait du propos valable sans que personne ne s'en aperçoive avant le rendu."""
        garde = decouper.retirer_reprises((Intervalle(0.0, 600.0),), (300.0,), retour=12.0)
        self.assertEqual(garde[0], Intervalle(0.0, 288.0))

    def test_deux_reprises_coupent_deux_fois(self):
        garde = decouper.retirer_reprises((Intervalle(0.0, 100.0),), (20.0, 60.0), retour=5.0)
        self.assertEqual(garde, (Intervalle(0.0, 15.0), Intervalle(20.0, 55.0), Intervalle(60.0, 100.0)))

    def test_une_reprise_qui_couvre_tout_un_segment_le_supprime(self):
        garde = decouper.retirer_reprises((Intervalle(10.0, 15.0), Intervalle(40.0, 50.0)),
                                          (20.0,), retour=15.0)
        self.assertEqual(garde, (Intervalle(40.0, 50.0),))

    def test_sans_reprise_rien_ne_change(self):
        segments = (Intervalle(0.0, 10.0), Intervalle(12.0, 20.0))
        self.assertEqual(decouper.retirer_reprises(segments, ()), segments)

    def test_les_reprises_sont_lues_un_horodatage_par_ligne(self):
        with tempfile.TemporaryDirectory() as dossier:
            fichier = pathlib.Path(dossier) / "reprises.txt"
            fichier.write_text("12.5\n# oubli du nom du parcours\n98.25\n\n", encoding="utf-8")
            self.assertEqual(decouper.charger_reprises(fichier), (12.5, 98.25))

    def test_un_fichier_de_reprises_absent_ne_fait_rien(self):
        self.assertEqual(decouper.charger_reprises(pathlib.Path("nulle-part.txt")), ())
        self.assertEqual(decouper.charger_reprises(None), ())


class TestLeFiltreRendu(unittest.TestCase):
    def test_image_et_son_sont_coupes_ensemble(self):
        """Couper l'image sans le son décale la voix de toute la durée retirée."""
        filtre = decouper.filtre_de_montage((Intervalle(0.0, 3.0),))
        self.assertIn("[0:v]select=", filtre)
        self.assertIn("[0:a]aselect=", filtre)
        self.assertEqual(filtre.count("between(t,0.000,3.000)"), 2)

    def test_les_horodatages_sont_refaits(self):
        """Sans `setpts`, le rendu garde les trous et la lecture saute."""
        filtre = decouper.filtre_de_montage((Intervalle(0.0, 3.0), Intervalle(5.0, 9.0)))
        self.assertIn("setpts=N/FRAME_RATE/TB", filtre)
        self.assertIn("asetpts=N/SR/TB", filtre)

    def test_le_son_est_normalise_a_la_norme_parlee(self):
        self.assertIn("loudnorm=I=-16.0", decouper.filtre_de_montage((Intervalle(0.0, 1.0),)))

    def test_aucun_segment_est_une_erreur_et_non_un_rendu_vide(self):
        with self.assertRaises(ValueError):
            decouper.filtre_de_montage(())

    def test_le_resume_dit_ce_qui_a_ete_retire(self):
        rapport = decouper.resume((Intervalle(0.0, 6.0),), duree=10.0)
        self.assertEqual((rapport["duree_gardee_s"], rapport["retire_s"], rapport["part_retiree"]),
                         (6.0, 4.0, 0.4))

    def test_un_resume_sur_une_duree_nulle_ne_divise_pas_par_zero(self):
        self.assertEqual(decouper.resume((), duree=0.0)["part_retiree"], 0.0)


WHISPER = {"transcription": [
    {"offsets": {"from": 0, "to": 1200}, "text": " Aujourd'hui", "tokens": [{"p": -0.1}]},
    {"offsets": {"from": 1200, "to": 3000}, "text": " nous allons voir", "tokens": [{"p": -0.2}]},
    {"offsets": {"from": 3000, "to": 6000}, "text": " comment un agent décide.", "tokens": [{"p": -0.9}]},
    {"offsets": {"from": 6000, "to": 7000}, "text": "   ", "tokens": []},
]}


class TestLaTranscriptionLue(unittest.TestCase):
    def test_les_bornes_passent_des_millisecondes_aux_secondes(self):
        repliques = sous_titrer.lire_whisper(WHISPER)
        self.assertEqual((repliques[0].debut, repliques[0].fin), (0.0, 1.2))

    def test_les_repliques_vides_sont_ecartees(self):
        self.assertEqual(len(sous_titrer.lire_whisper(WHISPER)), 3)

    def test_la_confiance_est_la_moyenne_des_jetons(self):
        repliques = sous_titrer.lire_whisper(WHISPER)
        self.assertAlmostEqual(repliques[2].confiance, -0.9)

    def test_sans_jetons_la_confiance_reste_nulle_plutot_qu_inventee(self):
        brut = {"transcription": [{"offsets": {"from": 0, "to": 1000}, "text": "bonjour"}]}
        self.assertEqual(sous_titrer.lire_whisper(brut)[0].confiance, 0.0)

    def test_un_json_sans_transcription_ne_donne_rien(self):
        self.assertEqual(sous_titrer.lire_whisper({}), ())


class TestDesSousTitresLisibles(unittest.TestCase):
    def test_les_fragments_sont_recolles(self):
        """Affichés tels quels, les fragments de whisper clignotent une demi-seconde chacun."""
        fusion = sous_titrer.fusionner(sous_titrer.lire_whisper(WHISPER))
        self.assertEqual(len(fusion), 1)
        self.assertEqual(fusion[0].texte, "Aujourd'hui nous allons voir comment un agent décide.")

    def test_on_ne_recolle_jamais_par_dessus_une_fin_de_phrase(self):
        """Un sous-titre qui mélange deux phrases se lit deux fois."""
        repliques = (Replique(0.0, 1.0, "C'est fini."), Replique(1.0, 2.0, "On passe à la suite."))
        self.assertEqual(len(sous_titrer.fusionner(repliques)), 2)

    def test_un_sous_titre_trop_long_est_recoupe_sur_un_espace(self):
        long = Replique(0.0, 10.0, " ".join(["mot"] * 60))
        morceaux = sous_titrer.fusionner((long,), caracteres_max=40)
        self.assertGreater(len(morceaux), 1)
        for morceau in morceaux:
            with self.subTest(morceau.texte):
                self.assertLessEqual(len(morceau.texte), 40)
                self.assertNotIn("  ", morceau.texte)

    def test_la_recoupe_repartit_la_duree_sans_trou_ni_recouvrement(self):
        long = Replique(10.0, 20.0, " ".join(["mot"] * 60))
        morceaux = sous_titrer.fusionner((long,), caracteres_max=40)
        self.assertAlmostEqual(morceaux[0].debut, 10.0)
        self.assertAlmostEqual(morceaux[-1].fin, 20.0, places=6)
        for avant, apres in zip(morceaux, morceaux[1:]):
            self.assertAlmostEqual(avant.fin, apres.debut, places=6)

    def test_un_mot_plus_long_que_la_limite_n_est_pas_cassé_en_deux(self):
        """Mieux vaut un sous-titre qui dépasse qu'un mot coupé au milieu."""
        enorme = Replique(0.0, 2.0, "anticonstitutionnellement")
        self.assertEqual(sous_titrer.fusionner((enorme,), caracteres_max=10)[0].texte,
                         "anticonstitutionnellement")

    def test_on_ne_recolle_pas_au_dela_de_la_duree_d_affichage(self):
        repliques = (Replique(0.0, 5.0, "début"), Replique(5.0, 9.0, "suite"))
        self.assertEqual(len(sous_titrer.fusionner(repliques, secondes_max=6.0)), 2)


class TestLeFichierSubRip(unittest.TestCase):
    def test_l_horodatage_suit_la_forme_du_format(self):
        self.assertEqual(sous_titrer.horodatage(3754.567), "01:02:34,567")

    def test_zero_s_ecrit_entierement(self):
        self.assertEqual(sous_titrer.horodatage(0), "00:00:00,000")

    def test_une_valeur_negative_est_ramenee_a_zero(self):
        """Un décalage mal appliqué ne doit pas produire un fichier qu'aucun lecteur n'ouvre."""
        self.assertEqual(sous_titrer.horodatage(-3.0), "00:00:00,000")

    def test_les_blocs_sont_numerotes_a_partir_de_un(self):
        srt = sous_titrer.en_srt((Replique(0.0, 1.0, "un"), Replique(1.0, 2.0, "deux")))
        self.assertTrue(srt.startswith("1\n00:00:00,000 --> 00:00:01,000\nun"))
        self.assertIn("\n\n2\n", srt)

    def test_un_sous_titre_long_tient_sur_deux_lignes_au_plus(self):
        srt = sous_titrer.en_srt((Replique(0.0, 4.0, " ".join(["mot"] * 40)),))
        lignes = srt.strip().splitlines()
        self.assertLessEqual(len(lignes) - 2, 2)  # numéro et horodatage mis à part


class TestCeQuIlFautRelire(unittest.TestCase):
    def attendus(self, texte: str):
        return [attendu for _, attendu in sous_titrer.mots_du_lexique_suspects(texte)]

    def test_une_casse_ou_une_espace_de_travers_est_signalee(self):
        self.assertIn("Openlab", self.attendus("Bienvenue chez Open Lab"))
        self.assertIn("LangGraph", self.attendus("on utilise langgraph ici"))

    def test_les_fautes_reellement_commises_par_le_modele_sont_signalees(self):
        """Relevées sur une vraie transcription de ce poste, modèle large-v3-turbo, amorce donnée.
        La version précédente du contrôle n'en voyait aucune : elle comparait des orthographes."""
        self.assertIn("LangGraph", self.attendus("avec LangGraff prend ses décisions"))
        self.assertIn("pandas", self.attendus("nous utiliserons scikit-learn et panda"))
        self.assertIn("Abidjan", self.attendus("dans le contexte ivoirien, à Abidjann"))

    def test_ce_qui_est_ecrit_est_rendu_avec_ce_qui_est_attendu(self):
        """Le relecteur doit pouvoir chercher le mot fautif dans le `.srt` sans le deviner."""
        self.assertEqual(sous_titrer.mots_du_lexique_suspects("avec LangGraff ici"),
                         (("LangGraff", "LangGraph"),))

    def test_un_mot_du_lexique_bien_ecrit_ne_derange_personne(self):
        self.assertEqual(sous_titrer.mots_du_lexique_suspects("Bienvenue chez Openlab"), ())
        self.assertEqual(sous_titrer.mots_du_lexique_suspects("on utilise scikit-learn et pandas"), ())

    def test_la_comparaison_ignore_les_accents(self):
        self.assertIn("ivoirien", self.attendus("le contexte ivoírien"))

    def test_un_mot_court_exige_l_egalite_plutot_que_la_ressemblance(self):
        """À trois ou quatre lettres tout ressemble à tout : « rang » n'est pas « RAG », « base » n'est
        pas « RAG » non plus. Signaler ces mots-là noierait la liste."""
        for texte in ("il frappe un grand rang de chiffres", "la base et le cas de ce test"):
            with self.subTest(texte):
                self.assertNotIn("RAG", self.attendus(texte))

    def test_un_mot_sans_rapport_n_est_pas_rapproche_de_force(self):
        self.assertEqual(sous_titrer.mots_du_lexique_suspects("nous verrons la régression linéaire"), ())

    def test_le_seuil_prend_les_fautes_du_modele(self):
        """Le seuil est mesuré, pas choisi. Ces neuf fautes sont du vrai : elles viennent de
        transcriptions, ou de la même famille d'erreurs."""
        for faute, attendu in (("langgraff", "LangGraph"), ("panda", "pandas"), ("pyhton", "Python"),
                               ("kubernets", "Kubernetes"), ("dockre", "Docker"), ("frape", "Frappe"),
                               ("agentik", "agentique"), ("abidjann", "Abidjan")):
            with self.subTest(faute):
                self.assertIn(attendu, self.attendus(f"on parle de {faute} aujourd'hui"))

    def test_le_seuil_ne_prend_pas_le_francais_de_cours(self):
        """L'autre bord. Une liste de relecture bruyante ne se lit plus, et c'est alors comme si elle
        n'existait pas — « agent » ne doit pas se faire prendre pour « agentique »."""
        courant = ("aujourd'hui nous allons voir comment un agent construit prend ses décisions "
                   "la régression linéaire le contexte le modèle la méthode les données une fonction "
                   "un tableau la mémoire la base le cas le rang la page le code le terminal la "
                   "commande le fichier le dossier la variable la boucle la condition la classe")
        self.assertEqual(sous_titrer.mots_du_lexique_suspects(courant), ())

    def test_un_mot_qui_suit_un_terme_du_lexique_n_est_pas_signale(self):
        """Les paires voisines ne servent qu'à « Open Lab » : par ressemblance, « scikit-learn et »
        passerait pour « scikit-learn », et chaque mot suivant un terme du lexique serait signalé."""
        self.assertEqual(sous_titrer.mots_du_lexique_suspects("on utilise scikit-learn et pandas"), ())
        self.assertEqual(sous_titrer.mots_du_lexique_suspects("Python pour l'analyse"), ())

    def test_le_meme_ecart_n_est_signale_qu_une_fois(self):
        suspects = sous_titrer.mots_du_lexique_suspects("LangGraff puis encore LangGraff")
        self.assertEqual(len(suspects), 1)

    def test_le_doute_du_modele_est_signale(self):
        signalements = sous_titrer.a_relire((Replique(0.0, 3.0, "mot", confiance=-0.9),))
        self.assertIn("le modèle a douté", signalements[0]["raisons"])

    def test_une_confiance_absente_ne_declenche_rien(self):
        self.assertEqual(sous_titrer.a_relire((Replique(0.0, 3.0, "mot", confiance=0.0),)), ())

    def test_un_sous_titre_illisible_dans_le_temps_imparti_est_signale(self):
        trop = Replique(0.0, 1.0, "x" * 60)
        self.assertIn("trop de texte pour le temps affiché", sous_titrer.a_relire((trop,))[0]["raisons"])

    def test_un_sous_titre_qui_clignote_est_signale(self):
        self.assertIn("affiché trop brièvement",
                      sous_titrer.a_relire((Replique(0.0, 0.3, "oui"),))[0]["raisons"])

    def test_une_transcription_propre_ne_signale_rien(self):
        propre = Replique(0.0, 4.0, "Bienvenue chez Openlab.", confiance=-0.1)
        self.assertEqual(sous_titrer.a_relire((propre,)), ())

    def test_le_signalement_nomme_le_mot_ecrit_et_celui_attendu(self):
        ecorche = Replique(0.0, 4.0, "construit avec LangGraff.", confiance=-0.1)
        raison = sous_titrer.a_relire((ecorche,))[0]["raisons"][0]
        self.assertIn("LangGraff", raison)
        self.assertIn("LangGraph", raison)

    def test_l_amorce_porte_tout_le_lexique_au_modele(self):
        """Le premier filet, et le plus efficace : sans elle, « Openlab » devient « Zopan Labbé »."""
        texte = sous_titrer.amorce()
        for mot in sous_titrer.LEXIQUE:
            with self.subTest(mot):
                self.assertIn(mot, texte)

    def test_la_liste_de_relecture_renvoie_au_srt_et_non_a_elle_meme(self):
        texte = sous_titrer.en_relecture(sous_titrer.a_relire((Replique(0.0, 0.2, "x"),)), total=1)
        self.assertIn("Corrigez le `.srt`", texte)

    def test_sans_signalement_la_liste_le_dit_et_demande_quand_meme_l_introduction(self):
        self.assertIn("rien à signaler", sous_titrer.en_relecture((), total=12))


class TestLeNomDeLaSeance(unittest.TestCase):
    def test_une_intro_est_lue(self):
        lu = habiller.lire_nom("00-fondamentaux-data-science/s01-intro.mp4")
        self.assertEqual((lu["seance"], lu["nature"], lu["numero_demo"]), (1, "intro", 0))

    def test_une_demo_numerotee_est_lue(self):
        lu = habiller.lire_nom("06-ia-agentique/s03-demo-2.mp4")
        self.assertEqual((lu["seance"], lu["nature"], lu["numero_demo"]), (3, "demo", 2))

    def test_les_barres_de_windows_sont_acceptees(self):
        """Le chemin saisi dans PowerShell porte des barres contraires ; la règle s'écrit avec des
        barres obliques."""
        lu = habiller.lire_nom(r"D:\studio\sorties\06-ia-agentique\s03-demo-2.mp4")
        self.assertEqual(lu["parcours_dossier"], "06-ia-agentique")

    def test_un_nom_hors_regle_est_refuse(self):
        for nom in ("ma-video.mp4", "06-ia-agentique/intro.mp4", "06-ia-agentique/s1-intro.mp4",
                    "ia-agentique/s01-intro.mp4", "06-ia-agentique/s01-intro.mkv",
                    "06-ia-agentique/s01-demo.mp4", "06-IA-Agentique/s01-intro.mp4"):
            with self.subTest(nom), self.assertRaises(habiller.NomHorsRegle):
                habiller.lire_nom(nom)

    def test_la_valeur_a_coller_dans_le_yaml_est_rendue_sans_le_reste_du_chemin(self):
        self.assertEqual(habiller.chemin_de_parcours(r"D:\studio\06-ia-agentique\s03-demo-2.mp4"),
                         "06-ia-agentique/s03-demo-2.mp4")

    def test_ce_que_l_outil_rend_au_yaml_est_toujours_accepte_par_l_application(self):
        r"""La règle est écrite deux fois : dans le domaine, parce qu'un fichier de parcours la subit, et
        ici, parce que cet outil ne peut pas importer Frappe.

        Les deux ne posent pourtant pas la même question. Le domaine valide une **valeur de YAML** : elle
        doit être exactement le chemin de l'atelier. L'outil lit un **chemin de disque**, qui porte en tête
        tout ce qui mène au studio — `D:\studio\sorties\...`. Il doit donc retrouver la règle en fin de
        chemin, et c'est `chemin_de_parcours` qui en extrait la valeur.

        L'invariant qui compte est le pont entre les deux : ce que l'outil donne à coller dans un parcours,
        l'application doit l'accepter. Sans lui, on habille une vidéo qui ne sera jamais publiable, et on
        ne s'en aperçoit qu'à la publication.
        """
        valider_video = self.valider_video_de_l_application()
        for chemin in ("00-fondamentaux-data-science/s01-intro.mp4",
                       "06-ia-agentique/s03-demo-2.mp4",
                       "01-developpeur-python/s18-demo-10.mp4",
                       r"D:\studio\sorties\06-ia-agentique\s03-demo-2.mp4",
                       "/home/moi/studio/06-ia-agentique/s01-intro.mp4",
                       "../06-ia-agentique/s01-intro.mp4"):
            with self.subTest(chemin):
                valeur = habiller.chemin_de_parcours(chemin)
                self.assertEqual(valider_video(valeur), valeur)

    def test_un_nom_que_l_application_refuse_est_refuse_ici_aussi(self):
        """L'autre moitié du pont : ce que le domaine n'accepterait pas, l'outil ne doit pas prétendre
        l'habiller. On ne juge que le nom lui-même, pas ce qui le précède sur le disque."""
        valider_video = self.valider_video_de_l_application()
        for nom in ("06-ia-agentique/s1-intro.mp4", "ia-agentique/s01-intro.mp4",
                    "06-ia-agentique/s01-intro.mkv", "06-ia-agentique/s01-demo.mp4",
                    "06-IA-Agentique/s01-intro.mp4", "06-ia-agentique/s01-intro.mp4.exe"):
            with self.subTest(nom):
                with self.assertRaises(Exception):
                    valider_video(nom)
                with self.assertRaises(habiller.NomHorsRegle):
                    habiller.lire_nom(nom)

    def valider_video_de_l_application(self):
        app = RACINE.parents[1] / "apps" / "openlab_academy"
        if not (app / "openlab_academy" / "domain" / "parcours.py").is_file():
            self.skipTest("application absente de ce poste")
        sys.path.insert(0, str(app))
        try:
            from openlab_academy.domain.parcours import valider_video
        finally:
            sys.path.remove(str(app))
        return valider_video


class TestCeQueRemotionRecoit(unittest.TestCase):
    def setUp(self):
        self.dossier = tempfile.TemporaryDirectory()
        self.addCleanup(self.dossier.cleanup)
        self.racine = pathlib.Path(self.dossier.name) / "06-ia-agentique"
        self.racine.mkdir(parents=True)
        self.source = self.racine / "s03-demo-2.mp4"
        self.source.write_bytes(b"x")

    def poser_srt(self, texte: str) -> None:
        self.source.with_suffix(".srt").write_text(texte, encoding="utf-8")

    def test_le_bandeau_nomme_la_seance_et_la_nature(self):
        habillage = habiller.preparer(self.source, titre="Un agent qui décide", parcours="IA agentique")
        self.assertEqual(habillage.mention(), "Séance 03 · Démonstration 2")

    def test_une_intro_ne_porte_pas_de_numero(self):
        intro = self.racine / "s01-intro.mp4"
        intro.write_bytes(b"x")
        self.assertEqual(habiller.preparer(intro).mention(), "Séance 01 · Introduction")

    def test_les_sous_titres_voisins_sont_lus_et_analyses(self):
        self.poser_srt("1\n00:00:01,000 --> 00:00:03,500\nBonjour\n")
        repliques = habiller.preparer(self.source).sous_titres
        self.assertEqual([(r.debut, r.fin, r.texte) for r in repliques], [(1.0, 3.5, "Bonjour")])

    def test_un_srt_absent_ne_donne_aucune_replique(self):
        """Incruster un `.srt` absent produirait une vidéo sans texte, sans que rien ne le signale."""
        self.assertEqual(habiller.preparer(self.source).sous_titres, ())

    def test_sans_titre_donne_le_dossier_en_fournit_un_lisible(self):
        self.assertEqual(habiller.preparer(self.source).titre, "Ia agentique")

    def test_la_composition_ne_recoit_que_le_nom_du_fichier(self):
        """Éprouvé sur ce poste : Remotion télécharge les ressources d'une composition, et une URL `file:`
        échoue à la lecture. Le dossier de la séance devient donc le dossier public du rendu, et
        `staticFile` y retrouve le fichier par son nom."""
        props = habiller.preparer(self.source).en_props()
        self.assertEqual(props["video"], "s03-demo-2.mp4")

    def test_le_dossier_de_la_seance_est_retenu_pour_le_rendu_mais_pas_passe_a_la_composition(self):
        """La composition n'a pas à connaître l'arborescence du poste : c'est à Remotion qu'on la donne."""
        habillage = habiller.preparer(self.source)
        self.assertEqual(pathlib.Path(habillage.dossier), self.racine.resolve())
        self.assertNotIn("dossier", habillage.en_props())

    def test_un_dossier_a_espaces_et_accents_passe_entier_au_rendu(self):
        """« D:\\Mes vidéos\\ » : le dossier part en argument, jamais concaténé dans une URL qu'un espace
        tronquerait."""
        dossier = pathlib.Path(self.dossier.name) / "Mes vidéos" / "06-ia-agentique"
        dossier.mkdir(parents=True)
        source = dossier / "s01-intro.mp4"
        source.write_bytes(b"x")
        commande = habiller.commande_de_rendu(pathlib.Path("s.mp4"), pathlib.Path("p.json"),
                                              habiller.preparer(source).dossier)
        self.assertIn(f"--public-dir={dossier.resolve()}", commande)

    def test_les_sous_titres_partent_en_proprietes_et_non_en_chemin(self):
        """La composition tourne sans accès au disque : un `.srt` chargé en différé rendrait la vidéo
        muette de texte un jour sur dix, sans rien signaler."""
        self.poser_srt("1\n00:00:00,500 --> 00:00:02,000\nUn agent décide\n")
        props = habiller.preparer(self.source).en_props()
        self.assertEqual(props["sousTitres"], [{"debut": 0.5, "fin": 2.0, "texte": "Un agent décide"}])

    def test_les_proprietes_passees_sont_exactement_celles_que_la_composition_attend(self):
        """Le pont entre Python et Remotion. Une propriété renommée d'un côté ne se voit pas de l'autre :
        le rendu part quand même, et sort une vidéo sans titre ou sans sous-titres. On compare donc les
        clés produites au type `SeanceProps` de la composition."""
        composition = (RACINE / "habillage" / "src" / "Seance.tsx").read_text(encoding="utf-8")
        corps = composition.split("export type SeanceProps = {")[1].split("};")[0]
        attendues = set(re.findall(r"^\s{2}(\w+)\??:", corps, re.MULTILINE))
        props = habiller.preparer(self.source, titre="T", parcours="P", duree=12.0).en_props()
        self.assertEqual(set(props), attendues)

    def test_la_duree_mesuree_est_transmise_a_la_composition(self):
        """Sans elle, la composition refuse de rendre — plutôt que de produire une vidéo tronquée que
        personne ne regarde jusqu'au bout avant de publier."""
        self.assertEqual(habiller.preparer(self.source, duree=754.56).en_props()["dureeVideo"], 754.56)


class TestLaCommandeDeRendu(unittest.TestCase):
    """Les propriétés passent par un fichier, jamais par la ligne de commande."""

    def test_les_proprietes_sont_passees_par_un_fichier(self):
        """Éprouvé sur ce poste : avec un JSON en ligne, `cmd` rend les accents dans la page de code
        locale et Remotion refuse le rendu — « Écosystème » suffit. Et une démonstration de douze minutes
        porte deux cents sous-titres, bien au-delà de la longueur de ligne permise."""
        commande = habiller.commande_de_rendu(pathlib.Path("s.mp4"), pathlib.Path("p.json"), "/un/dossier")
        self.assertIn("--props=p.json", commande)
        for argument in commande:
            with self.subTest(argument):
                self.assertNotIn("{", argument, "un JSON en ligne : la ligne de commande sera mutilée")

    def test_la_composition_visee_est_celle_de_la_racine_remotion(self):
        """Le nom est écrit des deux côtés. S'ils divergent, Remotion échoue sur « composition
        introuvable » — mais seulement au rendu, après le montage et la relecture."""
        racine = (RACINE / "habillage" / "src" / "Racine.tsx").read_text(encoding="utf-8")
        self.assertIn(f'id="{habiller.COMPOSITION}"', racine)


class TestLeBasDeLEcranAppartientAuxSousTitres(unittest.TestCase):
    """Un défaut vu à l'image, sur un rendu réel, et qu'aucun autre test n'aurait pris.

    Le bandeau était posé en bas à gauche. Dès la première réplique, le pavé de sous-titres recouvrait sa
    deuxième ligne. Rien n'échouait : le rendu sortait, la chaîne restait verte, et seul un œil sur
    l'image le voyait. Ce test fige la décision — les sous-titres occupent le bas du début à la fin, donc
    rien d'autre ne s'y pose.
    """

    def ancrage(self, composant: str) -> str:
        source = (RACINE / "habillage" / "src" / f"{composant}.tsx").read_text(encoding="utf-8")
        enveloppe = source.split("<AbsoluteFill")[1].split(">")[0]
        trouve = re.search(r"justifyContent:\s*'([a-z-]+)'", enveloppe)
        self.assertIsNotNone(trouve, f"{composant} : ancrage vertical introuvable")
        return trouve.group(1)

    def test_les_sous_titres_restent_en_bas(self):
        self.assertEqual(self.ancrage("SousTitres"), "flex-end")

    def test_le_bandeau_ne_partage_pas_le_bas_avec_eux(self):
        self.assertNotEqual(self.ancrage("Bandeau"), self.ancrage("SousTitres"))


class TestLaCharteDeLHabillage(unittest.TestCase):
    """L'habillage recopie la charte du site, parce que Remotion ne lit pas les variables CSS. Une dérive
    se voit à l'écran, mais jamais dans une chaîne verte."""

    def couleurs_du_site(self) -> dict:
        css = (RACINE.parents[1] / "apps" / "openlab_academy" / "openlab_academy" / "public" / "css"
               / "openlab.css")
        if not css.is_file():
            trouve = list((RACINE.parents[1] / "apps").rglob("openlab.css"))
            if not trouve:
                self.skipTest("feuille de style de l'application absente de ce poste")
            css = trouve[0]
        texte = css.read_text(encoding="utf-8")
        return {nom: valeur.lower()
                for nom, valeur in re.findall(r"--ol-([a-z-]+):\s*(#[0-9a-fA-F]{6})", texte)}

    def test_les_couleurs_sont_celles_du_site(self):
        site = self.couleurs_du_site()
        charte = (RACINE / "habillage" / "src" / "charte.ts").read_text(encoding="utf-8")
        recopiees = dict(re.findall(r"(\w+):\s*'(#[0-9a-fA-F]{6})'", charte))
        correspondances = {"orange": "orange", "orangeClair": "orange-light", "marine": "navy",
                           "marineDouce": "navy-soft", "ciel": "sky", "soleil": "sun",
                           "nuit": "night", "ivoire": "ivory"}
        for chez_nous, chez_le_site in correspondances.items():
            with self.subTest(chez_nous):
                self.assertIn(chez_nous, recopiees, "couleur disparue de l'habillage")
                self.assertEqual(recopiees[chez_nous].lower(), site[chez_le_site])


class TestLeSrtReluALaMain(unittest.TestCase):
    """Le `.srt` qu'on relit est celui qu'un humain a corrigé. Il faut tolérer ce qu'il y laisse."""

    def test_un_aller_retour_ne_perd_rien(self):
        """Le test le plus utile du lot : ce que `en_srt` écrit, `lire_srt` doit le rendre."""
        avant = (Replique(0.0, 2.5, "Bienvenue chez Openlab."),
                 Replique(2.5, 6.0, "Aujourd'hui, un agent qui décide."),
                 Replique(400.25, 403.875, "À la séance prochaine."))
        apres = sous_titrer.lire_srt(sous_titrer.en_srt(avant))
        self.assertEqual([(round(r.debut, 3), round(r.fin, 3), r.texte) for r in apres],
                         [(r.debut, r.fin, r.texte) for r in avant])

    def test_les_numeros_qui_ne_se_suivent_plus_sont_toleres(self):
        """Après une suppression à la main, la numérotation a des trous. Le fichier reste valable."""
        texte = ("1\n00:00:00,000 --> 00:00:01,000\nun\n\n"
                 "7\n00:00:02,000 --> 00:00:03,000\nsept\n")
        self.assertEqual([r.texte for r in sous_titrer.lire_srt(texte)], ["un", "sept"])

    def test_le_point_au_lieu_de_la_virgule_est_tolere(self):
        self.assertEqual(sous_titrer.lire_srt("1\n00:00:01.500 --> 00:00:02.750\nbonjour\n")[0].debut, 1.5)

    def test_les_fins_de_ligne_de_windows_sont_tolerees(self):
        texte = "1\r\n00:00:01,000 --> 00:00:02,000\r\nbonjour\r\n\r\n"
        self.assertEqual([r.texte for r in sous_titrer.lire_srt(texte)], ["bonjour"])

    def test_une_marque_d_octets_en_tete_ne_gene_pas(self):
        """Le Bloc-notes de Windows en pose une, et elle collerait au premier numéro."""
        texte = "﻿1\n00:00:01,000 --> 00:00:02,000\nbonjour\n"
        self.assertEqual([r.texte for r in sous_titrer.lire_srt(texte)], ["bonjour"])

    def test_les_lignes_d_un_meme_sous_titre_sont_recollees(self):
        """La coupure en deux lignes est une décision d'affichage : l'habillage la reprend à sa façon."""
        texte = "1\n00:00:01,000 --> 00:00:03,000\nune phrase\nsur deux lignes\n"
        self.assertEqual(sous_titrer.lire_srt(texte)[0].texte, "une phrase sur deux lignes")

    def test_un_bloc_vide_de_son_texte_est_ignore(self):
        """Le relecteur efface parfois le texte au lieu du bloc entier."""
        texte = ("1\n00:00:01,000 --> 00:00:02,000\n\n\n"
                 "2\n00:00:02,000 --> 00:00:03,000\nreste\n")
        self.assertEqual([r.texte for r in sous_titrer.lire_srt(texte)], ["reste"])

    def test_un_bloc_sans_bornes_est_ignore_plutot_que_devine(self):
        """Sans bornes, on ne sait pas quand l'afficher, et le deviner serait pire."""
        texte = "1\nune note du relecteur\n\n2\n00:00:02,000 --> 00:00:03,000\nbon\n"
        self.assertEqual([r.texte for r in sous_titrer.lire_srt(texte)], ["bon"])

    def test_un_fichier_vide_ne_donne_rien(self):
        self.assertEqual(sous_titrer.lire_srt(""), ())
        self.assertEqual(sous_titrer.lire_srt("\n\n\n"), ())

    def test_les_millisecondes_courtes_sont_completees_et_non_tronquees(self):
        """« ,5 » vaut cinq cents millisecondes, pas cinq."""
        self.assertEqual(sous_titrer.lire_srt("1\n00:00:00,5 --> 00:00:01,25\nx\n")[0].debut, 0.5)
