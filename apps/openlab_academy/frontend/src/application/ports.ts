// Ports des cas d'usage : ce que l'application attend du monde extérieur (API d'évaluation, appareil, horloge).
// Les adaptateurs (infrastructure) les implémentent ; un échec d'appel est une ErreurDepot.
import type { ChargeCorrection, FileCorrection, ResultatLot, VueCopie } from '../domaine/correction'
import type { Brouillon, ResumeRelecture, SaisieRelecture, VueRelecture } from '../domaine/relecture'
import type { FicheIntendance, ResumeFinances, VueIntendance } from '../domaine/intendance'
import type { DossierPaiement, Mode, MonPaiement } from '../domaine/paiement'
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

/** Dossier de paiement de l'apprenant connecté : le serveur le retrouve par la session, jamais par un identifiant. */
export interface DepotPaiement {
  /** Le dossier du parcours, ou l'état gratuit d'un parcours gratuit (MOOC). */
  monDossier(cours: string): Promise<MonPaiement>
  /** Rend le dossier replanifié dans le nouveau mode. */
  choisirMode(cours: string, mode: Mode, telephone: string): Promise<DossierPaiement>
  /** Adresse de la page de paiement CinetPay. */
  payer(cours: string): Promise<string>
}

/** Virement saisi par un agent, relu par le cas d'usage. */
export interface Virement {
  montant: number
  reference: string
  /** AAAA-MM-JJ */
  date_paiement: string
  motif: string
}

/** API de l'intendance et de l'administration ; le serveur vérifie le rôle à chaque appel et journalise l'acteur. */
export interface DepotIntendance {
  intendance(filtres: Record<string, string>): Promise<VueIntendance>
  fiche(dossier: string): Promise<FicheIntendance>
  enregistrerVirement(dossier: string, virement: Virement): Promise<void>
  accorderDelai(dossier: string, jusquau: string, motif: string): Promise<void>
  /** Adresse du classeur Excel des lignes filtrées. */
  lienExport(filtres: Record<string, string>): string
  resume(): Promise<ResumeFinances>
}

/** Écrans ouverts à l'utilisateur ; ne sert qu'à afficher les liens, l'API refuse elle-même. */
export interface Droits {
  intendance: boolean
  finances: boolean
}

export interface Session {
  droits(): Droits
}

/** Quitte l'application pour une page externe (paiement). */
export interface Navigateur {
  aller(url: string): void
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
