// Appels aux API de Frappe (évaluation, paiement) : seul endroit qui parle au réseau. La requête Frappe (frappe-ui) joint le
// jeton CSRF de la page à chaque écriture ; chaque réponse est validée par son schéma avant d'entrer dans
// l'application, et chaque échec devient une ErreurDepot typée.
import * as z from 'zod/mini'
import { ErreurDepot } from '../../application/erreurs'

export const RACINE_EVALUATION = 'openlab_academy.entrypoints.evaluation_api.'
export const RACINE_PAIEMENT = 'openlab_academy.entrypoints.paiement_api.'

export interface OptionsRequete {
  url: string
  method: 'GET' | 'POST'
  params?: Record<string, unknown> | undefined
}

/** Requête Frappe : rend le `message` de la réponse, ou rejette avec l'erreur décrite par Frappe. */
export type RequeteFrappe = (options: OptionsRequete) => Promise<unknown>

export type Parametres = Record<string, unknown> | undefined

// erreur levée par la requête Frappe : statut HTTP, type d'exception Python et messages du serveur, chacun lu pour
// lui-même (un champ malformé n'efface pas les autres), seuls les messages textuels retenus
const STATUT = z.number()
const TYPE = z.string()

function champ<T>(schema: z.ZodMiniType<T>, valeur: unknown): T | undefined {
  const lu = schema.safeParse(valeur)
  return lu.success ? lu.data : undefined
}

export function erreurDepuis(erreur: unknown): ErreurDepot {
  const brut: Record<string, unknown> = typeof erreur === 'object' && erreur !== null ? { ...erreur } : {}
  const status = champ(STATUT, brut.status)
  const type = champ(TYPE, brut.exc_type)
  const messages = Array.isArray(brut.messages) ? brut.messages.filter((m): m is string => typeof m === 'string') : []
  if (status === 429 || type === 'TooManyRequestsError') return new ErreurDepot('trop_de_demandes')
  if (status === 403 || type === 'PermissionError') return new ErreurDepot('acces_refuse')
  // élément absent (404) : présenté comme refusé, sans dire s'il existe
  if (status === 404 || type === 'DoesNotExistError') return new ErreurDepot('acces_refuse')
  if (type === 'ValidationError' && messages.length) return new ErreurDepot('refus', messages)
  return new ErreurDepot('hors_ligne')
}

export class ClientFrappe {
  constructor(
    private readonly requete: RequeteFrappe,
    private readonly racine = RACINE_EVALUATION,
  ) {}

  lire<T>(methode: string, params: Parametres, schema: z.ZodMiniType<T>): Promise<T> {
    return this.appeler('GET', methode, params, schema)
  }

  ecrire<T>(methode: string, params: Parametres, schema: z.ZodMiniType<T>): Promise<T> {
    return this.appeler('POST', methode, params, schema)
  }

  private async appeler<T>(method: 'GET' | 'POST', methode: string, params: Parametres, schema: z.ZodMiniType<T>) {
    let reponse: unknown
    try {
      reponse = await this.requete({ url: this.racine + methode, method, params })
    } catch (e) {
      throw erreurDepuis(e)
    }
    const lu = schema.safeParse(reponse)
    if (!lu.success) {
      const chemins = lu.error.issues.map((i) => `${[methode, ...i.path.map(String)].join('.')} : ${i.message}`)
      console.error(`Réponse invalide de ${methode}`, chemins) // contrat rompu entre le serveur et l'écran
      throw new ErreurDepot('reponse_invalide', chemins)
    }
    return lu.data
  }
}
