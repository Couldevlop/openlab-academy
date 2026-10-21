import unittest
from dataclasses import replace
from datetime import datetime, timedelta

from openlab_academy.application.soumettre_copie import Contenu, Exercice, SoumettreCopie
from openlab_academy.domain.copie import Copie, CopieVerrouillee, Etat, Proposition, Source, Statut
from openlab_academy.domain.grille import grille_generique
from openlab_academy.domain.reglages_evaluation import (
    CHAINES_DEFAUT, Chaine, ConfigEtape, Etape, Expiration, ReglagesEvaluation, Surcharge, TypeExercice,
)

GRILLE = grille_generique((("Pertinence", 60), ("Rigueur", 40)), ("Faible", "Bon"))
MAINTENANT = datetime(2026, 10, 20, 8, 0)


class DepotMemoire:
    def __init__(self, exercice=Exercice(TypeExercice.LIVRABLE, GRILLE, None), cohorte="COH1", auto=None):
        self.exercices = {"EX1": exercice} if exercice else {}
        self.cohorte_ = cohorte
        self.auto = auto
        self.copies: dict[str, Copie] = {}
        self.grilles, self.contenus, self.signatures = {}, {}, {}
        self.props: dict[str, list[Proposition]] = {}
        self.relectures_annulees: list[str] = []
        self.statuts: list[tuple] = []
        self.verrous: list[str] = []

    def exercice(self, exercice):
        return self.exercices.get(exercice)

    def cohorte(self, apprenant, exercice):
        return self.cohorte_

    def auto_evaluation(self, apprenant, exercice):
        return self.auto

    def signature(self, copie_id):
        return self.signatures[copie_id]

    def copie(self, copie_id):
        return self.copies[copie_id]

    def verrouiller(self, copie_id):
        self.verrous.append(copie_id)
        return CopieVerrouillee(self.copies[copie_id], Etat("", None))

    def creer(self, copie, grille, contenu):
        copie_id = f"C{len(self.copies) + 1}"
        self.copies[copie_id] = replace(copie, id=copie_id)
        self.grilles[copie_id], self.contenus[copie_id] = grille, contenu
        self.signatures[copie_id] = contenu.signature
        return copie_id

    def version_courante(self, soumission, verrouillee=False):
        versions = [c for c in self.copies.values() if self.contenus[c.id].soumission == soumission]
        return max(versions, key=lambda c: c.version, default=None)

    def ajouter_proposition(self, copie_id, p):
        self.props.setdefault(copie_id, []).append(p)

    def propositions(self, copie_id):
        return self.props.get(copie_id, [])

    def changer_statut(self, copie_id, statut, etape, echeance):
        self.statuts.append((copie_id, statut, etape, echeance))
        self.copies[copie_id] = replace(self.copies[copie_id], statut=statut)

    def annuler_relectures(self, copie_id):
        self.relectures_annulees.append(copie_id)


class InstantaneMemoire:
    def __init__(self, erreur=None):
        self.appels, self.erreur = [], erreur

    def prendre(self, url):
        self.appels.append(url)
        if self.erreur:
            raise self.erreur
        return f"contenu de {url}", "abc123"


def soumission(**autres):
    return {"name": "SUB1", "assignment": "EX1", "member": "a@x.ci", "type": "URL",
            "answer": "https://github.com/a/p", "assignment_attachment": None, **autres}


class TestSoumettreCopie(unittest.TestCase):
    def cas(self, depot=None, instantane=None, reglages=None, surcharges=lambda: ()):
        self.depot = depot or DepotMemoire()
        self.instantane = instantane or InstantaneMemoire()
        self.journal = []
        self.uc = SoumettreCopie(self.depot, self.instantane, reglages or ReglagesEvaluation(), lambda: MAINTENANT,
                                 surcharges, lambda *args: self.journal.append(args))
        return self.uc

    def test_premier_rendu(self):
        copie_id = self.cas().executer(soumission())
        c = self.depot.copie(copie_id)
        self.assertEqual((c.version, c.statut, c.apprenant, c.exercice, c.cohorte, c.type_),
                         (1, Statut.RENDUE, "a@x.ci", "EX1", "COH1", TypeExercice.LIVRABLE))
        self.assertIs(self.depot.grilles[copie_id], GRILLE)
        self.assertEqual(self.depot.grilles[copie_id].empreinte(), GRILLE.empreinte())

    def test_etape_et_echeance_de_depart(self):
        copie_id = self.cas().executer(soumission())
        # livrable : l'auto-évaluation ouvre la chaîne, avec son délai de 72 h
        self.assertEqual(self.depot.statuts,
                         [(copie_id, Statut.RENDUE, "auto_evaluation", datetime(2026, 10, 23, 8, 0))])

    def test_rendu_url_prend_un_instantane(self):
        copie_id = self.cas().executer(soumission())
        self.assertEqual(self.instantane.appels, ["https://github.com/a/p"])
        contenu = self.depot.contenus[copie_id]
        self.assertEqual((contenu.texte, contenu.source_url, contenu.commit, contenu.soumission),
                         ("contenu de https://github.com/a/p", "https://github.com/a/p", "abc123", "SUB1"))

    def test_instantane_en_erreur_ne_bloque_pas(self):
        copie_id = self.cas(instantane=InstantaneMemoire(RuntimeError("hors ligne"))).executer(soumission())
        contenu = self.depot.contenus[copie_id]
        self.assertEqual((contenu.texte, contenu.source_url, contenu.commit), ("", "https://github.com/a/p", ""))
        self.assertEqual(self.depot.copie(copie_id).statut, Statut.RENDUE)

    def test_rendu_texte_sans_instantane(self):
        copie_id = self.cas().executer(soumission(type="Text", answer="<p>ma réponse</p>"))
        self.assertEqual(self.instantane.appels, [])
        contenu = self.depot.contenus[copie_id]
        self.assertEqual((contenu.texte, contenu.source_url, contenu.commit), ("<p>ma réponse</p>", "", ""))

    def test_rendu_fichier_garde_le_lien(self):
        copie_id = self.cas().executer(
            soumission(type="PDF", answer=None, assignment_attachment="/private/files/a.pdf"))
        contenu = self.depot.contenus[copie_id]
        self.assertEqual((contenu.texte, contenu.source_url), ("", "/private/files/a.pdf"))
        self.assertEqual(self.instantane.appels, [])

    def test_exercice_sans_grille_ignore(self):
        self.assertIsNone(self.cas(DepotMemoire(exercice=None)).executer(soumission()))
        self.assertEqual(self.depot.copies, {})

    def test_cohorte_absente(self):
        copie_id = self.cas(DepotMemoire(cohorte=None)).executer(soumission())
        self.assertEqual(self.depot.copie(copie_id).cohorte, "")

    def test_meme_contenu_ne_cree_pas_de_version(self):
        uc = self.cas()
        premiere = uc.executer(soumission())
        # correction par le formateur : seul le statut LMS change
        self.assertEqual(uc.executer(soumission(status="Pass")), premiere)
        self.assertEqual(len(self.depot.copies), 1)
        self.assertEqual(self.instantane.appels, ["https://github.com/a/p"])

    def test_resoumission_cree_la_version_2(self):
        uc = self.cas()
        v1 = uc.executer(soumission())
        self.depot.ajouter_proposition(v1, Proposition(Source.IA, "ia", {"pertinence": 1}))
        v2 = uc.executer(soumission(answer="https://github.com/a/p2"))
        self.assertNotEqual(v1, v2)
        self.assertEqual(self.depot.copie(v2).version, 2)
        self.assertEqual(self.depot.relectures_annulees, [v1])
        self.assertEqual(self.depot.copie(v1).statut, Statut.RENVOYEE)
        self.assertEqual(self.depot.propositions(v2), [])  # propositions de la v1 hors calcul
        self.assertEqual(len(self.depot.propositions(v1)), 1)

    def test_resoumission_d_une_copie_avancee_non_publiee(self):
        for statut in (Statut.PRE_CORRIGEE, Statut.PROVISOIRE):
            uc = self.cas()
            v1 = uc.executer(soumission())
            self.depot.copies[v1] = replace(self.depot.copies[v1], statut=statut)
            v2 = uc.executer(soumission(answer="https://github.com/a/p2"))
            self.assertEqual(self.depot.copie(v2).version, 2)
            self.assertEqual(self.depot.copie(v1).statut, statut)
            self.assertEqual(self.depot.relectures_annulees, [v1])
            self.assertEqual(self.depot.statuts[-2], (v1, statut, "", None))  # hors chaîne : ni étape ni échéance

    def test_version_courante_relue_sous_verrou(self):
        uc = self.cas()
        v1 = uc.executer(soumission())
        perimee = self.depot.copies[v1]
        self.depot.copies[v1] = replace(perimee, statut=Statut.PUBLIEE)  # publiée par une autre transaction
        self.depot.version_courante = lambda s, verrouillee=False: perimee
        self.assertEqual(uc.executer(soumission(answer="https://github.com/a/p2")), v1)
        self.assertEqual(self.depot.verrous, [v1])
        self.assertEqual(self.depot.relectures_annulees, [])

    def test_version_creee_entre_temps_relue_sous_verrou(self):
        uc = self.cas()
        v1 = uc.executer(soumission())
        v2 = uc.executer(soumission(answer="https://github.com/a/p2"))  # rendu concurrent, déjà validé
        perimee = self.depot.copies[v1]
        self.depot.version_courante = lambda s, verrouillee=False: self.depot.copies[v2] if verrouillee else perimee
        self.depot.verrous.clear()
        self.assertEqual(uc.executer(soumission(answer="https://github.com/a/p2")), v2)  # même rendu : rien de neuf
        self.assertEqual(self.depot.verrous, [v1, v2])
        self.assertEqual(len(self.depot.copies), 2)
        v3 = uc.executer(soumission(answer="https://github.com/a/p3"))
        self.assertEqual(self.depot.copie(v3).version, 3)  # numérotée depuis la version relue, pas la périmée

    def test_resoumission_apres_publication_ignoree_et_journalisee(self):
        uc = self.cas()
        v1 = uc.executer(soumission())
        self.depot.copies[v1] = replace(self.depot.copies[v1], statut=Statut.PUBLIEE)
        self.assertEqual(uc.executer(soumission(answer="https://github.com/a/p2")), v1)
        self.assertEqual(len(self.depot.copies), 1)
        self.assertEqual(self.depot.relectures_annulees, [])
        self.assertEqual(self.journal[0][:3], (v1, "a@x.ci", "rendu après publication ignoré"))

    def test_chaine_devenue_invalide_la_copie_part_avec_la_chaine_du_type(self):
        demarrees = []
        uc = self.cas()
        uc._demarrer = demarrees.append
        v1 = uc.executer(soumission())
        dangereuse = Chaine(tuple(ConfigEtape(e, e == Etape.FORMATEUR, 1, Expiration.PUBLIER_PROVISOIRE)
                                  for e in Etape))
        uc._surcharges = lambda: (Surcharge(None, "EX1", dangereuse),)
        v2 = uc.executer(soumission(answer="https://github.com/a/p2"))
        self.assertNotEqual(v2, v1)
        self.assertEqual(demarrees, [v1, v2])
        self.assertEqual(self.depot.copie(v2).version, 2)
        premiere = CHAINES_DEFAUT[TypeExercice.LIVRABLE].config(Etape.AUTO_EVALUATION)
        self.assertEqual(self.depot.statuts[-1], (v2, Statut.RENDUE, "auto_evaluation",
                                                  MAINTENANT + timedelta(hours=premiere.delai_heures)))
        self.assertIn((v2, "systeme", "chaîne invalide : chaîne du type appliquée"), [j[:3] for j in self.journal])
        self.assertEqual(self.depot.relectures_annulees, [v1])

    def test_nouvelle_copie_demarree_une_seule_fois(self):
        demarrees = []
        uc = self.cas()
        uc._demarrer = demarrees.append
        v1 = uc.executer(soumission())
        uc.executer(soumission(status="Pass"))  # même rendu : rien ne redémarre
        v2 = uc.executer(soumission(answer="https://github.com/a/p2"))
        self.assertEqual(demarrees, [v1, v2])

    def test_auto_evaluation_prealable_rattachee(self):
        copie_id = self.cas(DepotMemoire(auto={"pertinence": 1, "rigueur": 0})).executer(soumission())
        self.assertEqual(self.depot.propositions(copie_id),
                         [Proposition(Source.AUTO_EVALUATION, "a@x.ci", {"pertinence": 1, "rigueur": 0})])

    def test_chaine_du_yaml_et_surcharge(self):
        yaml = Chaine((ConfigEtape(Etape.IA, True, 2, Expiration.PASSER),
                       ConfigEtape(Etape.FORMATEUR, True, 5, Expiration.ESCALADER)))
        depot = DepotMemoire(Exercice(TypeExercice.LIVRABLE, GRILLE, yaml))
        copie_id = self.cas(depot).executer(soumission())
        self.assertEqual(self.depot.statuts, [(copie_id, Statut.RENDUE, "ia", datetime(2026, 10, 20, 10, 0))])
        surcharge = Surcharge(None, "EX1", CHAINES_DEFAUT[TypeExercice.MISE_EN_SITUATION])
        self.cas(DepotMemoire(Exercice(TypeExercice.LIVRABLE, GRILLE, yaml)),
                 surcharges=lambda: (surcharge,)).executer(soumission())
        self.assertEqual(self.depot.statuts[0][2:], ("controles", datetime(2026, 10, 20, 9, 0)))


class TestContenu(unittest.TestCase):
    def test_signature_stable_et_sensible_au_rendu(self):
        a = Contenu.signature_de(soumission())
        self.assertEqual(a, Contenu.signature_de(soumission(status="Pass")))
        self.assertNotEqual(a, Contenu.signature_de(soumission(answer="autre")))
        self.assertNotEqual(a, Contenu.signature_de(soumission(assignment_attachment="/f")))
