// Ports des cas d'usage : ce que l'application attend du monde extérieur (API d'évaluation, appareil, horloge).
// Les adaptateurs (infrastructure) les implémentent ; un échec d'appel est une ErreurDepot.
import type { ChargeCorrection, FileCorrection, ResultatLot, VueCopie } from '../domaine/correction'
import type { Brouillon, ResumeRelecture, SaisieRelecture, VueRelecture } from '../domaine/relecture'
import type { Retour } from '../domaine/retour'

export interface DepotCorrection {
  file(exercice?: string): Promise<FileCorrection>
  copie(copie: string): Promise<VueCopie>
  corriger(charge: ChargeCorrection): Promise<void>
  /** Publie la note enregistrée ; rend la note publiée. */
  publier(copie: string): Promise<number>
  validerLot(copies: string[], etPublier: boolean): Promise<ResultatLot>
}

export interface DepotRelecture {
  mesRelectures(): Promise<ResumeRelecture[]>
  relecture(relecture: string): Promise<VueRelecture>
  enregistrer(relecture: string, saisie: SaisieRelecture): Promise<void>
}

export interface DepotRetour {
  monRetour(copie: string): Promise<Retour>
}

/** Brouillons de relecture gardés sur l'appareil ; un stockage indisponible ne fait jamais échouer l'écran. */
export interface DepotBrouillons {
  lire(relecture: string): Brouillon | null
  garder(relecture: string, brouillon: Brouillon): void
  oublier(relecture: string): void
}

export interface Horloge {
  maintenant(): Date
}
