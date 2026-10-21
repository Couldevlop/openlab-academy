// Grille d'évaluation et calcul de la note, identique au domaine Python (Grille.note) : somme pondérée des niveaux,
// arrondie au demi-point le plus proche, demi-pas au supérieur (10,25 -> 10,5).

export interface Niveau {
  libelle: string
  descripteur: string
  points: number
}

export interface Critere {
  code: string
  libelle: string
  description: string
  poids: number
  niveaux: Niveau[]
  controles: string[]
}

export interface Grille {
  criteres: Critere[]
}

/** Niveau choisi par code de critère : indice dans `Critere.niveaux`. */
export type Niveaux = Record<string, number>

export const PAS_NOTE = 0.5

const EPSILON_ARRONDI = 1e-9 // bruit des flottants : 20,4999999999 vaut 20,5, 20,499999998 non

/** Demi-pas arrondi au supérieur (10,25 -> 10,5), même formule que le domaine Python. */
function arrondiAuPas(note: number): number {
  return Math.floor(note / PAS_NOTE + 0.5 + EPSILON_ARRONDI) * PAS_NOTE
}

function niveauChoisi(critere: Critere, niveaux: Niveaux): Niveau | undefined {
  const i = niveaux[critere.code]
  return i === undefined || !Number.isInteger(i) ? undefined : critere.niveaux[i]
}

/** Note sur `noteSur`, ou null tant qu'un critère n'a pas de niveau valide. */
export function calculerNote(grille: Grille, niveaux: Niveaux, noteSur: number): number | null {
  let total = 0
  for (const c of grille.criteres) {
    const choisi = niveauChoisi(c, niveaux)
    const bas = c.niveaux[0]
    const haut = c.niveaux[c.niveaux.length - 1]
    if (!choisi || !bas || !haut) return null
    total += (c.poids * (choisi.points - bas.points)) / (haut.points - bas.points)
  }
  return arrondiAuPas((total / 100) * noteSur)
}

/** Descripteur d'un niveau quand il apprend quelque chose de plus que son libellé ; vide sinon. */
export function descripteurUtile(niveau: Niveau): string {
  return niveau.descripteur.trim() === niveau.libelle.trim() ? '' : niveau.descripteur
}

/** Descripteur utile du niveau choisi pour ce critère ; vide sans choix valide. */
export function descripteurChoisi(critere: Critere, niveaux: Niveaux): string {
  const choisi = niveauChoisi(critere, niveaux)
  return choisi ? descripteurUtile(choisi) : ''
}

/** Réussite au seuil, comme le domaine Python ; null tant que la note est inconnue. */
export function reussie(note: number | null, seuil: number): boolean | null {
  return note === null ? null : note >= seuil
}

const nombre = new Intl.NumberFormat('fr-FR', { maximumFractionDigits: 2 })

/** 12.5 -> « 12,5 » ; null -> « – ». */
export function formaterNombre(n: number | null | undefined): string {
  return n === null || n === undefined ? '–' : nombre.format(n)
}

/** Deux sources divergent de plus d'un niveau sur ce critère. */
export function ecart(...niveaux: Array<number | undefined>): boolean {
  const v = niveaux.filter((n): n is number => Number.isInteger(n))
  return v.length > 1 && Math.max(...v) - Math.min(...v) > 1
}

export const complet = (grille: Grille, niveaux: Niveaux): boolean =>
  grille.criteres.every((c) => Number.isInteger(niveaux[c.code]))
