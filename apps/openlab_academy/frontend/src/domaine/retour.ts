// Retour de l'apprenant : note, niveau et commentaire par critère, mention « provisoire ». Tant que l'apprenant doit
// des relectures, la note reste masquée (le serveur n'envoie alors ni note ni critère).

export interface CritereRetour {
  code: string
  libelle: string
  poids: number
  niveau: number | null
  niveau_libelle: string
  /** Libellés des niveaux de la grille. */
  niveaux: string[]
  auto_evaluation: number | null
  commentaire: string
  pairs: string[]
}

export interface Retour {
  copie: string
  exercice: string
  titre: string
  statut: string
  provisoire: boolean
  masquee: boolean
  note: number | null
  note_sur: number | null
  reussite: boolean | null
  criteres: CritereRetour[]
  commentaire_general: string
  message: string
}

export type Segment = 'vide' | 'atteint' | 'sommet'

/** Barre de niveaux : atteints jusqu'au niveau obtenu, le dernier niveau marqué comme sommet. */
export function segments(c: CritereRetour): Segment[] {
  const dernier = c.niveaux.length - 1
  return c.niveaux.map((_, i) => (c.niveau === null || i > c.niveau ? 'vide' : i === dernier ? 'sommet' : 'atteint'))
}

export function remarquesPairs(retour: Retour | null): string[] {
  return [...new Set((retour?.criteres ?? []).flatMap((c) => c.pairs))]
}

export function detailVisible(retour: Retour | null): boolean {
  return !!retour && !retour.masquee && retour.criteres.length > 0
}

export function libelleAutoEvaluation(c: CritereRetour): string {
  return c.auto_evaluation === null ? '' : (c.niveaux[c.auto_evaluation] ?? '')
}
