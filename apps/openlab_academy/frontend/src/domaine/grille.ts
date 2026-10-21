// Grille d'évaluation et calcul de la note, identique au domaine Python (Grille.note) : somme pondérée des niveaux,
// arrondie au demi-point, arrondi au pair le plus proche comme `round` en Python.

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

function arrondiPair(x: number): number {
  const bas = Math.floor(x)
  const reste = x - bas
  if (reste > 0.5) return bas + 1
  if (reste < 0.5) return bas
  return bas % 2 === 0 ? bas : bas + 1
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
  return arrondiPair(((total / 100) * noteSur) / PAS_NOTE) * PAS_NOTE
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
