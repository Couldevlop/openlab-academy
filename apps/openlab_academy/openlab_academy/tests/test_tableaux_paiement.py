"""Vues de lecture du paiement : dossier de l'apprenant, intendance, fiche, résumé, tableur (faux ports)."""
import unittest
from dataclasses import replace
from datetime import date

from openlab_academy.application.paiements import DossierAbsent
from openlab_academy.application.ports_paiement import DossierEnregistre, FiltresTableau, LigneDossier
from openlab_academy.application.tableaux_paiement import (
    LIGNES_MAX, Fiche, FiltreInvalide, Intendance, Resume, lire_filtres, neutraliser, tableur, vue_apprenant)
from openlab_academy.domain.dossier_paiement import Dossier, Statut
from openlab_academy.domain.echeancier import Echeance, Mode, Tarif

AUJOURDHUI = date(2026, 11, 15)
TARIF = Tarif(10000, 100000, 110000, 120000)
ECHEANCES = (Echeance(date(2026, 10, 15), 10000, "Frais d'inscription"),
             Echeance(date(2026, 11, 10), 45000, "Échéance"), Echeance(date(2026, 12, 10), 45000, "Échéance"))


def ligne(nom, apprenant, paye, cours="C1", mode=Mode.DEUX_TRANCHES, **dossier):
    return LigneDossier(nom, apprenant, f"Nom {apprenant}", f"{apprenant}@x.ci", cours, f"Titre {cours}", "B1", mode,
                        date(2026, 10, 15), Dossier(ECHEANCES, paye, frais_inscription=10000, **dossier))


A_JOUR = ligne("D-A", "a", 55000)
EN_RETARD = ligne("D-B", "b", 0, cours="C2", mode=Mode.MENSUEL)
SOLDE = ligne("D-C", "c", 100000, mode=Mode.UNE_FOIS)


class Tableaux:
    def __init__(self, lignes=(A_JOUR, EN_RETARD, SOLDE), encaisses=None):
        self.lignes = lignes
        self.encaisses = encaisses or {}
        self.filtres, self.appels_encaisse, self.journaux = [], [], []

    def dossiers(self, filtres):
        self.filtres.append(filtres)
        return tuple(x for x in self.lignes if filtres.parcours in (None, x.cours))

    def ligne(self, nom):
        return next((x for x in self.lignes if x.nom == nom), None)

    def encaisse(self, du, au, dossiers=None):
        self.appels_encaisse.append((du, au, dossiers))
        return self.encaisses.get((du, au), 0)

    def paiements(self, dossier):
        return ({"montant": 55000, "moyen": "virement", "reference": "VIR-1", "statut": "confirme"},)

    def rappels(self, dossier):
        return ({"date_limite": "2026-12-10", "jours_avant": 7, "canal": "sms", "statut": "envoye"},)

    def journal(self, dossier, limite):
        self.journaux.append((dossier, limite))
        return ({"acteur": "i@x.ci", "action": "delai_accorde", "motif": "M", "horodatage": "2026-11-15 10:00:00",
                 "avant": {}, "apres": {}},)


class TestFiltres(unittest.TestCase):
    def test_valeurs_valides(self):
        f, s = lire_filtres("C1", "B1", "mensuel", "en_retard", "2026-10-01", "2026-10-31")
        self.assertEqual(f, FiltresTableau("C1", "B1", Mode.MENSUEL, date(2026, 10, 1), date(2026, 10, 31)))
        self.assertIs(s, Statut.EN_RETARD)

    def test_absents_ou_vides(self):
        self.assertEqual(lire_filtres(), (FiltresTableau(), None))
        self.assertEqual(lire_filtres("", " ", "", "", "", ""), (FiltresTableau(), None))

    def test_valeurs_refusees(self):
        cas = [{"mode": "gratuit"}, {"statut": "bloque"}, {"du": "2026-13-01"}, {"au": "15/11/2026"},
               {"du": "2026-11-02", "au": "2026-11-01"}, {"parcours": "x" * 141}, {"cohorte": ["B1"]},
               {"du": 20261101}, {"mode": "MENSUEL"}, {"du": "2026-11-01T00:00"}]
        for c in cas:
            with self.subTest(c=c), self.assertRaises(FiltreInvalide):
                lire_filtres(**c)


class TestVueApprenant(unittest.TestCase):
    def enregistre(self, paye=0, **dossier):
        return DossierEnregistre("D-A", "a@x.ci", "C1", Mode.DEUX_TRANCHES, "+2250700000000", TARIF,
                                 date(2026, 11, 2), date(2027, 2, 22),
                                 Dossier(ECHEANCES, paye, frais_inscription=10000, **dossier), date(2026, 10, 15))

    def test_dossier_en_retard(self):
        v = vue_apprenant(self.enregistre(), "Titre C1", AUJOURDHUI, True)
        self.assertEqual(v, {
            "cours": "C1", "titre": "Titre C1", "mode": "deux_tranches", "telephone": "+2250700000000",
            "tarif": {"frais_inscription": 10000, "une_fois": 100000, "deux_tranches": 110000, "mensuel": 120000},
            "echeances": [
                {"date_limite": "2026-10-15", "montant": 10000, "libelle": "Frais d'inscription", "couverte": False},
                {"date_limite": "2026-11-10", "montant": 45000, "libelle": "Échéance", "couverte": False},
                {"date_limite": "2026-12-10", "montant": 45000, "libelle": "Échéance", "couverte": False}],
            "paye": 0, "reste": 100000, "statut": "en_retard",
            "prochaine": {"date_limite": "2026-10-15", "montant": 10000}, "paiement_en_ligne": True,
            "bloque": True, "instructions_virement": ""})

    def test_instructions_de_virement_rendues_et_blocage_selon_le_domaine(self):
        v = vue_apprenant(self.enregistre(55000), "T", AUJOURDHUI, False, "Banque X\nIBAN CI00 0000")
        self.assertEqual((v["instructions_virement"], v["bloque"]), ("Banque X\nIBAN CI00 0000", False))
        v = vue_apprenant(self.enregistre(0, delai_jusqu_au=date(2026, 11, 30)), "T", AUJOURDHUI, False, None)
        self.assertEqual((v["statut"], v["bloque"], v["instructions_virement"]), ("a_jour", False, ""))

    def test_partiellement_paye_puis_solde_puis_dispense(self):
        v = vue_apprenant(self.enregistre(10003), "T", AUJOURDHUI, False)
        self.assertEqual([e["couverte"] for e in v["echeances"]], [True, False, False])
        self.assertEqual(v["prochaine"], {"date_limite": "2026-11-10", "montant": 45000})
        self.assertFalse(v["paiement_en_ligne"])
        v = vue_apprenant(self.enregistre(100000), "T", AUJOURDHUI, True)
        self.assertEqual((v["statut"], v["reste"], v["prochaine"]), ("solde", 0, None))
        v = vue_apprenant(self.enregistre(0, dispense=True), "T", AUJOURDHUI, True)
        self.assertEqual((v["statut"], v["reste"], v["prochaine"]), ("dispense", 0, None))

    def test_frais_au_dela_du_calendrier(self):
        d = replace(self.enregistre(), dossier=Dossier((), 0, frais_inscription=10000))
        self.assertEqual(vue_apprenant(d, "T", AUJOURDHUI, True)["prochaine"], {"date_limite": None, "montant": 10000})


class TestIntendance(unittest.TestCase):
    def test_indicateurs_exacts_sur_trois_dossiers(self):
        t = Tableaux(encaisses={(date(2026, 11, 1), date(2026, 11, 30)): 65000})
        v = Intendance(t, lambda: AUJOURDHUI).executer(FiltresTableau())
        self.assertEqual(v["indicateurs"], {"encaisse_mois": 65000, "encours_30j": 90000,
                                            "en_retard": {"montant": 55000, "apprenants": 1}, "bloques": 1})
        self.assertEqual(t.appels_encaisse, [(date(2026, 11, 1), date(2026, 11, 30), None)])
        self.assertFalse(v["tronque"])
        self.assertEqual(v["lignes"][1], {
            "dossier": "D-B", "apprenant": "b", "nom": "Nom b", "email": "b@x.ci", "parcours": "C2",
            "titre": "Titre C2", "cohorte": "B1", "mode": "mensuel", "paye": 0, "total": 100000, "reste": 100000,
            "prochaine": {"date_limite": "2026-10-15", "montant": 10000}, "statut": "en_retard", "bloque": True})
        self.assertEqual([(x["statut"], x["bloque"]) for x in v["lignes"]],
                         [("a_jour", False), ("en_retard", True), ("solde", False)])
        self.assertNotIn("telephone", v["lignes"][0])

    def test_filtre_de_statut_selon_le_domaine_et_encaisse_restreint(self):
        t = Tableaux()
        v = Intendance(t, lambda: AUJOURDHUI).executer(FiltresTableau(), Statut.EN_RETARD)
        self.assertEqual([x["dossier"] for x in v["lignes"]], ["D-B"])
        self.assertEqual(t.appels_encaisse[-1][2], ("D-B",))
        self.assertEqual(v["indicateurs"]["encours_30j"], 45000)

    def test_filtres_transmis_et_encaisse_restreint(self):
        t = Tableaux()
        f = FiltresTableau(parcours="C1")
        v = Intendance(t, lambda: AUJOURDHUI).executer(f)
        self.assertEqual(t.filtres, [f])
        self.assertEqual([x["dossier"] for x in v["lignes"]], ["D-A", "D-C"])
        self.assertEqual(t.appels_encaisse[-1][2], ("D-A", "D-C"))

    def test_aucun_dossier(self):
        t = Tableaux(lignes=())
        v = Intendance(t, lambda: AUJOURDHUI).executer(FiltresTableau(cohorte="B9"))
        self.assertEqual(v["indicateurs"]["encaisse_mois"], 0)
        self.assertEqual(t.appels_encaisse, [])

    def test_delai_arriere_compte_mais_pas_bloque_et_apprenants_distincts(self):
        lignes = (EN_RETARD, ligne("D-B2", "b", 0, cours="C1"),
                  ligne("D-D", "d", 0, delai_jusqu_au=date(2026, 11, 30)), ligne("D-E", "e", 0, dispense=True))
        v = Intendance(Tableaux(lignes), lambda: AUJOURDHUI).executer(FiltresTableau())
        self.assertEqual(v["indicateurs"]["en_retard"], {"montant": 165000, "apprenants": 2})
        self.assertEqual(v["indicateurs"]["bloques"], 1)
        self.assertEqual([x["statut"] for x in v["lignes"]], ["en_retard", "en_retard", "a_jour", "dispense"])

    def test_lignes_plafonnees(self):
        lignes = tuple(ligne(f"D{i}", f"u{i}", 0) for i in range(3))
        v = Intendance(Tableaux(lignes), lambda: AUJOURDHUI).executer(FiltresTableau(), limite=2)
        self.assertEqual((len(v["lignes"]), v["tronque"]), (2, True))
        self.assertEqual(v["indicateurs"]["en_retard"]["apprenants"], 3)
        self.assertGreater(LIGNES_MAX, 1000)


class Depot:
    def __init__(self, d):
        self.d = d

    def par_nom(self, nom):
        return self.d if self.d and self.d.nom == nom else None


class TestFiche(unittest.TestCase):
    def test_fiche_complete(self):
        d = DossierEnregistre("D-B", "b", "C2", Mode.MENSUEL, "+2250700000000", TARIF, date(2026, 11, 2),
                              date(2027, 2, 22), EN_RETARD.dossier, date(2026, 10, 15))
        t = Tableaux()
        v = Fiche(Depot(d), t, lambda: AUJOURDHUI).executer("D-B")
        self.assertEqual((v["dossier"], v["apprenant"], v["nom"], v["email"], v["telephone"]),
                         ("D-B", "b", "Nom b", "b@x.ci", "+2250700000000"))
        self.assertEqual((v["statut"], v["bloque"], v["arriere"], v["dispense"], v["delai_jusqu_au"]),
                         ("en_retard", True, 55000, False, None))
        self.assertEqual(v["tarif"]["mensuel"], 120000)
        self.assertEqual(v["inscription"], "2026-10-15")
        self.assertEqual(len(v["echeances"]), 3)
        self.assertEqual(v["paiements"][0]["reference"], "VIR-1")
        self.assertEqual(v["rappels"][0]["canal"], "sms")
        self.assertEqual(v["journal"][0]["acteur"], "i@x.ci")
        self.assertEqual(t.journaux, [("D-B", 200)])

    def test_delai_affiche(self):
        d = DossierEnregistre("D-B", "b", "C2", Mode.MENSUEL, "", TARIF, date(2026, 11, 2), date(2027, 2, 22),
                              replace(EN_RETARD.dossier, delai_jusqu_au=date(2026, 11, 30)), date(2026, 10, 15))
        v = Fiche(Depot(d), Tableaux(), lambda: AUJOURDHUI).executer("D-B")
        self.assertEqual((v["delai_jusqu_au"], v["statut"], v["bloque"]), ("2026-11-30", "a_jour", False))

    def test_dossier_inconnu(self):
        with self.assertRaises(DossierAbsent):
            Fiche(Depot(None), Tableaux(), lambda: AUJOURDHUI).executer("D-X")
        d = DossierEnregistre("D-Z", "z", "C2", Mode.MENSUEL, "", TARIF, AUJOURDHUI, AUJOURDHUI,
                              EN_RETARD.dossier, AUJOURDHUI)
        with self.assertRaises(DossierAbsent):  # dossier supprimé entre les deux lectures
            Fiche(Depot(d), Tableaux(), lambda: AUJOURDHUI).executer("D-Z")


class TestResume(unittest.TestCase):
    def test_resume(self):
        t = Tableaux(encaisses={(date(2026, 11, 1), date(2026, 11, 30)): 20000,
                                (date(2026, 10, 1), date(2026, 10, 15)): 16000})
        v = Resume(t, lambda: AUJOURDHUI).executer()
        self.assertEqual(t.filtres, [FiltresTableau()])
        self.assertEqual((v["encaisse_mois"], v["evolution_pct"], v["taux_recouvrement"], v["retards"],
                          v["bloques"]), (20000, 25.0, 66.7, 1, 1))  # (55 000 + 0 + 55 000) / (3 × 55 000)
        self.assertEqual(v["par_parcours"], [
            {"parcours": "C1", "titre": "Titre C1", "inscrits": 2, "encaisse": 155000, "reste": 45000},
            {"parcours": "C2", "titre": "Titre C2", "inscrits": 1, "encaisse": 0, "reste": 100000}])
        self.assertEqual(v["modes"], {"une_fois": 1, "deux_tranches": 1, "mensuel": 1})
        self.assertEqual(len(v["dernieres_actions"]), 1)
        self.assertEqual(t.journaux, [(None, 5)])

    def test_sans_reference_ni_exigible(self):
        v = Resume(Tableaux(lignes=()), lambda: AUJOURDHUI).executer()
        self.assertEqual((v["encaisse_mois"], v["evolution_pct"], v["taux_recouvrement"], v["par_parcours"]),
                         (0, None, None, []))

    def test_meme_periode_du_mois_precedent_bornee_a_sa_fin(self):
        t = Tableaux(lignes=())
        Resume(t, lambda: date(2026, 3, 31)).executer()
        self.assertEqual(t.appels_encaisse, [(date(2026, 3, 1), date(2026, 3, 31), None),
                                             (date(2026, 2, 1), date(2026, 2, 28), None)])
        t = Tableaux(lignes=())
        Resume(t, lambda: date(2026, 1, 20)).executer()
        self.assertEqual(t.appels_encaisse, [(date(2026, 1, 1), date(2026, 1, 31), None),
                                             (date(2025, 12, 1), date(2025, 12, 20), None)])


class TestTableur(unittest.TestCase):
    def test_formules_neutralisees(self):
        for v in ("=1+1", "+33", "-2", "@SUM(A1)", "\t=1", "\r=1"):
            with self.subTest(v=v):
                self.assertEqual(neutraliser(v), "'" + v)
        for v in ("  =1+1", "  @x", "＝1+1", "＋33", "－2", "＠SUM(A1)", " ＝1"):
            with self.subTest(v=v):
                self.assertEqual(neutraliser(v), "'" + v)
        self.assertEqual(neutraliser("Aya"), "Aya")
        self.assertEqual(neutraliser("  Aya"), "  Aya")
        self.assertEqual(neutraliser(-5), -5)
        self.assertEqual(neutraliser(None), "")

    def test_lignes(self):
        v = Intendance(Tableaux(), lambda: AUJOURDHUI).executer(FiltresTableau())
        lignes = [dict(x, nom="=HYPERLINK(\"http://x\")") if x["dossier"] == "D-A" else x for x in v["lignes"]]
        t = tableur(lignes)
        self.assertEqual(t[0], ["Dossier", "Apprenant", "Nom", "E-mail", "Parcours", "Cohorte", "Mode", "Payé",
                                "Total", "Reste", "Prochaine échéance", "Montant prochaine", "Statut", "Bloqué"])
        self.assertEqual(t[1], ["D-A", "a", "'=HYPERLINK(\"http://x\")", "a@x.ci", "Titre C1", "B1",
                                "Deux tranches", 55000, 100000, 45000, "2026-12-10", 45000, "À jour", "non"])
        self.assertEqual(t[3][10:14], ["", "", "Soldé", "non"])
        self.assertEqual(t[2][13], "oui")


if __name__ == "__main__":
    unittest.main()
