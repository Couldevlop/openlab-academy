// Adaptateurs de chaque port : API d'évaluation de Frappe, stockage du navigateur, horloge système.
import type { Ports } from '../application/cas-usages'
import { ClientFrappe, type RequeteFrappe } from './frappe/client'
import { DepotCorrectionFrappe, DepotRelectureFrappe, DepotRetourFrappe } from './frappe/depots'
import { DepotBrouillonsNavigateur } from './navigateur/brouillons'
import { horlogeSysteme } from './navigateur/horloge'

export function creerPorts(requete: RequeteFrappe, stockage: () => Storage): Ports {
  const client = new ClientFrappe(requete)
  return {
    correction: new DepotCorrectionFrappe(client),
    relecture: new DepotRelectureFrappe(client),
    retour: new DepotRetourFrappe(client),
    brouillons: new DepotBrouillonsNavigateur(stockage),
    horloge: horlogeSysteme,
  }
}
