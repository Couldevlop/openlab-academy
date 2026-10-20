// Calcul de la note à partir de la grille, identique au domaine Python (Grille.note) : somme pondérée des niveaux,
// arrondie au demi-point, arrondi au pair le plus proche comme `round` en Python.
export const PAS_NOTE = 0.5

function arrondiPair(x) {
  const bas = Math.floor(x)
  const reste = x - bas
  if (reste > 0.5) return bas + 1
  if (reste < 0.5) return bas
  return bas % 2 === 0 ? bas : bas + 1
}

/** Note sur `noteSur`, ou null tant qu'un critère n'a pas de niveau valide. */
export function calculerNote(grille, niveaux, noteSur) {
  let total = 0
  for (const c of grille.criteres) {
    const i = niveaux[c.code]
    if (!Number.isInteger(i) || i < 0 || i >= c.niveaux.length) return null
    const bas = c.niveaux[0].points
    const haut = c.niveaux[c.niveaux.length - 1].points
    total += (c.poids * (c.niveaux[i].points - bas)) / (haut - bas)
  }
  return arrondiPair(((total / 100) * noteSur) / PAS_NOTE) * PAS_NOTE
}

const nombre = new Intl.NumberFormat('fr-FR', { maximumFractionDigits: 2 })

/** 12.5 -> « 12,5 » ; null -> « – ». */
export function formaterNombre(n) {
  return n === null || n === undefined ? '–' : nombre.format(n)
}

/** Deux sources divergent de plus d'un niveau sur ce critère. */
export function ecart(...niveaux) {
  const v = niveaux.filter(Number.isInteger)
  return v.length > 1 && Math.max(...v) - Math.min(...v) > 1
}

export const complet = (grille, niveaux) => grille.criteres.every((c) => Number.isInteger(niveaux[c.code]))
