// Faux ports en mémoire pour tester cas d'usage et écrans sans réseau ni stockage réel.
import { vi } from 'vitest'
import { creerCasUsages, type Ports } from '../application/cas-usages'
import type {
  DepotBrouillons,
  DepotCorrection,
  DepotPaiement,
  DepotRelecture,
  DepotRetour,
  Horloge,
  Navigateur,
} from '../application/ports'
import type { Brouillon } from '../domaine/relecture'

export const MAINTENANT = new Date('2026-11-03T10:00:00Z')

export function fauxDepotCorrection() {
  return {
    file: vi.fn<DepotCorrection['file']>(),
    copie: vi.fn<DepotCorrection['copie']>(),
    corriger: vi.fn<DepotCorrection['corriger']>(async () => undefined),
    publier: vi.fn<DepotCorrection['publier']>(),
    validerLot: vi.fn<DepotCorrection['validerLot']>(),
  } satisfies DepotCorrection
}

export function fauxDepotRelecture() {
  return {
    mesRelectures: vi.fn<DepotRelecture['mesRelectures']>(async () => []),
    relecture: vi.fn<DepotRelecture['relecture']>(),
    enregistrer: vi.fn<DepotRelecture['enregistrer']>(async () => undefined),
  } satisfies DepotRelecture
}

export function fauxDepotRetour() {
  return { monRetour: vi.fn<DepotRetour['monRetour']>() } satisfies DepotRetour
}

export function fauxDepotPaiement() {
  return {
    monDossier: vi.fn<DepotPaiement['monDossier']>(),
    choisirMode: vi.fn<DepotPaiement['choisirMode']>(),
    payer: vi.fn<DepotPaiement['payer']>(),
  } satisfies DepotPaiement
}

/** Navigation retenue au lieu d'être suivie. */
export function fauxNavigateur() {
  return { aller: vi.fn<Navigateur['aller']>() } satisfies Navigateur
}

/** Brouillons gardés dans une table en mémoire, comme sur l'appareil. */
export class FauxBrouillons implements DepotBrouillons {
  readonly table = new Map<string, Brouillon>()

  lire(relecture: string): Brouillon | null {
    return this.table.get(relecture) ?? null
  }

  garder(relecture: string, brouillon: Brouillon): void {
    this.table.set(relecture, brouillon)
  }

  oublier(relecture: string): void {
    this.table.delete(relecture)
  }
}

export const horlogeFixe = (date = MAINTENANT): Horloge => ({ maintenant: () => date })

export function fauxPorts() {
  return {
    correction: fauxDepotCorrection(),
    relecture: fauxDepotRelecture(),
    retour: fauxDepotRetour(),
    paiement: fauxDepotPaiement(),
    navigateur: fauxNavigateur(),
    brouillons: new FauxBrouillons(),
    horloge: horlogeFixe(),
  } satisfies Ports
}

export type FauxPorts = ReturnType<typeof fauxPorts>

/** Faux ports et cas d'usage réels branchés dessus. */
export function fauxCasUsages(ports: FauxPorts = fauxPorts()) {
  return { ports, cas: creerCasUsages(ports) }
}
