// Appels à l'API d'évaluation de Frappe : seul endroit qui parle au réseau. La requête Frappe (frappe-ui) joint le
// jeton CSRF de la page à chaque écriture ; chaque réponse est validée par son schéma avant d'entrer dans
// l'application, et chaque échec devient une ErreurDepot typée.
import * as z from 'zod/mini'
import { ErreurDepot } from '../../application/erreurs'

const RACINE = 'openlab_academy.entrypoints.evaluation_api.'

export interface OptionsRequete {
  url: string
  method: 'GET' | 'POST'
  params?: Record<string, unknown> | undefined
}

/** Requête Frappe : rend le `message` de la réponse, ou rejette avec l'erreur décrite par Frappe. */
export type RequeteFrappe = (options: OptionsRequete) => Promise<unknown>

export type Parametres = Record<string, unknown> | undefined

// erreur levée par la requête Frappe : statut HTTP, type d'exception Python et messages du serveur
const ECHEC_FRAPPE = z.object({
  status: z.optional(z.number()),
  exc_type: z.optional(z.string()),
  messages: z.optional(z.array(z.string())),
})

export function erreurDepuis(erreur: unknown): ErreurDepot {
  const lu = ECHEC_FRAPPE.safeParse(erreur)
  const { status, exc_type: type, messages = [] } = lu.success ? lu.data : {}
  if (status === 429 || type === 'TooManyRequestsError') return new ErreurDepot('trop_de_demandes')
  if (status === 403 || type === 'PermissionError') return new ErreurDepot('acces_refuse')
  if (type === 'ValidationError' && messages.length) return new ErreurDepot('refus', messages)
  return new ErreurDepot('hors_ligne')
}

export class ClientFrappe {
  constructor(private readonly requete: RequeteFrappe) {}

  lire<T>(methode: string, params: Parametres, schema: z.ZodMiniType<T>): Promise<T> {
    return this.appeler('GET', methode, params, schema)
  }

  ecrire<T>(methode: string, params: Parametres, schema: z.ZodMiniType<T>): Promise<T> {
    return this.appeler('POST', methode, params, schema)
  }

  private async appeler<T>(method: 'GET' | 'POST', methode: string, params: Parametres, schema: z.ZodMiniType<T>) {
    let reponse: unknown
    try {
      reponse = await this.requete({ url: RACINE + methode, method, params })
    } catch (e) {
      throw erreurDepuis(e)
    }
    const lu = schema.safeParse(reponse)
    if (!lu.success) {
      throw new ErreurDepot(
        'reponse_invalide',
        lu.error.issues.map((i) => `${[methode, ...i.path.map(String)].join('.')} : ${i.message}`),
      )
    }
    return lu.data
  }
}
