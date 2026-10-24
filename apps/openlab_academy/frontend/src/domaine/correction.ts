// Correction par le formateur ou un juré : file des copies, copie à corriger avec ses sources (auto-évaluation, IA,
// pairs, jury), saisie du correcteur et règles de l'écran (IA écartée sur copie signalée, raccourcis, enchaînement).
import type { Grille, Niveaux } from './grille'

/** Clé du commentaire général parmi les commentaires d'une correction. */
export const GENERAL = 'general'

export type Role = 'formateur' | 'jury'

export interface ElementFile {
  copie: string
  apprenant: string
  exercice: string
  cohorte: string
  version: number
  statut: string
  etape: string
  echeance: string | null
  role: Role
  confiance: number | null
  ecarts: string[]
  signalee: boolean
  corrigee: boolean
}

export interface FileCorrection {
  copies: ElementFile[]
  /** Lots validables d'un geste : identifiants de copies. */
  lots: string[][]
}

export interface PropositionIa {
  niveaux: Niveaux
  justifications: Record<string, string>
  citations: Record<string, string>
  confiance: number | null
}

export interface AvisPairs {
  mediane: Niveaux
  nombre: number
  commentaires: Array<Record<string, string>>
}

export interface AvisJury {
  mediane: Niveaux
  nombre: number
  attendus: number
}

export interface CorrectionFormateur {
  niveaux: Niveaux
  commentaires: Record<string, string>
  auteur: string
  au_nom_de: string | null
}

/** Version antérieure de la même soumission (re-soumission). */
export interface VersionPrecedente {
  copie: string
  version: number
  rendue_le: string | null
}

/** Texte d'une version antérieure, pour la comparer à la version corrigée. */
export interface VersionTexte extends VersionPrecedente {
  contenu: string
}

export interface VueCopie {
  copie: string
  apprenant: string
  exercice: string
  cohorte: string
  titre: string
  note_sur: number
  seuil_reussite: number
  version: number
  statut: string
  etape: string
  echeance: string | null
  role: Role
  au_nom_de: string | null
  contenu: string
  source_url: string
  commit: string
  consigne: string
  grille: Grille
  auto_evaluation: Niveaux | null
  controles: string[]
  ia: PropositionIa | null
  pairs: AvisPairs
  jury: AvisJury
  formateur: CorrectionFormateur | null
  ecarts: string[]
  signalement: string
  /** Version remplacée par un nouveau rendu : seule la dernière se corrige. */
  remplacee: boolean
  versions_precedentes: VersionPrecedente[]
}

/** Ce que le correcteur a saisi : niveaux, commentaires par critère et commentaire général. */
export interface Saisie {
  niveaux: Niveaux
  commentaires: Record<string, string>
  general: string
}

/** Charge de l'appel `corriger`. */
export interface ChargeCorrection {
  copie: string
  niveaux: Niveaux
  commentaires: Record<string, string>
}

export interface ResultatLot {
  copies: string[]
  publiees: string[]
}

const STATUTS: Record<string, string> = { a_corriger: 'à corriger', provisoire: 'note provisoire publiée' }

export function libelleStatut(statut: string): string {
  return STATUTS[statut] ?? statut
}

/** Copie signalée (injection) : la pré-correction de l'IA est écartée, ni puces, ni justification, ni citation. */
export function propositionRetenue(vue: VueCopie): PropositionIa | null {
  return vue.signalement ? null : vue.ia
}

/** Saisie de départ : la correction déjà enregistrée par le formateur, vierge sinon (et pour un juré). */
export function saisieInitiale(vue: VueCopie): Saisie {
  const miens = vue.role === 'formateur' ? vue.formateur : null
  const { [GENERAL]: general = '', ...commentaires } = miens?.commentaires ?? {}
  return { niveaux: { ...miens?.niveaux }, commentaires, general }
}

export function chargeCorrection(copie: string, saisie: Saisie): ChargeCorrection {
  return { copie, niveaux: saisie.niveaux, commentaires: { ...saisie.commentaires, [GENERAL]: saisie.general } }
}

/** Après publication : la copie qui suivait si elle reste à corriger, sinon une autre que la copie publiée. */
export function copieApresPublication(restantes: string[], suivante: string | undefined, courante: string) {
  return suivante !== undefined && restantes.includes(suivante) ? suivante : restantes.find((c) => c !== courante)
}

export interface ChoixClavier {
  code: string
  indice: number
  /** Critère actif après le choix : le suivant, ou le dernier. */
  actif: string
}

/** Touche 1 à 9 : niveau du critère actif (le premier à défaut), puis le critère suivant devient actif. */
export function niveauParTouche(grille: Grille, actif: string, touche: string): ChoixClavier | null {
  if (!/^[1-9]$/.test(touche)) return null
  const criteres = grille.criteres
  const position = Math.max(
    0,
    criteres.findIndex((c) => c.code === actif),
  )
  const critere = criteres[position]
  const indice = Number(touche) - 1
  const suivant = criteres[Math.min(position + 1, criteres.length - 1)]
  if (!critere || !suivant || indice >= critere.niveaux.length) return null
  return { code: critere.code, indice, actif: suivant.code }
}
