// Appels à l'API d'évaluation. frappeRequest (frappe-ui) joint le jeton CSRF de la page à chaque écriture.
import { frappeRequest } from 'frappe-ui-requete'

const RACINE = 'openlab_academy.entrypoints.evaluation_api.'

export const lire = (methode, params) => frappeRequest({ url: RACINE + methode, method: 'GET', params })

export const ecrire = (methode, params) => frappeRequest({ url: RACINE + methode, method: 'POST', params })

export const TROP_DE_DEMANDES =
  'Trop de demandes en peu de temps. Patientez quelques minutes puis réessayez : votre saisie est conservée.'
export const ACCES_REFUSE = "Cet élément n'existe pas ou ne vous est pas ouvert."
export const HORS_LIGNE = 'Le serveur ne répond pas. Vérifiez votre connexion puis réessayez.'

/** Message lisible d'une erreur d'appel (texte brut, affiché échappé). */
export function messageErreur(erreur) {
  if (erreur?.status === 429 || erreur?.exc_type === 'TooManyRequestsError') return TROP_DE_DEMANDES
  if (erreur?.status === 403 || erreur?.exc_type === 'PermissionError') return ACCES_REFUSE
  if (erreur?.exc_type === 'ValidationError' && erreur.messages?.length) return erreur.messages.join(' ')
  return HORS_LIGNE
}
