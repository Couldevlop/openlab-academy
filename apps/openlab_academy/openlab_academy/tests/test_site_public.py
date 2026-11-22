"""La façade publique est une vitrine : elle montre tout le catalogue, et n'engage rien.

Deux exigences gouvernent ce fichier, et elles tirent en sens contraire.

La première : **tout le catalogue se montre**. Un parcours masqué par la phase de lancement est
visible du visiteur, fiche comprise. L'existence et le programme des parcours à venir sont devenus
l'argument de vente — c'est un renversement assumé de la précaution d'origine, qui les traitait
comme inexistants.

La seconde : **la vitrine ne livre que ce qu'elle annonce**. Le corps des séances reste aux
inscrits ; `published` reste l'interrupteur qui retire une page du site ; et une fiche qui
n'accueille personne n'affiche ni session, ni dates, ni places restantes.
"""
import frappe
from frappe.tests.utils import FrappeTestCase

from openlab_academy.domain.cohorte import PLACES_FENETRE
from openlab_academy.entrypoints import site_api
from openlab_academy.infrastructure.inscriptions_frappe import (PLACES_PAR_DEFAUT,
                                                                CohortesPubliquesFrappe,
                                                                TarifsPublicsFrappe)
from openlab_academy.infrastructure import domaines_frappe
from openlab_academy.www import catalogue_public

DOCTYPE_REGLAGES = "Reglages OpenLab Academy"
CHAMP_GRATUIT = catalogue_public.CHAMP_GRATUIT
CORPS_SECRET = "Le corps de la séance, réservé aux inscrits."
TITRE_SEANCE = "Installer la chaîne de développement"


class TestLaVitrineMontreToutLeCatalogue(FrappeTestCase):
    def setUp(self):
        self.ouvert = self.cours("Vitrine — parcours ouvert")
        self.masque = self.cours("Vitrine — parcours masqué")
        self.depublie = self.cours("Vitrine — parcours retiré", publie=0)
        doc = frappe.get_single(DOCTYPE_REGLAGES)
        doc.phase_lancement = 1
        doc.set("parcours_lancement", [{"cours": self.ouvert}])
        doc.save(ignore_permissions=True)
        frappe.set_user("Guest")

    def tearDown(self):
        frappe.set_user("Administrator")
        frappe.db.rollback()

    def cours(self, titre, publie=1):
        return frappe.get_doc({"doctype": "LMS Course", "title": titre, "short_introduction": "i",
                               "description": "d", "published": publie,
                               "instructors": [{"instructor": "Administrator"}]}
                              ).insert(ignore_permissions=True).name

    def noms_visibles(self):
        return [p.name for p in catalogue_public.parcours_visibles()]

    def test_un_parcours_masque_par_la_phase_de_lancement_est_au_catalogue(self):
        """C'est tout l'objet du lot : un catalogue de neuf entrées dont huit sont cachées se lit
        comme un catalogue d'une entrée."""
        self.assertIn(self.masque, self.noms_visibles())

    def test_le_parcours_du_lancement_y_est_aussi(self):
        self.assertIn(self.ouvert, self.noms_visibles())

    def test_un_parcours_retire_du_catalogue_n_y_est_pas(self):
        """`published` reste l'interrupteur : `retirer_parcours_echus` dépublie chaque nuit un
        parcours limité dont la fenêtre s'est fermée, et un brouillon commencé dans
        l'administration ne doit pas devenir public en naissant."""
        self.assertNotIn(self.depublie, self.noms_visibles())

    def test_la_fiche_d_un_parcours_masque_repond(self):
        self.assertEqual(site_api.parcours_du_catalogue(self.masque), self.masque)

    def test_la_fiche_d_un_parcours_retire_reste_introuvable(self):
        self.assertEqual(site_api.parcours_du_catalogue(self.depublie), "")

    def test_un_parcours_inconnu_reste_introuvable(self):
        self.assertEqual(site_api.parcours_du_catalogue("parcours-qui-n-existe-pas"), "")

    def test_un_nom_qui_n_est_pas_une_chaine_est_refuse(self):
        """Le nom vient de l'URL ou du client : il ne doit pas atteindre la base tel quel."""
        for valeur in (None, 0, [], {"name": "x"}):
            with self.subTest(repr(valeur)):
                self.assertEqual(site_api.parcours_du_catalogue(valeur), "")


class TestLaVitrineNeLivreQueCeQuElleAnnonce(FrappeTestCase):
    def setUp(self):
        self.masque = self.cours("Vitrine — contenu réservé")
        self.chapitre = frappe.get_doc({"doctype": "Course Chapter", "title": "Les bases",
                                        "course": self.masque}).insert(ignore_permissions=True)
        frappe.get_doc({"doctype": "Chapter Reference", "parent": self.masque,
                        "parenttype": "LMS Course", "parentfield": "chapters",
                        "chapter": self.chapitre.name, "idx": 1}).insert(ignore_permissions=True)
        lecon = frappe.get_doc({"doctype": "Course Lesson", "title": TITRE_SEANCE,
                                "chapter": self.chapitre.name, "course": self.masque,
                                "content": CORPS_SECRET}).insert(ignore_permissions=True)
        frappe.get_doc({"doctype": "Lesson Reference", "parent": self.chapitre.name,
                        "parenttype": "Course Chapter", "parentfield": "lessons",
                        "lesson": lecon.name, "idx": 1}).insert(ignore_permissions=True)
        doc = frappe.get_single(DOCTYPE_REGLAGES)
        doc.phase_lancement = 1
        doc.set("parcours_lancement", [])
        doc.save(ignore_permissions=True)
        frappe.set_user("Guest")

    def tearDown(self):
        frappe.set_user("Administrator")
        frappe.db.rollback()

    def cours(self, titre):
        return frappe.get_doc({"doctype": "LMS Course", "title": titre, "short_introduction": "i",
                               "description": "d", "published": 1,
                               "instructors": [{"instructor": "Administrator"}]}
                              ).insert(ignore_permissions=True).name

    def test_le_programme_montre_les_titres_et_jamais_le_corps(self):
        from openlab_academy.www import parcours_public
        programme = parcours_public._programme(self.masque)
        rendu = repr(programme)
        self.assertIn(TITRE_SEANCE, rendu)
        self.assertNotIn(CORPS_SECRET, rendu)

    def test_un_chapitre_sans_titre_est_ecarte_du_programme(self):
        """Un bloc anonyme n'apprend rien au visiteur, et une puce vide dans un programme se voit."""
        from openlab_academy.www import parcours_public
        muet = frappe.get_doc({"doctype": "Course Chapter", "title": "À nommer",
                               "course": self.masque}).insert(ignore_permissions=True)
        frappe.get_doc({"doctype": "Chapter Reference", "parent": self.masque,
                        "parenttype": "LMS Course", "parentfield": "chapters",
                        "chapter": muet.name, "idx": 2}).insert(ignore_permissions=True)
        frappe.db.set_value("Course Chapter", muet.name, "title", "")
        titres = [bloc["titre"] for bloc in parcours_public._programme(self.masque)]
        self.assertEqual(titres, ["Les bases"])

    def test_une_seance_sans_titre_est_ecartee_du_bloc(self):
        from openlab_academy.www import parcours_public
        lecon = frappe.get_doc({"doctype": "Course Lesson", "title": "À nommer",
                                "chapter": self.chapitre.name, "course": self.masque,
                                "content": ""}).insert(ignore_permissions=True)
        frappe.get_doc({"doctype": "Lesson Reference", "parent": self.chapitre.name,
                        "parenttype": "Course Chapter", "parentfield": "lessons",
                        "lesson": lecon.name, "idx": 2}).insert(ignore_permissions=True)
        frappe.db.set_value("Course Lesson", lecon.name, "title", "")
        self.assertEqual(parcours_public._programme(self.masque)[0]["seances"], [TITRE_SEANCE])

    def test_l_offre_d_un_parcours_sans_cohorte_ne_promet_ni_date_ni_place(self):
        offre = site_api.offre(self.masque)
        self.assertFalse(offre["ouverte"])
        self.assertEqual(offre["session"], "")
        self.assertEqual((offre["debut"], offre["fin"]), ("", ""))
        self.assertEqual(offre["places_restantes"], 0)

    def test_l_offre_d_un_parcours_retire_est_refusee(self):
        depublie = self.cours("Vitrine — offre retirée")
        frappe.db.set_value("LMS Course", depublie, "published", 0)
        frappe.clear_document_cache("LMS Course", depublie)
        with self.assertRaises(frappe.DoesNotExistError):
            site_api.offre(depublie)


class TestLaPorteDInscriptionDuSite(FrappeTestCase):
    """`inscrire` est le seul point d'écriture de la façade, et il est fermé tant que les réglages
    ne l'ont pas réouvert. Un bouton caché dans un gabarit n'est pas une règle : c'est ici que le
    refus doit se voir."""

    def setUp(self):
        self.cours = frappe.get_doc(
            {"doctype": "LMS Course", "title": "Porte — parcours gratuit", "short_introduction": "i",
             "description": "d", "published": 1, CHAMP_GRATUIT: 1,
             "instructors": [{"instructor": "Administrator"}]}).insert(ignore_permissions=True).name
        self.apprenant = self.eleve("porte.eleve@example.ci")
        # La phase de lancement masque tout parcours hors de sa liste, et le crochet
        # `LMS Enrollment` du LMS refuse alors l'inscription — ce qui est son travail. Ici on
        # éprouve la porte de la façade, pas le masquage : on sort donc de la phase.
        doc = frappe.get_single(DOCTYPE_REGLAGES)
        doc.phase_lancement = 0
        doc.save(ignore_permissions=True)
        self.suspendre(True)

    def tearDown(self):
        frappe.set_user("Administrator")
        frappe.db.rollback()

    def eleve(self, courriel):
        if not frappe.db.exists("User", courriel):
            frappe.get_doc({"doctype": "User", "email": courriel, "first_name": "Porte",
                            "send_welcome_email": 0}).insert(ignore_permissions=True)
        return courriel

    def suspendre(self, suspendues):
        doc = frappe.get_single(DOCTYPE_REGLAGES)
        doc.inscriptions_ouvertes = 0 if suspendues else 1
        doc.save(ignore_permissions=True)

    def test_un_appel_direct_est_refuse_pendant_la_suspension(self):
        frappe.set_user(self.apprenant)
        with self.assertRaises(frappe.ValidationError):
            site_api.inscrire(self.cours)
        self.assertFalse(frappe.db.exists("LMS Enrollment",
                                          {"course": self.cours, "member": self.apprenant}))

    def test_un_parcours_retire_est_refuse_comme_inexistant(self):
        frappe.set_user(self.apprenant)
        with self.assertRaises(frappe.DoesNotExistError):
            site_api.inscrire("parcours-qui-n-existe-pas")

    def test_un_visiteur_sans_compte_est_refuse(self):
        """Garde-fou de dernier recours : la page ne montre le bouton qu'aux connectés, l'API ne
        s'y fie pas."""
        self.suspendre(False)
        frappe.set_user("Guest")
        with self.assertRaises(frappe.ValidationError):
            site_api.inscrire(self.cours)

    def test_reouverte_la_porte_inscrit_l_utilisateur_de_la_session(self):
        self.suspendre(False)
        frappe.set_user(self.apprenant)
        destination = site_api.inscrire(self.cours)["destination"]
        self.assertIn(self.cours, destination)
        self.assertTrue(frappe.db.exists("LMS Enrollment",
                                         {"course": self.cours, "member": self.apprenant}))

    def test_un_deuxieme_appel_ne_cree_pas_une_seconde_inscription(self):
        """Rejouable : deux clics, ou un double envoi, ne doivent pas doubler l'inscription."""
        self.suspendre(False)
        frappe.set_user(self.apprenant)
        site_api.inscrire(self.cours)
        site_api.inscrire(self.cours)
        self.assertEqual(frappe.db.count("LMS Enrollment",
                                         {"course": self.cours, "member": self.apprenant}), 1)

    def test_l_offre_est_lisible_par_un_visiteur_sans_compte(self):
        """C'est tout l'intérêt d'une façade : montrer avant d'exiger un compte."""
        frappe.set_user("Guest")
        offre = site_api.offre(self.cours)
        self.assertTrue(offre["gratuit"])
        self.assertFalse(offre["deja_inscrit"])

    def test_l_offre_ne_dit_deja_inscrit_que_de_l_utilisateur_de_la_session(self):
        self.suspendre(False)
        frappe.set_user(self.apprenant)
        site_api.inscrire(self.cours)
        self.assertTrue(site_api.offre(self.cours)["deja_inscrit"])
        frappe.set_user("Guest")
        self.assertFalse(site_api.offre(self.cours)["deja_inscrit"])


class TestLesPagesPubliquesSeRendent(FrappeTestCase):
    """Les trois contrôleurs de page, exercés pour de vrai : ils sont la façade, et un contexte qui
    casse ne se voit qu'à l'écran."""

    def setUp(self):
        self.categorie = "Vitrine Data"
        if not frappe.db.exists("LMS Category", self.categorie):
            frappe.get_doc({"doctype": "LMS Category", "category": self.categorie}
                           ).insert(ignore_permissions=True)
        self.payant = frappe.get_doc(
            {"doctype": "LMS Course", "title": "Pages — parcours payant", "short_introduction": "a",
             "description": "d", "published": 1, "category": self.categorie,
             domaines_frappe.CHAMP: "ia",
             "instructors": [{"instructor": "Administrator"}]}).insert(ignore_permissions=True).name
        self.gratuit = frappe.get_doc(
            {"doctype": "LMS Course", "title": "Pages — parcours gratuit", "short_introduction": "a",
             "description": "d", "published": 1, CHAMP_GRATUIT: 1,
             "instructors": [{"instructor": "Administrator"}]}).insert(ignore_permissions=True).name
        frappe.set_user("Guest")

    def tearDown(self):
        frappe.set_user("Administrator")
        frappe.db.rollback()

    def test_l_accueil_compte_ses_chiffres_et_met_des_parcours_en_vedette(self):
        from openlab_academy.www import accueil
        context = frappe._dict()
        accueil.get_context(context)
        self.assertGreaterEqual(context.chiffres["parcours"], 2)
        self.assertGreaterEqual(context.chiffres["gratuits"], 1)
        self.assertLessEqual(len(context.vedette), accueil.PARCOURS_EN_VEDETTE)
        self.assertEqual(context.lien_parcours, "/parcours")
        self.assertTrue(context.metatags["description"])

    def test_l_accueil_met_les_parcours_ouverts_en_tete(self):
        """C'est sur eux qu'on peut agir aujourd'hui."""
        from openlab_academy.www import accueil
        context = frappe._dict()
        accueil.get_context(context)
        etats = [p["offre"]["ouverte"] for p in context.vedette]
        self.assertEqual(etats, sorted(etats, reverse=True))

    def test_le_catalogue_liste_les_parcours_avec_leur_prix_lisible(self):
        from openlab_academy.www import parcours
        context = frappe._dict()
        parcours.get_context(context)
        noms = [p["name"] for p in context.parcours]
        self.assertIn(self.payant, noms)
        self.assertIn(self.gratuit, noms)
        self.assertTrue(all("prix" in p for p in context.parcours))
        self.assertTrue(all("etat_libelle" in p for p in context.parcours))

    def test_le_catalogue_met_en_tete_ce_qu_on_peut_rejoindre(self):
        """Un parcours qui n'accueille personne ne doit pas ouvrir la page : le visiteur juge
        l'academie sur la premiere carte, et « en preparation » n'invite a rien."""
        from openlab_academy.www import parcours
        context = frappe._dict()
        parcours.get_context(context)
        rangs = [catalogue_public.RANG_DES_ETATS[p["etat"]] for p in context.parcours]
        self.assertEqual(rangs, sorted(rangs))

    def test_le_tri_par_etat_ne_perd_ni_n_invente_aucune_carte(self):
        cartes = [{"name": "a", "etat": catalogue_public.PREPARATION},
                  {"name": "b", "etat": catalogue_public.OUVERTE},
                  {"name": "c", "etat": catalogue_public.LIBRE},
                  {"name": "d", "etat": catalogue_public.BIENTOT}]
        range_ = catalogue_public.par_etat(cartes)
        self.assertEqual([c["name"] for c in range_], ["b", "c", "d", "a"])
        self.assertEqual(len(range_), len(cartes))

    def test_le_catalogue_ne_propose_que_des_familles_qui_filtrent_vraiment(self):
        """Un filtre qui ne filtre rien est un bouton qui déçoit : seules les familles présentes
        au catalogue sont proposées, et leur compte doit correspondre aux cartes affichées."""
        from openlab_academy.www import parcours
        context = frappe._dict()
        parcours.get_context(context)
        affichees = [p["domaine_libelle"] for p in context.parcours if p["domaine_libelle"]]
        for famille in context.familles:
            with self.subTest(famille["libelle"]):
                self.assertIn(famille["libelle"], affichees)
                self.assertEqual(famille["compte"], affichees.count(famille["libelle"]))
                self.assertTrue(famille["teinte"].startswith("#"))

    def test_une_famille_sans_parcours_n_apparait_pas_dans_les_filtres(self):
        from openlab_academy.www import parcours
        context = frappe._dict()
        parcours.get_context(context)
        proposees = {f["libelle"] for f in context.familles}
        self.assertIn("Intelligence artificielle", proposees)
        toutes = {d.libelle for d in domaines_frappe.tous()}
        self.assertTrue(proposees <= toutes)

    def test_la_fiche_porte_son_offre_et_son_lien_de_connexion(self):
        from openlab_academy.www import parcours_public
        context = frappe._dict()
        frappe.form_dict["parcours"] = self.gratuit
        try:
            parcours_public.get_context(context)
        finally:
            frappe.form_dict.pop("parcours", None)
        self.assertEqual(context.parcours, self.gratuit)
        self.assertTrue(context.offre["gratuit"])
        self.assertFalse(context.connecte)
        self.assertIn(self.gratuit, context.lien_connexion)
        self.assertEqual(context.metatags["title"], context.titre)

    def test_la_fiche_d_un_parcours_retire_est_une_page_absente(self):
        from openlab_academy.www import parcours_public
        frappe.db.set_value("LMS Course", self.payant, "published", 0)
        frappe.clear_document_cache("LMS Course", self.payant)
        frappe.form_dict["parcours"] = self.payant
        try:
            with self.assertRaises(frappe.DoesNotExistError):
                parcours_public.get_context(frappe._dict())
        finally:
            frappe.form_dict.pop("parcours", None)


class TestLesCohortesVuesDeLaFacade(FrappeTestCase):
    """L'adaptateur qui traduit une cohorte du LMS en candidate du domaine.

    Deux traductions s'y jouent et toutes deux se paient cher si elles glissent : une cohorte sans
    nombre de places n'est pas illimitée, elle est mal renseignée ; et la fenêtre d'accès libre se
    reconnaît à son nombre de places sentinelle, pas à un champ.
    """

    def setUp(self):
        self.cours = frappe.get_doc(
            {"doctype": "LMS Course", "title": "Cohortes — parcours", "short_introduction": "a",
             "description": "d", "published": 1,
             "instructors": [{"instructor": "Administrator"}]}).insert(ignore_permissions=True).name

    def tearDown(self):
        frappe.db.rollback()

    def lot(self, titre, places, debut, fin, publiee=1):
        return frappe.get_doc({
            "doctype": "LMS Batch", "title": titre, "start_date": debut, "end_date": fin,
            "seat_count": places, "published": publiee, "start_time": "09:00:00",
            "end_time": "12:00:00", "timezone": "Africa/Abidjan", "description": "d",
            "batch_details": "d", "medium": "Online",
            "instructors": [{"instructor": "Administrator"}],
            "courses": [{"course": self.cours}]}).insert(ignore_permissions=True)

    def cohorte(self, titre, places, debut, fin, publiee=1):
        return self.lot(titre, places, debut, fin, publiee).name

    def candidates(self):
        return CohortesPubliquesFrappe().candidates(self.cours)

    def test_un_parcours_sans_cohorte_n_a_aucune_candidate(self):
        self.assertEqual(self.candidates(), ())

    def test_une_cohorte_devient_une_candidate_avec_ses_places_restantes(self):
        self.cohorte("Promo mesurée", 30, "2026-12-01", "2027-03-01")
        candidate = self.candidates()[0]
        self.assertEqual(candidate.places, 30)
        self.assertEqual(candidate.places_restantes, 30)
        self.assertTrue(candidate.publiee)
        self.assertFalse(candidate.libre)

    def test_une_cohorte_sans_places_renseignees_n_est_pas_illimitee(self):
        self.cohorte("Promo mal renseignée", 0, "2026-12-01", "2027-03-01")
        self.assertEqual(self.candidates()[0].places, PLACES_PAR_DEFAUT)

    def test_une_fenetre_d_acces_libre_se_reconnait_a_ses_places(self):
        self.cohorte("Fenêtre libre", PLACES_FENETRE, "2026-01-01", "2027-12-31")
        self.assertTrue(self.candidates()[0].libre)

    def test_une_cohorte_sans_dates_est_ecartee(self):
        """Elle n'est pas une offre : on ne sait ni quand elle commence ni quand elle finit."""
        lot = self.lot("Promo sans dates", 10, "2026-12-01", "2027-03-01")
        frappe.db.set_value("LMS Batch", lot.name, "end_date", None)
        self.assertEqual(self.candidates(), ())

    def test_un_parcours_payant_sans_tarif_n_a_pas_de_montant(self):
        self.assertIsNone(TarifsPublicsFrappe().montant(self.cours))


class TestLesPetitsOutilsDuCatalogue(FrappeTestCase):
    def tearDown(self):
        frappe.db.rollback()

    def test_un_montant_se_lit_sans_se_couper_en_fin_de_ligne(self):
        """Les deux espaces sont insécables, et c'est le but : ni le millier ni la devise ne doivent
        passer à la ligne suivante. D'où les caractères nommés plutôt qu'une espace ordinaire, qui
        rendrait ce test vert par accident le jour où quelqu'un les remplacerait."""
        fine = " "      # espace fine insécable, séparateur de milliers
        insecable = " "  # espace insécable, avant la devise
        self.assertEqual(catalogue_public.montant_lisible(250000),
                         f"250{fine}000{insecable}F CFA")
        self.assertEqual(catalogue_public.montant_lisible("250000"),
                         f"250{fine}000{insecable}F CFA")
        self.assertEqual(catalogue_public.montant_lisible(0), "")
        self.assertEqual(catalogue_public.montant_lisible(None), "")

    def test_le_lien_d_un_parcours_ne_peut_pas_sortir_de_son_prefixe(self):
        """Le nom vient de la base, mais rien n'empêche un titre d'y mettre une barre oblique."""
        self.assertEqual(catalogue_public.lien_de("mon-parcours"), "/parcours/mon-parcours")
        self.assertEqual(catalogue_public.lien_de("a/b"), "/parcours/a%2Fb")
        self.assertEqual(catalogue_public.lien_de("a b"), "/parcours/a%20b")

    def test_un_catalogue_vide_compte_zero_plutot_que_de_casser(self):
        self.assertEqual(catalogue_public.chiffres([]),
                         {"parcours": 0, "seances": 0, "gratuits": 0})


class TestLesQuatreEtatsHonnetes(FrappeTestCase):
    """Ce qu'une carte a le droit d'annoncer. « Fermé » n'en fait plus partie.

    Pour un parcours dont la conception n'est pas terminée, « fermé » se lit comme un refus alors
    qu'il s'agit d'une préparation : le visiteur s'en va au lieu de revenir.
    """

    def test_un_parcours_annonce_est_en_preparation(self):
        self.assertEqual(catalogue_public.etat_de({"upcoming": 1, "offre": {"ouverte": True}}),
                         catalogue_public.PREPARATION)

    def test_la_preparation_prime_sur_l_offre(self):
        """Un parcours annoncé n'a pas de contenu : quoi que dise l'offre, on ne vend pas du vide."""
        for offre in ({"ouverte": True, "gratuit": True}, {"ouverte": False}, {}):
            with self.subTest(offre):
                self.assertEqual(catalogue_public.etat_de({"upcoming": 1, "offre": offre}),
                                 catalogue_public.PREPARATION)

    def test_une_offre_fermee_est_bientot_ouverte(self):
        self.assertEqual(catalogue_public.etat_de({"upcoming": 0, "offre": {"ouverte": False}}),
                         catalogue_public.BIENTOT)

    def test_une_offre_ouverte_et_payante_annonce_ses_inscriptions(self):
        self.assertEqual(
            catalogue_public.etat_de({"upcoming": 0, "offre": {"ouverte": True, "gratuit": False}}),
            catalogue_public.OUVERTE)

    def test_l_acces_libre_exige_une_offre_reellement_ouverte(self):
        """Pendant une suspension, même un parcours gratuit n'accueille personne. L'annoncer libre
        serait un mensonge que le visiteur découvrirait au clic suivant."""
        self.assertEqual(
            catalogue_public.etat_de({"upcoming": 0, "offre": {"ouverte": False, "gratuit": True}}),
            catalogue_public.BIENTOT)
        self.assertEqual(
            catalogue_public.etat_de({"upcoming": 0, "offre": {"ouverte": True, "gratuit": True}}),
            catalogue_public.LIBRE)

    def test_une_offre_absente_ne_fait_pas_tomber_la_page(self):
        self.assertEqual(catalogue_public.etat_de({}), catalogue_public.BIENTOT)

    def test_chaque_etat_porte_un_libelle_et_aucun_ne_dit_ferme(self):
        for etat in (catalogue_public.PREPARATION, catalogue_public.BIENTOT,
                     catalogue_public.OUVERTE, catalogue_public.LIBRE):
            with self.subTest(etat):
                libelle = catalogue_public.libelle_etat(etat)
                self.assertTrue(libelle)
                self.assertNotIn("ferm", libelle.lower())

    def test_un_etat_inconnu_ne_rend_rien(self):
        self.assertEqual(catalogue_public.libelle_etat("n-importe-quoi"), "")

    def test_aucune_date_n_est_annoncee_dans_un_libelle(self):
        """Nous ne tenons aucune date d'ouverture : une date manquée coûte plus cher que son absence."""
        for etat in (catalogue_public.PREPARATION, catalogue_public.BIENTOT):
            with self.subTest(etat):
                libelle = catalogue_public.libelle_etat(etat)
                self.assertNotRegex(libelle, r"\d")


class TestCeQuUneCartePorte(FrappeTestCase):
    def setUp(self):
        self.categorie_doctype = "LMS Category"
        self.cours = frappe.get_doc({
            "doctype": "LMS Course", "title": "Parcours pour cartes", "short_introduction": "s",
            "description": "d", "published": 1,
            domaines_frappe.CHAMP: "ia"}).insert(ignore_permissions=True).name
        chapitre = frappe.get_doc({"doctype": "Course Chapter", "title": "Bloc",
                                   "course": self.cours}).insert(ignore_permissions=True)
        frappe.get_doc({"doctype": "Chapter Reference", "parent": self.cours,
                        "parenttype": "LMS Course", "parentfield": "chapters",
                        "chapter": chapitre.name, "idx": 1}).insert(ignore_permissions=True)
        for i in range(3):
            frappe.get_doc({"doctype": "Course Lesson", "title": f"Séance {i}", "chapter": chapitre.name,
                            "course": self.cours, "content": ""}).insert(ignore_permissions=True)

    def tearDown(self):
        frappe.db.rollback()

    def test_la_carte_porte_la_famille_et_sa_teinte(self):
        carte = catalogue_public.pour_les_cartes(catalogue_public.avec_offre(
            [c for c in catalogue_public.parcours_visibles() if c.name == self.cours]))[0]
        self.assertEqual(carte["domaine_libelle"], "Intelligence artificielle")
        self.assertTrue(carte["domaine_teinte"].startswith("#"))

    def test_un_parcours_sans_famille_ne_fait_pas_tomber_la_carte(self):
        """Il prendra la teinte neutre de la charte ; il ne casse pas la page."""
        frappe.db.set_value("LMS Course", self.cours, domaines_frappe.CHAMP, None)
        carte = catalogue_public.pour_les_cartes(catalogue_public.avec_offre(
            [c for c in catalogue_public.parcours_visibles() if c.name == self.cours]))[0]
        self.assertEqual((carte["domaine_libelle"], carte["domaine_teinte"]), ("", ""))

    def test_la_carte_compte_ses_seances(self):
        """Compté, jamais estimé : une carte qui ment sur la taille fait perdre son temps."""
        self.assertEqual(catalogue_public.seances_par_parcours([self.cours])[self.cours], 3)

    def test_un_parcours_sans_chapitre_compte_zero_seance(self):
        vide = frappe.get_doc({"doctype": "LMS Course", "title": "Parcours vide",
                               "short_introduction": "s", "description": "d"}
                              ).insert(ignore_permissions=True).name
        self.assertEqual(catalogue_public.seances_par_parcours([vide]), {vide: 0})

    def test_sans_parcours_rien_n_est_compte(self):
        self.assertEqual(catalogue_public.seances_par_parcours([]), {})

    def test_le_comptage_ne_melange_pas_deux_parcours(self):
        """Deux requêtes pour tout le catalogue : l'erreur guettée est d'attribuer à l'un les
        séances de l'autre."""
        autre = frappe.get_doc({"doctype": "LMS Course", "title": "Autre parcours",
                                "short_introduction": "s", "description": "d"}
                               ).insert(ignore_permissions=True).name
        chapitre = frappe.get_doc({"doctype": "Course Chapter", "title": "Bloc autre",
                                   "course": autre}).insert(ignore_permissions=True)
        frappe.get_doc({"doctype": "Course Lesson", "title": "Unique", "chapter": chapitre.name,
                        "course": autre, "content": ""}).insert(ignore_permissions=True)
        compte = catalogue_public.seances_par_parcours([self.cours, autre])
        self.assertEqual((compte[self.cours], compte[autre]), (3, 1))
