// Adaptateurs de chaque port : API de Frappe (évaluation, paiement), stockage et navigation du navigateur, horloge
// système.
import type { Ports } from '../application/cas-usages'
import { ClientFrappe, RACINE_PAIEMENT, type RequeteFrappe } from './frappe/client'
import {
  DepotCorrectionFrappe,
  DepotIntendanceFrappe,
  DepotPaiementFrappe,
  DepotRelectureFrappe,
  DepotRetourFrappe,
} from './frappe/depots'
import { DepotBrouillonsNavigateur } from './navigateur/brouillons'
import { horlogeSysteme } from './navigateur/horloge'
import { navigateurSur } from './navigateur/navigation'
import { sessionSur } from './navigateur/session'

export function creerPorts(
  requete: RequeteFrappe,
  stockage: () => Storage,
  lieu: () => Pick<Location, 'assign'>,
  droits: () => unknown,
): Ports {
  const client = new ClientFrappe(requete)
  const clientPaiement = new ClientFrappe(requete, RACINE_PAIEMENT)
  return {
    correction: new DepotCorrectionFrappe(client),
    relecture: new DepotRelectureFrappe(client),
    retour: new DepotRetourFrappe(client),
    paiement: new DepotPaiementFrappe(clientPaiement),
    intendance: new DepotIntendanceFrappe(clientPaiement),
    session: sessionSur(droits),
    navigateur: navigateurSur(lieu),
    brouillons: new DepotBrouillonsNavigateur(stockage),
    horloge: horlogeSysteme,
  }
}
