# Site public de l'académie — vitrine et refonte : plan d'implémentation

> **Pour un exécutant agentique :** utiliser `superpowers:executing-plans` (ou
> `superpowers:subagent-driven-development`) pour dérouler ce plan tâche par tâche. Les étapes sont
> des cases à cocher.

**But :** afficher les neuf parcours, suspendre toute inscription publique au serveur, pouvoir
créer un compte apprenant depuis l'administration, et refaire l'allure des trois pages publiques
sur un gabarit court.

**Architecture :** hexagonale, comme le reste de l'app. La suspension est une règle de domaine
(`domain/inscription_ouverte.Etat`), lue par le cas d'usage public via un port, commandée par un
réglage. La vitrine est un changement de filtre dans `entrypoints/site_api` et
`www/catalogue_public`. L'allure est du Jinja et du CSS qui consomment la charte.

**Pile :** Python 3.14, Frappe v15 + Frappe LMS, Jinja2, CSS natif (aucun framework), unittest.

**Conception :** `docs/specs/2026-11-21-academy-site-public-vitrine-design.md` — à lire avec ce plan.

## Contraintes globales

- Tests d'abord, à chaque tâche. Puis OWASP et architecture hexagonale.
- Une seule suite de tests à la fois ; jamais deux piles Docker. Module seul :
  `bash docker/dev-test.sh openlab_academy.tests.<module>`.
- Toute chaîne passée à `_()` doit avoir son anglais dans `translations/en.csv` — le garde-fou
  `test_traductions` échoue sinon, et la couverture cumulée tombe avec lui.
- Aucune couleur redéfinie : la charte vit dans `public/css/openlab.css`. Contraste AA, règle en
  tête de ce fichier — texte blanc seulement sur `#b35210` ou plus foncé.
- Les gabarits échappent toute valeur venant des données avec `| e` (l'autoéchappement de Frappe
  est désactivé).
- Aucune trace d'assistant : ni commit, ni code, ni nom de fichier.
- Couverture ≥ 99 %.

## Points de vigilance

Cinq classes d'entrées que la conception implique sans qu'aucune tâche ne les exerce d'elle-même.
Chaque ligne a son test, ajouté à la tâche qui possède le code.

1. **POST direct sur `site_api.inscrire` pendant la suspension** — doit refuser, même si aucun
   bouton n'est affiché. *Tâche 1.*
2. **Inscription par l'administration pendant la suspension** — doit aboutir, sinon les tests
   utilisateurs sont impossibles. *Tâche 1.*
3. **Fiche d'un parcours masqué par la phase de lancement** — doit répondre et n'afficher que des
   titres de séances, jamais un corps, ni date de cohorte, ni places restantes. Un parcours
   *dépublié*, lui, reste introuvable. *Tâche 2.*
4. **`creer_apprenant` rejoué sur un compte existant** — doit renvoyer le compte sans réinitialiser
   son mot de passe. *Tâche 3.*
5. **Parcours sans domaine renseigné** — la carte doit rester lisible, avec une teinte neutre, pas
   un attribut vide ni une classe CSS inexistante. *Tâche 4.*

---

### Tâche 1 : Suspension des inscriptions publiques

**Fichiers :**
- Modifier : `domain/inscription_ouverte.py`
- Modifier : `application/inscrire_au_parcours.py`
- Modifier : `infrastructure/inscriptions_frappe.py`
- Modifier : `infrastructure/reglages_frappe.py`, `domain/reglages.py`
- Modifier : `openlab_academy/doctype/reglages_openlab_academy/reglages_openlab_academy.json`
- Tests : `tests/test_inscriptions_ouvertes.py`, `tests/test_inscrire_au_parcours.py`,
  `tests/test_site_api.py` (créer s'il n'existe pas)

**Interfaces :**
- Produit : `Etat.SUSPENDUE`, de message « Les inscriptions ouvriront bientôt. » et `ouverte`
  faux ; `Reglages.inscriptions_suspendues() -> bool` au protocole de
  `application/inscrire_au_parcours.py` ; `ReglagesInscriptionFrappe.inscriptions_suspendues()`
  qui lit le champ `inscriptions_suspendues` des réglages.
- Consomme : rien.

- [ ] **Étape 1 : écrire les tests qui échouent**

```python
# tests/test_inscriptions_ouvertes.py
def test_l_etat_suspendu_n_est_pas_ouvert(self):
    self.assertFalse(Etat.SUSPENDUE.ouverte)
    self.assertEqual(Etat.SUSPENDUE.message, "Les inscriptions ouvriront bientôt.")

def test_tout_etat_porte_une_phrase(self):
    for etat in Etat:
        self.assertTrue(etat.message.strip())

# tests/test_inscrire_au_parcours.py — réglages suspendus, cohorte ouverte par ailleurs
def test_l_offre_annonce_la_suspension(self):
    offre = self.usage(suspendues=True).offre("cours", "")
    self.assertEqual(offre.etat, Etat.SUSPENDUE)
    self.assertFalse(offre.en_dict()["ouverte"])

def test_la_suspension_refuse_l_inscription(self):
    with self.assertRaises(InscriptionImpossible) as refus:
        self.usage(suspendues=True).executer("cours", "awa@example.com")
    self.assertIn("ouvriront bientôt", str(refus.exception))

def test_la_suspension_precede_la_gratuite(self):
    """Un parcours gratuit est ouvert sans cohorte ni tarif : la suspension doit passer avant."""
    self.assertEqual(self.usage(suspendues=True, gratuit=True).offre("cours", "").etat, Etat.SUSPENDUE)

def test_un_deja_inscrit_garde_son_acces(self):
    """La suspension ferme la porte d'entrée, elle ne met personne dehors."""
    destination = self.usage(suspendues=True, deja_inscrit=True).executer("cours", "awa@example.com")
    self.assertIn("cours", destination)
```

Et les deux points de vigilance 1 et 2, en test d'intégration Frappe :

```python
# tests/test_site_api.py
def test_un_post_direct_est_refuse_pendant_la_suspension(self):
    """Aucun bouton n'est affiché, mais c'est le serveur qui refuse."""
    with self.assertRaises(frappe.ValidationError):
        site_api.inscrire(self.cours)

def test_l_administration_inscrit_malgre_la_suspension(self):
    gratuites.basculer(self.cours, self.apprenant, 1)
    gratuites.inscrire(self.cours, self.apprenant)
    self.assertTrue(frappe.db.exists("LMS Enrollment", {"course": self.cours, "member": self.apprenant}))

def test_le_pilote_gratuit_reste_rejoignable_par_le_lms(self):
    """La suspension ferme la façade, pas le LMS : une promotion en cours ne s'interrompt pas
    pour un chantier d'allure. Le crochet `LMS Enrollment` n'est pas touché."""
    frappe.get_doc({"doctype": "LMS Enrollment", "course": self.cours_gratuit,
                    "member": self.apprenant}).insert(ignore_permissions=True)
    self.assertTrue(frappe.db.exists("LMS Enrollment",
                                     {"course": self.cours_gratuit, "member": self.apprenant}))
```

- [ ] **Étape 2 : lancer les tests, vérifier qu'ils échouent**

`bash docker/dev-test.sh openlab_academy.tests.test_inscriptions_ouvertes`
Attendu : ÉCHEC sur `Etat.SUSPENDUE` inexistant.

- [ ] **Étape 3 : ajouter `SUSPENDUE` à `Etat`**

Première valeur de l'énumération, avant `OUVERTE`, pour que l'ordre de lecture dise la priorité.
Elle n'entre pas dans `etat_de` ni `etat_du_parcours` : une cohorte n'est pas suspendue, c'est
l'académie qui l'est. Le rang de `etat_du_parcours` reste inchangé.

- [ ] **Étape 4 : ajouter `inscriptions_suspendues()` au protocole `Reglages` et le refus dans `_examiner`**

Dans `application/inscrire_au_parcours.py`, premier test de `_examiner`, avant la gratuité :
`if self._reglages.inscriptions_suspendues(): return Etat.SUSPENDUE, None, False, None`.
C'est le point unique déjà partagé par `offre` et `executer` — ne pas écrire un second contrôle
dans `executer`.

- [ ] **Étape 5 : le réglage et son adaptateur**

Champ `Check` `inscriptions_suspendues`, intitulé « Inscriptions suspendues », dans la section
« Lancement » du doctype `Reglages OpenLab Academy`, après `phase_lancement`. Le porter sur
l'objet de `domain/reglages.py` et dans `reglages_frappe.py`, comme
`inscription_tardive_mois`. Valeur par défaut : coché (`default: "1"`) — l'état voulu aujourd'hui
est « suspendu », et un déploiement ne doit pas ouvrir les inscriptions par inadvertance.

- [ ] **Étape 6 : lancer les trois modules, vérifier qu'ils passent**

`bash docker/dev-test.sh openlab_academy.tests.test_inscriptions_ouvertes` puis
`...test_inscrire_au_parcours` puis `...test_site_api`. Attendu : `Ran … OK` à chaque fois.

- [ ] **Étape 7 : commit**

```bash
git add apps/openlab_academy/openlab_academy/{domain,application,infrastructure,openlab_academy/doctype}/ apps/openlab_academy/openlab_academy/tests/
git commit -m "feat(academy): les inscriptions publiques se suspendent au domaine"
```

---

### Tâche 2 : La vitrine — les neuf parcours visibles

**Fichiers :**
- Modifier : `entrypoints/site_api.py` (`parcours_publie`)
- Modifier : `www/catalogue_public.py` (`parcours_visibles`)
- Modifier : `www/parcours_public.py` (le `DoesNotExistError`)
- Tests : `tests/test_catalogue_public.py` (créer s'il n'existe pas), `tests/test_site_api.py`

**Interfaces :**
- Produit : `site_api.parcours_du_catalogue(nom) -> str` remplace `parcours_publie` ; elle rend le
  nom si le parcours existe **et est publié**, sans appliquer `cours_refuses_courants()`.
  `catalogue_public.parcours_visibles(limite=None)` rend tous les parcours publiés.
  `Offre.en_dict()` tait `session`, `debut`, `fin` et `places_restantes` quand l'état n'est pas
  ouvert.
- Consomme : `Etat.SUSPENDUE` (tâche 1).

- [ ] **Étape 1 : écrire les tests qui échouent**

```python
# tests/test_catalogue_public.py
def test_un_parcours_masque_par_la_phase_de_lancement_est_au_catalogue(self):
    noms = [p.name for p in catalogue_public.parcours_visibles()]
    self.assertIn(self.cours_masque, noms)

def test_un_parcours_depublie_reste_hors_du_catalogue(self):
    """`published` reste l'interrupteur : `retirer_parcours_echus` dépublie chaque nuit, et un
    brouillon d'administration ne doit pas devenir public en naissant."""
    noms = [p.name for p in catalogue_public.parcours_visibles()]
    self.assertNotIn(self.cours_depublie, noms)

# tests/test_site_api.py — point de vigilance 3
def test_la_fiche_d_un_parcours_masque_repond(self):
    self.assertEqual(site_api.parcours_du_catalogue(self.cours_masque), self.cours_masque)

def test_une_fiche_non_ouverte_ne_livre_ni_date_ni_places(self):
    offre = site_api.offre(self.cours_masque)
    self.assertEqual(offre["session"], "")
    self.assertEqual(offre["places_restantes"], 0)

def test_la_fiche_ne_livre_aucun_corps_de_seance(self):
    """Elle montre des titres. Le contenu reste aux inscrits."""
    contexte = self.contexte_fiche(self.cours_non_publie)
    rendu = str(contexte.programme)
    self.assertIn(self.titre_seance, rendu)
    self.assertNotIn(self.corps_seance, rendu)

def test_un_parcours_inconnu_reste_introuvable(self):
    self.assertEqual(site_api.parcours_du_catalogue("nexiste-pas"), "")
```

- [ ] **Étape 2 : lancer, vérifier l'échec**

`bash docker/dev-test.sh openlab_academy.tests.test_catalogue_public` — ÉCHEC : le parcours masqué
est absent.

- [ ] **Étape 3 : ouvrir la façade**

`parcours_du_catalogue(nom)` garde `published` et laisse tomber
`lms.cours_refuses_courants()`. `parcours_visibles` fait de même. `Offre.en_dict()` tait session,
dates et places quand `etat.ouverte` est faux — c'est l'API qui doit les taire, pas le gabarit :
`offre` est ouverte aux visiteurs.

**Réécrire les deux docstrings**, qui expliquent aujourd'hui l'inverse : dire que l'existence et le
programme des parcours à venir sont devenus l'argument de vente, que c'est une décision et non un
oubli, et ce qui reste fermé (le corps des séances, l'accès à `/lms/courses/<nom>`, le masquage
dans le LMS pour l'apprenant connecté).

- [ ] **Étape 4 : lancer les deux modules, vérifier qu'ils passent**

- [ ] **Étape 5 : commit**

```bash
git commit -m "feat(academy): la facade publique montre tout le catalogue"
```

---

### Tâche 3 : Créer un compte apprenant depuis l'administration

**Fichiers :**
- Modifier : `entrypoints/gratuites.py`
- Tests : `tests/test_gratuites.py`

**Interfaces :**
- Produit : `gratuites.creer_apprenant(email: str, nom: str, prenom: str = "", mot_de_passe: str = "")
  -> dict`, rendant `{"apprenant": <email>, "cree": bool, "mot_de_passe": <chaîne ou "">}`.
- Consomme : `_exiger_le_droit()` du même module.

- [ ] **Étape 1 : écrire les tests qui échouent**

```python
def test_le_compte_nait_utilisable_sans_courriel(self):
    reponse = gratuites.creer_apprenant("essai1@example.com", "Essai")
    self.assertTrue(reponse["cree"])
    self.assertTrue(frappe.db.get_value("User", "essai1@example.com", "enabled"))
    self.assertIn("LMS Student", frappe.get_roles("essai1@example.com"))

def test_le_mot_de_passe_tire_est_rendu_une_fois(self):
    reponse = gratuites.creer_apprenant("essai2@example.com", "Essai")
    self.assertGreaterEqual(len(reponse["mot_de_passe"]), 12)

def test_rejoue_il_ne_reinitialise_rien(self):  # point de vigilance 4
    gratuites.creer_apprenant("essai3@example.com", "Essai", mot_de_passe="motdepasse-essai-1")
    reponse = gratuites.creer_apprenant("essai3@example.com", "Essai")
    self.assertFalse(reponse["cree"])
    self.assertEqual(reponse["mot_de_passe"], "")

def test_il_est_reserve_a_l_administrateur_et_a_l_intendant(self):
    frappe.set_user(self.apprenant)
    with self.assertRaises(frappe.PermissionError):
        gratuites.creer_apprenant("essai4@example.com", "Essai")
```

- [ ] **Étape 2 : lancer, vérifier l'échec**

- [ ] **Étape 3 : implémenter `creer_apprenant`**

`_exiger_le_droit()` d'abord. Si l'utilisateur existe, renvoyer `{"cree": False,
"mot_de_passe": ""}` sans rien toucher. Sinon : `frappe.get_doc({"doctype": "User", ...})`,
`flags.no_welcome_mail = True` avant l'insertion, rôle `LMS Student`, puis
`frappe.utils.password.update_password` avec le mot de passe fourni ou un
`frappe.generate_hash(length=16)`. Le mot de passe n'est renvoyé que lorsqu'il a été tiré, et
**jamais journalisé**.

- [ ] **Étape 4 : lancer, vérifier que ça passe**

- [ ] **Étape 5 : exposer l'action dans l'écran « Inscrits et gratuités »**

Un bouton « Créer un compte apprenant » qui demande courriel et nom, affiche le mot de passe une
fois, puis rafraîchit la liste. Pas de nouvelle page.

- [ ] **Étape 6 : commit**

```bash
git commit -m "feat(academy): un compte apprenant se cree depuis l'administration"
```

---

### Tâche 4 : Le domaine d'un parcours comme donnée, et ses teintes

**Fichiers :**
- Modifier : `infrastructure/yaml_source.py`, `domain/parcours.py`
- Modifier : les neuf `data/parcours/*.yaml` (clé `domaine:`)
- Modifier : `public/css/openlab.css` (variables de teinte), `docs/charte-graphique.md`
- Tests : `tests/test_yaml_source.py`

**Interfaces :**
- Produit : clé `domaine:` lue par `yaml_source`, portée sur le parcours ; variables CSS
  `--ol-domaine-<clef>` et `--ol-domaine-neutre`.

- [ ] **Étape 1 : écrire les tests qui échouent**

```python
def test_le_domaine_est_lu_du_yaml(self):
    self.assertEqual(self.parcours("06-ia-agentique").domaine, "ia")

def test_un_parcours_sans_domaine_vaut_neutre(self):  # point de vigilance 5
    self.assertEqual(self.parcours_sans_domaine().domaine, "neutre")

def test_un_domaine_inconnu_est_refuse_a_la_lecture(self):
    """Mieux vaut un échec de publication qu'une carte sans couleur en production."""
    with self.assertRaises(ValueError):
        self.lire_domaine("marketing-lunaire")
```

- [ ] **Étape 2 : lancer, vérifier l'échec**

- [ ] **Étape 3 : porter `domaine` du YAML sur `LMS Course.category`**

Liste fermée de clés, déclarée à un seul endroit. Le champ `category` existe et les gabarits le
rendent déjà : pas de champ sur mesure, pas de correctif de migration — la chaîne republie depuis
les YAML. `card_gradient` reste. Proposer les teintes **avant** d'écrire les gabarits : les dériver
de la charte, vérifier chaque contraste, et ne mettre du texte blanc que sur une teinte assez
sombre.

- [ ] **Étape 4 : renseigner `domaine:` dans les neuf YAML**

- [ ] **Étape 5 : lancer, vérifier que ça passe, puis commit**

```bash
git commit -m "feat(academy): chaque parcours porte son domaine"
```

---

### Tâche 5 : La coquille propre des pages publiques

**Fichiers :**
- Créer : `templates/site_public.html` (gabarit de base), `public/css/site.css` (en-tête, pied)
- Modifier : `www/accueil.html`, `www/parcours.html`, `www/parcours-public.html` (changement
  d'`extends`)
- Tests : `tests/test_pages_publiques.py` (créer)

**Interfaces :**
- Produit : `templates/site_public.html`, étendu par les trois pages publiques.

- [ ] **Étape 1 : écrire les tests qui échouent**

```python
def test_les_trois_pages_publiques_etendent_la_coquille_propre(self):
    for page in ("accueil.html", "parcours.html", "parcours-public.html"):
        self.assertIn("templates/site_public.html", self.source(page))

def test_l_espace_apprenant_garde_la_coquille_du_lms(self):
    """La bascule ne concerne que les pages publiques."""
    self.assertIn("templates/web.html", self.source("espace.html"))
```

- [ ] **Étape 2 : lancer, vérifier l'échec**

- [ ] **Étape 3 : écrire la coquille**

En-tête : logo, deux entrées (Parcours, Comment ça marche), connexion. Pied sobre, filet de la
charte. Pas de mégamenu, pas de recherche.

- [ ] **Étape 4 : lancer, vérifier que ça passe, puis commit**

---

### Tâche 6 : Les trois pages refaites

**Fichiers :**
- Modifier : `www/accueil.html`, `www/parcours.html`, `www/parcours-public.html`,
  `public/css/site.css`
- Modifier : `www/accueil.py`, `www/catalogue_public.py` (les lots du catalogue)
- Tests : `tests/test_pages_publiques.py`

- [ ] **Étape 1 : écrire les tests qui échouent**

```python
def test_aucune_page_n_annonce_des_inscriptions_ouvertes_pendant_la_suspension(self):
    for page in self.pages_rendues():
        self.assertNotIn("Inscriptions ouvertes", page)

def test_la_carte_porte_la_teinte_de_son_domaine(self):
    self.assertIn("ol-carte--ia", self.rendu_catalogue())

def test_le_catalogue_range_les_parcours_en_lots(self):
    rendu = self.rendu_catalogue()
    self.assertNotIn('data-role="filtres"', rendu)  # plus de facettes
    self.assertIn("ol-lot", rendu)

def test_aucune_page_ne_capture_d_adresse(self):
    """Pas de liste d'attente : la façade n'écrit rien."""
    for page in self.pages_rendues():
        self.assertNotIn("<form", page)

def test_le_badge_de_duree_est_absent_plutot_que_vide(self):
    self.assertNotIn('class="ol-duree"></span>', self.rendu_catalogue())
```

- [ ] **Étape 2 : lancer, vérifier l'échec**

- [ ] **Étape 3 : refaire les gabarits**

Carte : aplat de domaine, étiquette de domaine, titre, une ligne, badge de durée (« 18 séances
prévues » quand le programme est annoncé, rien sinon) et pastille d'état. Accueil : une action
primaire — qui mène au catalogue, pas à une inscription —, chiffres comptés, méthode, grille.
Catalogue : lots annoncés, aucun compteur de résultats, aucune facette. Fiche : fil d'Ariane, hero
(titre, accroche, deux métadonnées, l'action — le programme ou un contact existant), ce que vous
saurez faire, prérequis, programme numéroté, ce qui est fourni, questions fréquentes courtes, date
de mise à jour. Encart latéral collant : métadonnées et état seulement, ni date de cohorte ni
places restantes tant que l'état n'est pas ouvert.

- [ ] **Étape 4 : ajouter l'anglais des chaînes nouvelles à `translations/en.csv`**

Puis `bash docker/dev-test.sh openlab_academy.tests.test_traductions`.

- [ ] **Étape 5 : lancer les deux modules, vérifier qu'ils passent, puis commit**

---

### Tâche 7 : Une annonce qui porte son programme

C'est le vrai morceau du lot. Aujourd'hui `statut: a_venir` donne une `Annonce` sans aucun bloc
(`DepotFrappe.creer` publie `upcoming=1`, zéro chapitre), et un `Parcours` complet exigerait un
projet final et publierait des séances au corps vide. Il faut une troisième forme. Cybersécurité I
et II en profitent : annoncés, ils n'affichent aucun programme aujourd'hui.

**Fichiers :**
- Modifier : `domain/parcours.py` (`Annonce`), `infrastructure/yaml_source.py`,
  `infrastructure/depot_frappe.py`
- Tests : `tests/test_annonce.py`, `tests/test_yaml_source.py`

**Interfaces :**
- Produit : `Annonce.programme: tuple[ModuleAnnonce, ...]`, chaque `ModuleAnnonce` portant
  `titre: str` et `seances: tuple[str, ...]` — des titres, rien d'autre : pas de corps, pas de
  durée, pas de projet final.

- [ ] **Étape 1 : écrire les tests qui échouent**

```python
# tests/test_annonce.py
def test_une_annonce_peut_porter_un_programme_de_titres(self):
    annonce = self.annonce(programme=[{"titre": "Les bases", "seances": ["Installer la chaîne"]}])
    self.assertEqual(annonce.programme[0].seances, ("Installer la chaîne",))

def test_une_annonce_sans_programme_reste_valide(self):
    """Les annonces existantes n'en ont pas : le champ est facultatif."""
    self.assertEqual(self.annonce().programme, ())

def test_une_seance_annoncee_ne_porte_aucun_corps(self):
    """Si un corps se glisse dans le YAML, la lecture le refuse plutôt que de publier du vide."""
    with self.assertRaises(ValueError):
        self.lire_annonce_avec_corps_de_seance()

def test_le_cours_a_venir_est_publie_avec_ses_chapitres_et_sans_contenu(self):
    self.depot.creer(self.annonce_avec_programme())
    chapitres = frappe.get_all("Chapter Reference", {"parent": self.cours}, pluck="chapter")
    self.assertTrue(chapitres)
    lecons = frappe.get_all("Course Lesson", {"chapter": ["in", chapitres]}, ["title", "content"])
    self.assertTrue(all(not l.content for l in lecons))
```

- [ ] **Étape 2 : lancer, vérifier l'échec**

`bash docker/dev-test.sh openlab_academy.tests.test_annonce`

- [ ] **Étape 3 : porter le programme sur `Annonce`, de la lecture à la publication**

`domain/parcours.py` : `ModuleAnnonce` et le champ facultatif sur `Annonce`, avec la vérification
qu'aucune séance annoncée ne porte de corps. `yaml_source` lit la clé. `depot_frappe.creer` crée
les chapitres et les séances sans contenu, en gardant `upcoming=1`.

- [ ] **Étape 4 : lancer les deux modules, vérifier qu'ils passent, puis commit**

```bash
git commit -m "feat(academy): un parcours annonce montre son programme"
```

---

### Tâche 8 : Le parcours Rust

**Fichiers :**
- Créer : `data/parcours/08-rust-pour-l-ia.yaml`
- Tests : `tests/test_yaml_source.py`

**Interfaces :**
- Consomme : `Annonce.programme` (tâche 7), la clé `domaine:` (tâche 4).

- [ ] **Étape 1 : écrire le test qui échoue**

```python
def test_le_parcours_rust_est_annonce_avec_son_programme(self):
    annonce = self.lire("08-rust-pour-l-ia")
    self.assertEqual(annonce.domaine, "systeme")
    self.assertGreaterEqual(len(annonce.programme), 6)
```

- [ ] **Étape 2 : lancer, vérifier l'échec**

- [ ] **Étape 3 : écrire le YAML**

`statut: a_venir`, titre, accroche, description, `domaine: systeme`, et le programme en modules et
séances nommés. L'angle : Rust gagne l'infrastructure de l'IA — moteurs d'inférence, chaînes de
données, outillage — pas une récitation de la syntaxe du langage.

- [ ] **Étape 4 : lancer, vérifier que ça passe, puis commit**

---

### Tâche 9 : Recette et publication

- [ ] **Étape 1 : la suite complète**

`bash docker/dev-test.sh` seul, rien d'autre ouvert. Lire la ligne `Ran … OK` et le rapport de
couverture.

- [ ] **Étape 2 : exercer le site dans le navigateur**

Les neuf parcours visibles ; aucune action d'inscription **sur le site public** ; un POST direct
sur `inscrire` refusé ; la fiche d'un parcours en préparation qui montre son programme en titres,
sans corps de séance, sans date ni places restantes ; le pilote toujours rejoignable depuis le
LMS ; un compte apprenant créé depuis l'administration, qui se connecte ; l'espace apprenant
intact. À 375 px aussi.

- [ ] **Étape 3 : publier**

`/publier` : push, PR vers `develop`, puis `gh pr checks <n> --watch` jusqu'au verdict des quatre
contrôles. Ne rien déclarer de vert sans le verdict lu.
