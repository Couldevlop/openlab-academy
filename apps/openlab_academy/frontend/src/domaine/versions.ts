// Comparaison entre deux versions d'une copie (re-soumission) : différence ligne à ligne par plus longue
// sous-séquence commune, comme `diff`. Les textes restent bruts : l'écran les échappe.

export type SorteLigne = 'egal' | 'ajout' | 'retrait'

export interface LigneDiff {
  sorte: SorteLigne
  texte: string
}

export interface ResumeDiff {
  ajouts: number
  retraits: number
}

const lignes = (texte: string) => (texte ? texte.replace(/\r\n?/g, '\n').split('\n') : [])

/** Lignes de l'ancienne version et de la nouvelle, dans l'ordre : identiques, retirées, ajoutées. */
export function comparerTextes(ancien: string, nouveau: string): LigneDiff[] {
  const a = lignes(ancien)
  const b = lignes(nouveau)
  // longueurs[i][j] : plus longue sous-séquence commune de a[i:] et b[j:]
  const longueurs = Array.from({ length: a.length + 1 }, () => new Array<number>(b.length + 1).fill(0))
  for (let i = a.length - 1; i >= 0; i--) {
    for (let j = b.length - 1; j >= 0; j--) {
      longueurs[i]![j] =
        a[i] === b[j] ? longueurs[i + 1]![j + 1]! + 1 : Math.max(longueurs[i + 1]![j]!, longueurs[i]![j + 1]!)
    }
  }
  const resultat: LigneDiff[] = []
  let i = 0
  let j = 0
  while (i < a.length && j < b.length) {
    if (a[i] === b[j]) {
      resultat.push({ sorte: 'egal', texte: a[i]! })
      i++
      j++
    } else if (longueurs[i + 1]![j]! >= longueurs[i]![j + 1]!) {
      resultat.push({ sorte: 'retrait', texte: a[i++]! })
    } else {
      resultat.push({ sorte: 'ajout', texte: b[j++]! })
    }
  }
  while (i < a.length) resultat.push({ sorte: 'retrait', texte: a[i++]! })
  while (j < b.length) resultat.push({ sorte: 'ajout', texte: b[j++]! })
  return resultat
}

export function resumerDiff(diff: LigneDiff[]): ResumeDiff {
  return {
    ajouts: diff.filter((l) => l.sorte === 'ajout').length,
    retraits: diff.filter((l) => l.sorte === 'retrait').length,
  }
}

const pluriel = (n: number, mot: string) => `${n} ligne${n > 1 ? 's' : ''} ${mot}${n > 1 ? 's' : ''}`

/** « 2 lignes ajoutées, 1 ligne retirée » ; « Aucune différence » si les textes sont identiques. */
export function libelleResume(r: ResumeDiff): string {
  if (!r.ajouts && !r.retraits) return 'Aucune différence'
  return [r.ajouts && pluriel(r.ajouts, 'ajoutée'), r.retraits && pluriel(r.retraits, 'retirée')]
    .filter(Boolean)
    .join(', ')
}
