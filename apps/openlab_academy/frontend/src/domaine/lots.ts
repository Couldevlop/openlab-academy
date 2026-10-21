// Lots (Gradescope) : copies d'un même exercice auxquelles l'IA propose, avec assurance, les mêmes niveaux.
import type { ElementFile, FileCorrection } from './correction'

export interface LotAffiche {
  ids: string[]
  /** Copies du lot ; une copie sortie de la file entre-temps n'est connue que par son identifiant. */
  copies: Array<Pick<ElementFile, 'copie'> & Partial<ElementFile>>
  exercice: string
  /** Plus faible confiance de l'IA dans le lot (1 si inconnue). */
  confiance: number
}

export function lotsAffiches(file: FileCorrection): LotAffiche[] {
  const parCopie = new Map(file.copies.map((c) => [c.copie, c]))
  return file.lots.map((ids) => {
    const copies: LotAffiche['copies'] = ids.map((id) => parCopie.get(id) ?? { copie: id })
    return {
      ids,
      copies,
      exercice: copies[0]?.exercice ?? '',
      confiance: Math.min(...copies.map((c) => c.confiance ?? 1)),
    }
  })
}
