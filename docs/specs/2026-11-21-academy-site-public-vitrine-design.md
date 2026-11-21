# Le site public de l'académie : vitrine complète, inscriptions suspendues

*Conception — 21 novembre 2026*

## Intention

Le site public existe (accueil, catalogue, fiche d'un parcours) et il est structurellement
correct : contrastes AA, offre rendue au serveur, échappement systématique. Mais il n'est pas
désirable. Le reproche est net : « le site est trop nul ». Il faut qu'il ressemble aux meilleures
plateformes de formation tech et qu'un visiteur puisse atteindre l'inscription en trois clics.

Deux décisions produit s'ajoutent à la refonte visuelle :

1. **Les huit parcours s'affichent tous**, y compris ceux que la phase de lancement masque
   aujourd'hui. Un catalogue de huit entrées dont sept sont cachées se lit comme un catalogue
   d'une entrée.
2. **Aucune inscription n'est possible pour l'instant**, parce que la conception des parcours
   n'est pas terminée. Le site est une vitrine : il montre tout, il n'engage rien.

Et un parcours de plus à annoncer : **Rust**, parce que les géants de l'IA l'adoptent.

## Pourquoi maintenant

La façade vient d'être livrée (PR #61) et c'est en l'exerçant que son allure s'est révélée
insuffisante. Le moment est le bon : les gabarits sont jeunes, personne ne s'est encore inscrit
par le site, et suspendre les inscriptions supprime le risque pendant le chantier.

## Objectifs

- Un site dont l'allure soutient la comparaison avec Le Wagon ou Boot.dev, à notre échelle.
- Les huit — bientôt neuf — parcours visibles, chacun avec son état honnête.
- Aucune inscription possible, et ce refus tenu **au serveur**, pas par l'absence d'un bouton.
- La règle des trois clics tenue : accueil → catalogue → fiche, et la fiche porte l'action.
- Le parcours Rust annoncé : fiche et programme listés, sans contenu de séance.

## Non-objectifs

- Pas de refonte de l'espace apprenant ni de l'interface d'administration du LMS.
- Pas de recherche, pas de filtres à facettes : sous trente entrées, ils renvoient des
  sélections vides et mesurent publiquement la petitesse du catalogue.
- Pas d'avis, de notes, de logos d'entreprises ni de chiffres de masse : nous n'en avons pas, et
  « 4,9 (3 avis) » fait du tort.
- Pas d'aperçu vidéo, pas de page formateur : sans tournage, ces blocs sont des cadres vides.
- Pas de contenu de séance écrit pour Rust dans ce lot.

## Anti-objectifs

Ce qui rendrait ce lot un échec même s'il fonctionne :

- **Un bouton d'inscription qui disparaît du gabarit sans que le serveur refuse.** Le refus doit
  venir du domaine ; un bouton caché n'est pas une règle.
- **Un parcours dont le contenu de séance fuit** parce qu'on a ouvert la fiche à tous. La fiche
  ne livre que des titres ; le corps des séances reste réservé aux inscrits.
- **Une promesse fausse.** Un parcours annoncé « ouvert » qu'on ne peut pas rejoindre, ou un
  chiffre écrit à la main sur l'accueil.
- **Une dizaine de visuels à produire et à faire vieillir.** Si la nouvelle carte exige une image
  par parcours, elle sera vide la moitié du temps, comme aujourd'hui.

## Contraintes

- **La coquille Frappe.** Les trois pages héritent de `templates/web.html` : en-tête, navigation
  et pied de page viennent du LMS. C'est la première chose vue et une bonne part de l'effet
  « site générique ».
- **La charte est posée** dans `public/css/openlab.css` (`docs/charte-graphique.md`) : Montserrat
  pour les titres, Nunito Sans pour le texte, bleu nuit `#001e48` pour les actions, orange en
  accent, règle de contraste écrite en tête du fichier. On s'en sert, on ne la redéfinit pas.
- **Aucune catégorie dans les YAML de parcours.** Ils portent `tags` et `card_gradient`, pas de
  `category`. Les gabarits affichent déjà `p.category` — qui est donc souvent vide.
- **La mémoire du poste** ne supporte pas deux piles Docker, ni deux suites de tests.
- **Tests d'abord**, puis OWASP et architecture hexagonale, à chaque étape.

## Les façons de s'y prendre

**A — Peau et cartes.** Garder la coquille Frappe, refaire `site.css` et l'anatomie de la carte,
ajouter les sections de réassurance. Environ une journée, aucun risque pour l'espace apprenant.
Écartée : l'en-tête du LMS reste, et c'est précisément ce qu'on voit d'abord.

**B — Coquille propre et les trois pages refaites.** *Retenue, validée le 21 novembre 2026.*
Notre propre gabarit de base (en-tête, pied de page), puis les trois pages selon un gabarit court
— sept à dix blocs, pas vingt-quatre. Deux à trois journées.

**C — Plateforme complète** (aperçus vidéo, avis, pages formateur, recherche). Écartée : elle
demande exactement les actifs que nous n'avons pas, et chaque bloc vide se verrait.

## Ce qui est décidé

### 1. La visibilité : la vitrine remplace le masquage

Le site public cesse d'appliquer le masquage de la phase de lancement
(`cours_refuses_courants()`). Il liste tous les parcours publiés du catalogue, et la fiche de
chacun répond.

**`published` reste l'interrupteur, et c'est délibéré.** Le relever aussi aurait deux effets
qu'on ne veut pas : `lancement.retirer_parcours_echus` dépublie chaque nuit un parcours limité dont
la fenêtre s'est fermée — il reparaîtrait ; et tout brouillon commencé dans l'administration du
LMS deviendrait public à la seconde où il est créé. L'administration doit garder un moyen de
retirer une page du site ; c'est celui-là.

C'est **le renversement d'une décision documentée** : `site_api.parcours_publie` traitait un
parcours masqué comme inexistant, et son commentaire explique pourquoi (ne pas apprendre à un
visiteur qu'un parcours se prépare, ne pas laisser lire son prix ni ses dates). Cette précaution
protégeait un secret que nous ne voulons plus garder : l'existence et le programme des parcours à
venir sont désormais l'argument de vente. Le commentaire doit être réécrit, pas supprimé en
silence, pour que la prochaine lecture comprenne que c'est un choix et non un oubli.

Ce qui ne change pas, et que les tests doivent continuer d'exiger :

- le corps des séances n'est pas servi par la façade — la fiche n'affiche que des titres ;
- l'accès à `/lms/courses/<nom>` reste gouverné par les règles du LMS, inchangées ;
- le masquage de la phase de lancement continue de s'appliquer **dans le LMS**, pour l'apprenant
  connecté ; seule la façade publique s'en affranchit.

### 2. Les inscriptions : suspendues au domaine

Un nouvel état de domaine, dans `domain/inscription_ouverte.py` : la suspension. Elle précède
tous les autres motifs de refus, comme le retrait précède aujourd'hui la date et le remplissage.
Sa phrase est portée par l'énumération `Etat`, avec les autres, pour que le test puisse exiger
qu'aucun état n'en manque — par exemple : « Les inscriptions ouvriront bientôt. »

Elle est commandée par un réglage, pas par une constante : la rouvrir ne doit pas demander un
déploiement. Le réglage vit avec les autres réglages du parcours ou de l'académie, lu par un
adaptateur, le domaine n'en connaissant que la valeur.

Trois endroits s'alignent dessus, sans qu'aucun ne réimplémente la règle :

- `application/inscrire_au_parcours.py` refuse — c'est le seul chemin d'écriture ;
- `entrypoints/site_api.inscrire` remonte le refus en message lisible, **avant toute écriture** ;
- les gabarits affichent l'état au lieu d'un bouton actif.

Le test qui compte n'est pas celui du gabarit : c'est celui qui poste sur `inscrire` et exige un
refus. Un bouton absent n'est pas une règle.

**La suspension ne descend pas dans le crochet `LMS Enrollment`.** Elle ferme la façade publique,
pas le LMS. Le parcours pilote IA agentique est gratuit et tourne : un apprenant connecté continue
de le rejoindre depuis la page du LMS, et c'est voulu — l'arrêter reviendrait à interrompre une
promotion en cours pour un chantier d'allure. « Aucune inscription possible » s'entend donc du
site public, et la recette doit le formuler ainsi plutôt que « nulle part ».

Conséquence à écrire dans les tests, sans quoi la prochaine modification fermera les deux chemins
ou aucun : inscription publique refusée, inscription par le LMS et par l'administration acceptées.

### 3. L'état de chaque parcours, montré honnêtement

Trois états suffisent, et chacun dit la vérité :

| État | Quand | Ce que la carte et la fiche montrent |
|---|---|---|
| En préparation | parcours annoncé, contenu non écrit | pastille neutre, « En préparation » |
| Bientôt ouvert | contenu prêt, inscriptions suspendues | pastille d'attente |
| Accès libre | parcours gratuit déjà consultable | ce qui est accessible l'est |

Tant que la suspension est en vigueur, aucune carte ne porte « Inscriptions ouvertes ».

**Aucune date annoncée.** Les seules dates du système sont les fenêtres des cohortes publiées, et
seul le pilote en a une ; `ouverture_lancement` est une date globale, pas une date par parcours.
Une date par parcours serait une seconde donnée à ajouter aux YAML, hors de ce lot : tant qu'elle
n'existe pas, on n'en montre aucune plutôt qu'une inventée.

**Ce qu'une fiche en préparation révèle.** L'existence et le programme, oui — c'est l'argument de
vente. Le prix, seulement s'il est renseigné. Jamais les dates de cohorte ni les places
restantes : un parcours dont le contenu n'est pas écrit n'a pas de session à annoncer, et
`places_restantes` sur une cohorte qui n'accueille personne est une promesse fausse. `Offre` doit
donc taire ces champs dans cet état, et pas seulement le gabarit : l'API `offre` est ouverte aux
visiteurs.

### 3 bis. L'action principale, pendant la suspension

Le bouton principal **ne capture aucune adresse**. Pas de liste d'attente : ce serait le seul
chemin d'écriture ouvert aux visiteurs sur un site dont tout l'intérêt est qu'il n'écrit rien, et
il porterait consentement, anti-abus, confirmation et sa propre revue.

L'action est donc : la pastille d'état dit où en est le parcours, et le bouton mène au programme
(sur l'accueil et le catalogue : la fiche ; sur la fiche : un contact existant). La règle des trois
clics garde une destination — la fiche et son programme — sans rien promettre.

### 4. La carte : une couleur par domaine, pas une image

C'est le procédé relevé sur OpenClassrooms et il règle notre problème le plus visible. La carte
porte, de haut en bas :

1. un **aplat de couleur plein**, ratio ≈ 3:1 sur la largeur de la carte, teinte dépendant du
   domaine — pas d'image, pas de dégradé vide ;
2. l'**étiquette de domaine** en capitales, 0,78 rem, dans la même teinte ;
3. le **titre** ;
4. **une ligne** de résumé ;
5. en pied, un **badge typographique de durée** (« 18 séances », « ~54 h ») et l'état.

Ni note, ni nombre d'inscrits, ni prix sur la carte : rien qui se dégrade mal à notre échelle. Le
badge de durée fait le travail de repérage visuel que ferait une image, pour zéro actif graphique
— c'est ce que fait Le Wagon avec ses « 400 Hours ».

**Le domaine doit devenir une donnée.** Une clé `domaine:` dans les YAML de parcours, comme
`video:` l'a été, **portée sur `LMS Course.category`** — le champ existe, les gabarits le rendent
déjà, et il est aujourd'hui vide, ce qui explique une bonne part de la fadeur actuelle. Pas de
champ sur mesure, et pas de correctif de migration : la chaîne republie les parcours depuis les
YAML. `card_gradient` reste, c'est le champ du LMS pour ses propres écrans. Les teintes s'ajoutent à
`openlab.css` en variables (`--ol-domaine-data`, `--ol-domaine-ia`, …), dérivées de la charte et
vérifiées au contraste : texte blanc seulement sur une teinte assez sombre, la règle en tête
d'`openlab.css` s'applique sans exception.

### 5. Les trois pages

**Accueil** — un seul appel à l'action primaire, au plus un secondaire ; les chiffres restent
comptés, jamais écrits à la main ; les trois étapes de méthode gardées ; la grille des parcours ;
pas de recherche, pas de filtres.

**Catalogue** — pas de facettes. Les parcours rangés en lots annoncés en tête, comme Le Wagon
range « Bootcamps » et « Skill courses » : par exemple les parcours longs d'un côté, les parcours
courts et l'accès libre de l'autre. Le compteur de résultats disparaît : il mesure la petitesse.

**Fiche** — gabarit court, sept à dix blocs, dans cet ordre, parce que c'est l'ordre que suivent
les six plateformes relevées : fil d'Ariane, hero (titre, accroche, deux métadonnées, l'action),
« ce que vous saurez faire », prérequis, programme en modules et séances numérotées avec durée et
total, ce qui est fourni, questions fréquentes courtes, date de mise à jour en clair. L'encart
latéral reste collant et porte les métadonnées et l'état ; l'action principale est dans le hero.

### 6. La coquille propre

Un gabarit de base à nous pour les pages publiques : en-tête (logo, deux entrées, connexion),
pied de page sobre, le filet de la charte. Pas de mégamenu.

Les quatre routes qui basculent : `/` (accueil), `/parcours` (catalogue), `/parcours/<nom>`
(fiche) et `/parcours-ferme/<cours>`, qui est aussi une page publique. L'espace apprenant
(`espace.html`), l'atelier et l'administration gardent la coquille du LMS — un test doit le
constater plutôt que de l'espérer.

**`/login` reste la page de Frappe**, avec sa coquille : la remplacer toucherait
l'authentification, hors du périmètre de ce lot. Un visiteur qui clique « connexion » change donc
de décor. C'est un écart connu, assumé pour l'instant, à reprendre plus tard.

### 7. Le parcours Rust

Un neuvième YAML, `data/parcours/08-rust-...yaml`, avec titre, accroche, description, domaine,
et le programme en modules et séances **listés sans contenu**. Il s'affiche « En préparation ».

L'angle est celui qui justifie le parcours : Rust gagne l'infrastructure de l'IA — moteurs
d'inférence, chaînes de données, outillage. Le programme doit l'annoncer, pas réciter la syntaxe
du langage.

**La chaîne ne sait pas encore faire cela, et c'est le vrai morceau de ce lot.** Le code existant
offre deux formes et aucune ne convient : `statut: a_venir` donne une `Annonce`, qui ne porte que
titre, accroche, description, tags et dégradé — **aucun bloc** (`DepotFrappe.creer` la publie avec
`upcoming=1` et zéro chapitre) ; un `Parcours` complet, lui, exige un projet final et publierait de
vraies séances au corps vide.

Il faut donc une troisième forme : **une `Annonce` qui porte un programme de titres seuls** —
modules et séances nommés, sans corps, sans projet final. Le domaine, l'adaptateur et la chaîne de
publication changent ensemble. Ce n'est pas du travail en plus pour Rust seul : Cybersécurité I et
II sont déjà annoncés et n'affichent aujourd'hui aucun programme, et c'est précisément le cadre
vide que ce lot s'interdit. Les trois en profitent.

Le badge de durée suit la même règle : « 18 séances prévues » quand le programme est annoncé,
rien quand il n'y en a pas — jamais un badge vide.

### 8. Créer un compte apprenant depuis l'administration

Les tests utilisateurs en ont besoin, et la suspension des inscriptions publiques ne doit pas les
empêcher. Ce qui existe déjà : l'écran « Inscrits et gratuités » d'un parcours
(`entrypoints/gratuites.py`), réservé à l'administrateur et à l'intendant, qui offre un parcours à
une personne puis l'inscrit. Ce qui manque : **créer le compte lui-même**.

Frappe sait créer un utilisateur dans son interface d'administration, mais le compte né ainsi
attend un courriel de bienvenue pour choisir son mot de passe — et les comptes d'envoi de
production ne sont pas en service. Un compte d'essai doit donc naître utilisable immédiatement.

Un point d'entrée, dans le même module et sous les mêmes droits que `gratuites.inscrire` :

- il crée l'utilisateur, désactive le courriel de bienvenue, lui donne le rôle d'apprenant du LMS ;
- le mot de passe est fourni par l'administrateur, ou tiré au hasard et **rendu une seule fois**
  dans la réponse — jamais journalisé, jamais stocké ailleurs que dans le compte ;
- il est rejouable : sur un compte qui existe déjà, il le renvoie sans toucher à son mot de passe,
  parce qu'une réinitialisation silencieuse ferait perdre l'accès à quelqu'un ;
- les droits sont vérifiés dans le point d'entrée, comme partout ici : un appel direct à l'API
  passe par les mêmes contrôles.

**La suspension ne s'applique pas à ce chemin**, et c'est voulu : elle vit dans le cas d'usage
public `inscrire_au_parcours`, que l'administration n'emprunte pas. Un test doit le constater —
l'inscription publique refusée, l'inscription par l'administration acceptée — sinon la prochaine
modification fermera les deux ou aucune.

## Ce qui est laissé à celui qui construit

- Le nombre exact de teintes de domaine et leurs valeurs : à dériver de la charte, à vérifier au
  contraste, à proposer avant d'écrire les gabarits.
- La répartition des parcours en lots sur le catalogue, et leur intitulé.
- Le mécanisme de réglage de la suspension : réglage global de l'académie ou par parcours. Le
  global suffit au besoin exprimé ; le choix doit être dit.
- Le texte des questions fréquentes et des blocs de réassurance.
- Le découpage en séances du parcours Rust.
- L'ordre d'exécution : la suspension des inscriptions d'abord, parce qu'elle seule porte un
  risque ; la vitrine ensuite ; l'allure en dernier.

## Recette

Le build vert ne suffit pas. Avant de déclarer le lot fini : lancer la pile, exercer le site dans
le navigateur — les neuf parcours visibles ; aucune action d'inscription **sur le site public** ;
un POST direct sur `inscrire` refusé ; la fiche d'un parcours en préparation qui montre son
programme en titres et aucun corps de séance, sans date ni places restantes ; le pilote toujours
rejoignable depuis le LMS ; un compte apprenant créé depuis l'administration, qui se connecte ;
l'espace apprenant intact. À 375 px aussi.
