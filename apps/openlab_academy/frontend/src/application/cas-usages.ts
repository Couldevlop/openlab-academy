// Assemblage des cas d'usage sur leurs ports : c'est tout ce que les écrans connaissent de l'application.
import {
  ComparerVersions,
  ConsulterFile,
  EnregistrerCorrection,
  OuvrirCopie,
  PublierNote,
  ValiderLot,
} from './correction'
import {
  AccorderDelai,
  ConsulterDroits,
  ConsulterIntendance,
  ConsulterResume,
  EnregistrerVirement,
  LienExport,
  OuvrirFiche,
} from './intendance'
import { ChargerDossier, ChoisirMode, Payer } from './paiement'
import { ConsulterReglagesEffectifs, ConsulterSouffrances } from './pilotage'
import type {
  DepotBrouillons,
  DepotCorrection,
  DepotIntendance,
  DepotPaiement,
  DepotPilotage,
  DepotRelecture,
  DepotRetour,
  Horloge,
  Navigateur,
  Session,
} from './ports'
import { ConsulterRelectures, EnvoyerRelecture, GarderBrouillon, OuvrirRelecture } from './relecture'
import { ConsulterAccuse, ConsulterRetour } from './retour'

export interface Ports {
  correction: DepotCorrection
  relecture: DepotRelecture
  retour: DepotRetour
  paiement: DepotPaiement
  intendance: DepotIntendance
  pilotage: DepotPilotage
  session: Session
  navigateur: Navigateur
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
    comparerVersions: new ComparerVersions(p.correction),
    consulterRelectures: new ConsulterRelectures(p.relecture),
    ouvrirRelecture: new OuvrirRelecture(p.relecture, p.brouillons, p.horloge),
    garderBrouillon: new GarderBrouillon(p.brouillons, p.horloge),
    envoyerRelecture: new EnvoyerRelecture(p.relecture, p.brouillons),
    consulterRetour: new ConsulterRetour(p.retour),
    consulterAccuse: new ConsulterAccuse(p.retour),
    chargerDossier: new ChargerDossier(p.paiement, p.horloge),
    choisirMode: new ChoisirMode(p.paiement),
    payer: new Payer(p.paiement, p.navigateur),
    consulterIntendance: new ConsulterIntendance(p.intendance),
    lienExport: new LienExport(p.intendance),
    ouvrirFiche: new OuvrirFiche(p.intendance, p.horloge),
    enregistrerVirement: new EnregistrerVirement(p.intendance, p.horloge),
    accorderDelai: new AccorderDelai(p.intendance, p.horloge),
    consulterResume: new ConsulterResume(p.intendance),
    consulterDroits: new ConsulterDroits(p.session),
    consulterSouffrances: new ConsulterSouffrances(p.pilotage),
    consulterReglagesEffectifs: new ConsulterReglagesEffectifs(p.pilotage),
  }
}

export type CasUsages = ReturnType<typeof creerCasUsages>
