// Assemblage des cas d'usage sur leurs ports : c'est tout ce que les écrans connaissent de l'application.
import { ConsulterFile, EnregistrerCorrection, OuvrirCopie, PublierNote, ValiderLot } from './correction'
import type { DepotBrouillons, DepotCorrection, DepotRelecture, DepotRetour, Horloge } from './ports'
import { ConsulterRelectures, EnvoyerRelecture, GarderBrouillon, OuvrirRelecture } from './relecture'
import { ConsulterRetour } from './retour'

export interface Ports {
  correction: DepotCorrection
  relecture: DepotRelecture
  retour: DepotRetour
  brouillons: DepotBrouillons
  horloge: Horloge
}

export function creerCasUsages(p: Ports) {
  return {
    consulterFile: new ConsulterFile(p.correction),
    ouvrirCopie: new OuvrirCopie(p.correction),
    enregistrerCorrection: new EnregistrerCorrection(p.correction),
    publierNote: new PublierNote(p.correction),
    validerLot: new ValiderLot(p.correction),
    consulterRelectures: new ConsulterRelectures(p.relecture),
    ouvrirRelecture: new OuvrirRelecture(p.relecture, p.brouillons, p.horloge),
    garderBrouillon: new GarderBrouillon(p.brouillons, p.horloge),
    envoyerRelecture: new EnvoyerRelecture(p.relecture, p.brouillons),
    consulterRetour: new ConsulterRetour(p.retour),
  }
}

export type CasUsages = ReturnType<typeof creerCasUsages>
