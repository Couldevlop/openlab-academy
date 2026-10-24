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

/** Accusé de dépôt d'une copie (evaluation_api.accuse_depot) : horodatage UTC et empreinte de ce qui a été rendu. */
export interface AccuseDepot {
  copie: string
  exercice: string
  version: number
  /** « 2026-11-03T21:12:05Z » */
  depose_le: string | null
  empreinte: string
  algorithme: string
  instantane: string
  commit: string
}

// Abidjan = UTC : l'heure affichée est celle du site, quel que soit le fuseau du téléphone
const horodatageDepot = new Intl.DateTimeFormat('fr-FR', {
  timeZone: 'Africa/Abidjan',
  day: 'numeric',
  month: 'long',
  year: 'numeric',
  hour: '2-digit',
  minute: '2-digit',
  second: '2-digit',
})

/** « 3 novembre 2026 à 21:12:05 » ; vide si l'horodatage est absent ou illisible. */
export function formaterDepot(iso: string | null): string {
  const d = iso ? new Date(iso) : null
  return d && !Number.isNaN(d.getTime()) ? horodatageDepot.format(d) : ''
}

const INSTANTANES: Record<string, string> = {
  en_cours: 'Instantané du dépôt en cours.',
  pris: 'Instantané du dépôt conservé.',
  indisponible: 'Dépôt injoignable au rendu : aucun instantané conservé.',
}

/** État de l'instantané d'un rendu par lien ; vide pour un rendu texte ou fichier. */
export function libelleInstantane(instantane: string): string {
  return INSTANTANES[instantane] ?? ''
}
