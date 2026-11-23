/**
 * La charte de l'academie, reprise de assets/css/openlab.css.
 *
 * Elle y est ecrite en variables CSS, que Remotion ne lit pas : la video est rendue hors du site. Les
 * valeurs sont donc recopiees ici, et `tests/test_montage.py` les confronte au fichier de l'application —
 * un habillage qui derive de la charte se voit tout de suite a l'ecran, mais pas dans une chaine verte.
 */
export const COULEURS = {
  orange: '#ec7623',
  orangeClair: '#f39a5b',
  marine: '#001e48',
  marineDouce: '#244498',
  ciel: '#2890c8',
  soleil: '#fcd80f',
  nuit: '#00132e',
  ivoire: '#faf8f5',
} as const;

export const TITRAGE = '"Montserrat", "Segoe UI", system-ui, sans-serif';
export const TEXTE = '"Nunito Sans", "Segoe UI", system-ui, sans-serif';

/** Le filet de l'academie : quatre bandes, dans cet ordre et ces proportions. */
export const FILET = `linear-gradient(90deg, ${COULEURS.marineDouce} 0 34%, ${COULEURS.ciel} 34% 50%, ${COULEURS.orange} 50% 84%, ${COULEURS.soleil} 84% 100%)`;

/** 1080 est la hauteur de reference des regles de lisibilite ; tout se met a l'echelle depuis elle. */
export const HAUTEUR_REFERENCE = 1080;

export const echelle = (hauteur: number) => hauteur / HAUTEUR_REFERENCE;
