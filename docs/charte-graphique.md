# OpenLab Academy — charte graphique

Édition du 24 octobre 2026. Référence : logo officiel corrigé (`docs/logo.jfif`). OpenLab Academy est la division
Formation d'OpenLab Consulting (www.openlabconsulting.com).

Les fichiers du logo sont dans `docs/charte/logo/`. Ils sont générés par `docs/charte/generer_charte.py`, qui
contient un redessin vectoriel du logo officiel et la police Montserrat convertie en tracés : aucun fichier ne dépend
d'une police installée. Pour modifier le logo, on modifie le script et on le relance ; on ne retouche jamais un
fichier généré à la main. La planche visuelle de la charte : `docs/charte/index.html`.

## 1. Logo

### Composition

- **Pictogramme** : un livre ouvert, page gauche bleu royal et page droite orange, gravées de pistes de circuit
  imprimé (le savoir et la technologie). Deux feuillets bleu ciel s'envolent de chaque page, et un anneau jaune
  enlace le livre (le mouvement, la réussite).
- **Logotype** : « OPENLAB » en capitales grasses bleu nuit, « ACADEMY » en capitales orange très espacées, et la
  signature « DIVISION FORMATION – OPENLAB CONSULTING » en graphite.

### Déclinaisons

| Version | Fichier (`docs/charte/logo/`) | Usage |
|---|---|---|
| Complète | `openlab-academy-couleur.svg` | documents officiels, attestations, présentations, site vitrine |
| Sans signature | `openlab-academy-court-couleur.svg` | supports où OpenLab Consulting est déjà nommé |
| Compacte | `openlab-academy-compact-couleur.svg` | en-têtes d'application, e-mails, bannières étroites (pictogramme à la hauteur du texte) |
| Pictogramme | `pictogramme-couleur.svg` | favicon, avatar, réseaux sociaux, application mobile |
| Réserve | `*-reserve.svg` (et `*-reserve-sur-fond.svg`) | sur fond bleu nuit : textes en blanc, pictogramme en couleur |
| Monochrome bleu nuit | `*-mono-nuit.svg` | impression une couleur, tampon, fax, gravure sur fond clair |
| Monochrome blanc | `*-mono-blanc.svg` | sérigraphie, broderie, gravure sur fond foncé |

Formats prêts à l'emploi (`png/`, fond transparent) : complète en 480, 960 et 1920 px ; sans signature et compacte
en 460 et 920 px ; pictogramme en 64, 192, 512 et 1024 px. Icônes : `favicon.ico` (16 à 64 px),
`apple-touch-icon.png` (180 px, fond blanc), `vignette-partage.png` (1200 × 630, partage sur les réseaux sociaux).

### Règles d'usage

- **Zone de protection** : autour du logo, garder un espace libre égal à la hauteur du « O » d'OPENLAB (la moitié
  pour la version compacte).
- **Taille minimale** : complète 200 px (50 mm à l'impression), compacte 140 px (35 mm), pictogramme 24 px
  (8 mm). En dessous, passer à la version plus simple : la signature cesse d'être lisible sous 200 px.
- **Fonds** : blanc, ivoire ou brume pour la version couleur ; bleu nuit pour la réserve. Sur une photo, poser le
  logo dans un cartouche blanc ou bleu nuit.
- **Interdits** : déformer, incliner, changer une couleur, ajouter une ombre ou un contour, recomposer le logotype
  dans une autre police, isoler « ACADEMY », poser la version couleur sur un fond orange, jaune ou chargé.

## 2. Couleurs

| Rôle | Nom | Hex | RVB | Usage |
|---|---|---|---|---|
| Principale | Bleu nuit | `#001E48` | 0 30 72 | titres, logotype, bandeaux, pied de page |
| Principale | Orange Academy | `#EC7623` | 236 118 35 | appels à l'action, accents, « ACADEMY » |
| Secondaire | Bleu royal | `#244498` | 36 68 152 | page gauche du livre, liens, éléments interactifs, graphiques |
| Secondaire | Bleu ciel | `#2890C8` | 40 144 200 | feuillets du livre, informations, survols, illustrations |
| Accent | Jaune soleil | `#FCD80F` | 252 216 15 | anneau du logo, badges, réussite (jamais en texte sur blanc) |
| Neutre | Ivoire | `#FAF8F5` | 250 248 245 | fonds de section |
| Neutre | Brume | `#EEF1F6` | 238 241 246 | fonds d'application, séparateurs |
| Neutre | Graphite | `#1A1D24` | 26 29 36 | texte courant, signature du logo |
| Neutre | Gris ardoise | `#6B7590` | 107 117 144 | texte secondaire |
| Interface | Nuit profonde | `#00132E` | 0 19 46 | fond du thème sombre |

**Proportions conseillées** : 60 % de neutres, 25 % de bleu nuit, 10 % d'orange, 5 % de bleus et de jaune.

**Contrastes (WCAG 2.2 AA)**
- Orange `#EC7623` sur blanc : 2,9:1. Réservé aux accents, filets, bordures, et au texte sur bleu nuit.
- Texte blanc sur un bouton orange : utiliser l'orange foncé `#B35210` (5,1:1), et `#9F490E` au survol.
- Texte orange sur blanc : `#C25A12` (4,4:1), en gros texte seulement (18,66 px gras ou plus).
- Bleu nuit sur blanc : 16,4:1 ; bleu royal : 8,9:1 ; gris ardoise : 4,6:1 (texte secondaire, 14 px minimum).

Ces valeurs sont les jetons CSS de la plateforme (`--ol-navy`, `--ol-orange`, `--ol-navy-soft`, `--ol-sky`,
`--ol-sun`, `--ol-ivory`, `--ol-mist`, `--ol-graphite`, `--ol-slate`, `--ol-night`, `--ol-orange-deep`,
`--ol-orange-dark`), définis dans `openlab_academy/public/css/openlab.css`.

## 3. Typographie

- **Montserrat** (Google Fonts, licence SIL Open Font License), la police du logotype : titres en SemiBold (Bold
  pour les grands montants), surtitres en capitales espacées (SemiBold, interlettrage de 0,12 em).
- **Nunito Sans** (Google Fonts, licence SIL Open Font License) pour le texte courant, en Regular ou SemiBold :
  humaniste, plus douce et plus compacte que Montserrat, qui fatiguait à la lecture en continu (retour du 25/10/2026).
- **JetBrains Mono** pour le code.
- Polices de repli : `'Segoe UI', system-ui, Helvetica, Arial, sans-serif` (obligatoires dans les e-mails).
- Échelle conseillée : 12, 14, 16 (texte), 20, 24, 32, 40 px, avec une interligne de 1,5 pour le texte et de 1,2
  pour les titres.

## 4. Éléments graphiques

- **Filet quatre couleurs** repris du logo (bleu royal, bleu ciel, orange, jaune), en séparateur sous les en-têtes
  et en jauge de progression.
- **Motif de circuit imprimé** (les pistes et pastilles des pages du livre), en filigrane fin sur les bandeaux bleu
  nuit, à 6–10 % d'opacité.
- **Formes** : coins arrondis de 12 à 16 px, boutons en pilule, ombres douces bleutées
  (`0 2px 8px rgba(0, 30, 72, .08)`).
- **Icônes** : trait de 1,75 px, extrémités arrondies, une seule couleur (bleu nuit ou orange), jamais en couleurs
  multiples.
- **Photographie** : apprenants et formateurs réels, en Côte d'Ivoire et en Afrique de l'Ouest, lumière naturelle,
  écrans et code lisibles. Pas de banque d'images générique.

## 5. Applications

| Support | Règle |
|---|---|
| Plateforme (`/espace`, LMS) | en-tête blanc avec le logo compact (`images/logo-horizontal.svg`) et le filet quatre couleurs dessous ; favicon : pictogramme (`images/logo.svg`) |
| E-mails | logo compact en PNG intégré au message (`images/logo-email.png`, 460 px affiché à 230 px), bouton orange foncé `#B35210`, polices de repli |
| Attestations et certificats | logo complet en haut, fond ivoire, filet quatre couleurs en pied de page |
| Réseaux sociaux | avatar : pictogramme sur fond blanc ; partage : `vignette-partage.png` |
| Présentations | page de titre bleu nuit avec le logo en réserve ; pages intérieures blanches avec le logo compact en pied de page |
| Objets, textile | monochrome blanc sur bleu nuit, ou monochrome bleu nuit sur blanc |

## 6. Ton

Professionnel, chaleureux, concret. On parle de compétences et de livrables, jamais de promesses de salaire. On
vouvoie l'apprenant, et on écrit en français clair, sans jargon inutile.
