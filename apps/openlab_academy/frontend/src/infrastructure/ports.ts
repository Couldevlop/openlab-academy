// Adaptateurs de chaque port : API de Frappe (évaluation, paiement), stockage et navigation du navigateur, horloge
// système.
import type { Ports } from '../application/cas-usages'
import { ClientFrappe, RACINE_PAIEMENT, type RequeteFrappe } from './frappe/client'
import { DepotCorrectionFrappe, DepotPaiementFrappe, DepotRelectureFrappe, DepotRetourFrappe } from './frappe/depots'
import { DepotBrouillonsNavigateur } from './navigateur/brouillons'
import { horlogeSysteme } from './navigateur/horloge'
import { navigateurSur } from './navigateur/navigation'

export function creerPorts(
  requete: RequeteFrappe,
  stockage: () => Storage,
  lieu: () => Pick<Location, 'assign'>,
): Ports {
  const client = new ClientFrappe(requete)
  return {
    correction: new DepotCorrectionFrappe(client),
    relecture: new DepotRelectureFrappe(client),
    retour: new DepotRetourFrappe(client),
    paiement: new DepotPaiementFrappe(new ClientFrappe(requete, RACINE_PAIEMENT)),
    navigateur: navigateurSur(lieu),
    brouillons: new DepotBrouillonsNavigateur(stockage),
    horloge: horlogeSysteme,
  }
}
