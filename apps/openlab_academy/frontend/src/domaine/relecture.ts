// Relecture par un pair : liste de ses relectures, copie anonyme à relire, un niveau et un conseil par critère.
import type { Grille, Niveaux } from './grille'

export const A_FAIRE = 'à_faire'

/** Durée de conservation d'un brouillon de relecture sur l'appareil (appareil partagé : pas d'oubli indéfini). */
export const DUREE_BROUILLON_MS = 7 * 24 * 3600 * 1000

export interface ResumeRelecture {
  relecture: string
  exercice: string
  statut: string
  echeance: string | null
  rang: number
  total: number
}

export interface VueRelecture {
  relecture: string
  exercice: string
  titre: string
  consigne: string
  contenu: string
  grille: Grille
  statut: string
  echeance: string | null
  rang: number
  total: number
  anonymat_garanti: boolean
}

export interface SaisieRelecture {
  niveaux: Niveaux
  conseils: Record<string, string>
}

/** Saisie gardée sur l'appareil, datée (ISO 8601) ; sans date pour un brouillon d'une version antérieure. */
export interface Brouillon extends SaisieRelecture {
  enregistre?: string
}

export const aFaire = (statut: string): boolean => statut === A_FAIRE

export function prochaineAFaire(liste: ResumeRelecture[]): ResumeRelecture | undefined {
  return liste.find((r) => aFaire(r.statut))
}

/** Relectures faites sur l'exercice de la relecture ouverte ; le total annoncé tant que la liste est vide. */
export function progression(liste: ResumeRelecture[], exercice: string, total: number) {
  const memeExercice = liste.filter((r) => r.exercice === exercice)
  return { faites: memeExercice.filter((r) => !aFaire(r.statut)).length, sur: memeExercice.length || total }
}

/** Un critère est complet avec un niveau et un conseil non vide. */
export function critereIncomplet(saisie: SaisieRelecture, code: string): boolean {
  return !Number.isInteger(saisie.niveaux[code]) || !saisie.conseils[code]?.trim()
}

export function criteresIncomplets(grille: Grille, saisie: SaisieRelecture): string[] {
  return grille.criteres.filter((c) => critereIncomplet(saisie, c.code)).map((c) => c.code)
}

export function brouillonPerime(brouillon: Brouillon, maintenant: Date): boolean {
  if (brouillon.enregistre === undefined) return false
  const date = Date.parse(brouillon.enregistre)
  return Number.isNaN(date) || maintenant.getTime() - date > DUREE_BROUILLON_MS
}
