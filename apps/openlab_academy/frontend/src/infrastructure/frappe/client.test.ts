import { frappeRequest } from 'frappe-ui-requete'
import { afterEach, describe, expect, it, vi } from 'vitest'
import * as z from 'zod/mini'
import { ErreurDepot } from '../../application/erreurs'
import { ClientFrappe, erreurDepuis, type RequeteFrappe } from './client'

const RACINE = 'openlab_academy.entrypoints.evaluation_api.'
const SCHEMA = z.object({ copie: z.string(), note: z.number() })

const echec = (proprietes: object) => Object.assign(new Error('échec'), proprietes)

describe('client de l’API d’évaluation', () => {
  it('lit en GET et écrit en POST sur les points de l’API d’évaluation', async () => {
    const requete = vi.fn<RequeteFrappe>(async () => ({ copie: 'C1', note: 12 }))
    const client = new ClientFrappe(requete)
    expect(await client.lire('mon_retour', { copie: 'C1' }, SCHEMA)).toEqual({ copie: 'C1', note: 12 })
    await client.ecrire('publier', { copie: 'C1' }, SCHEMA)
    await client.lire('mes_relectures', undefined, SCHEMA)
    expect(requete.mock.calls).toEqual([
      [{ url: `${RACINE}mon_retour`, method: 'GET', params: { copie: 'C1' } }],
      [{ url: `${RACINE}publier`, method: 'POST', params: { copie: 'C1' } }],
      [{ url: `${RACINE}mes_relectures`, method: 'GET', params: undefined }],
    ])
  })

  it('un autre module d’API se choisit à la construction', async () => {
    const requete = vi.fn<RequeteFrappe>(async () => ({ copie: 'C1', note: 12 }))
    await new ClientFrappe(requete, 'openlab_academy.entrypoints.paiement_api.').lire('mon_dossier', {}, SCHEMA)
    expect(requete.mock.calls[0]![0].url).toBe('openlab_academy.entrypoints.paiement_api.mon_dossier')
  })

  it('une réponse malformée donne une erreur typée qui dit où', async () => {
    const client = new ClientFrappe(async () => ({ copie: 7 }))
    const erreur = await client.lire('publier', {}, SCHEMA).catch((e: unknown) => e)
    expect(erreur).toBeInstanceOf(ErreurDepot)
    expect(erreur).toMatchObject({ sorte: 'reponse_invalide' })
    expect((erreur as ErreurDepot).details).toEqual([
      expect.stringMatching(/^publier\.copie : /),
      expect.stringMatching(/^publier\.note : /),
    ])
    const vide = await new ClientFrappe(async () => null).lire('publier', {}, SCHEMA).catch((e: unknown) => e)
    expect((vide as ErreurDepot).details).toEqual([expect.stringMatching(/^publier : /)])
  })

  it('une réponse malformée est signalée dans la console avec les chemins fautifs', async () => {
    const console_ = vi.spyOn(console, 'error').mockImplementation(() => undefined)
    await new ClientFrappe(async () => ({ copie: 7 })).lire('publier', {}, SCHEMA).catch(() => undefined)
    expect(console_).toHaveBeenCalledWith('Réponse invalide de publier', [
      expect.stringMatching(/^publier\.copie : /),
      expect.stringMatching(/^publier\.note : /),
    ])
    console_.mockRestore()
  })

  it('un échec d’appel devient une erreur typée', async () => {
    const client = new ClientFrappe(async () => {
      throw echec({ status: 429, exc_type: 'TooManyRequestsError', messages: [] })
    })
    await expect(client.ecrire('corriger', {}, z.unknown())).rejects.toMatchObject({ sorte: 'trop_de_demandes' })
  })
})

describe('erreurs typées', () => {
  it('limitation de débit (429)', () => {
    expect(erreurDepuis(echec({ status: 429 })).sorte).toBe('trop_de_demandes')
    expect(erreurDepuis(echec({ status: 429, messages: [{}] })).sorte).toBe('trop_de_demandes')
    expect(erreurDepuis(echec({ status: '429', exc_type: 'TooManyRequestsError' })).sorte).toBe('trop_de_demandes')
    expect(erreurDepuis(echec({ exc_type: 'TooManyRequestsError' })).sorte).toBe('trop_de_demandes')
  })

  it('accès refusé, refus métier motivé et panne', () => {
    expect(erreurDepuis(echec({ status: 403 })).sorte).toBe('acces_refuse')
    expect(erreurDepuis(echec({ exc_type: 'PermissionError' })).sorte).toBe('acces_refuse')
    const refus = erreurDepuis(
      echec({ status: 417, exc_type: 'ValidationError', messages: ['un commentaire est obligatoire'] }),
    )
    expect(refus).toMatchObject({ sorte: 'refus', details: ['un commentaire est obligatoire'] })
    expect(erreurDepuis(echec({ exc_type: 'ValidationError', messages: [] })).sorte).toBe('hors_ligne')
    expect(erreurDepuis(echec({ exc_type: 'ValidationError' })).sorte).toBe('hors_ligne')
    // chaque champ lu pour lui-même : seuls les messages textuels sont retenus
    expect(erreurDepuis(echec({ exc_type: 'ValidationError', messages: [{}, 'motif', 3] }))).toMatchObject({
      sorte: 'refus',
      details: ['motif'],
    })
    expect(erreurDepuis(echec({ exc_type: 'ValidationError', messages: [{}] })).sorte).toBe('hors_ligne')
    expect(erreurDepuis(echec({ status: 403, messages: 'motif' })).sorte).toBe('acces_refuse')
    // dossier absent : 404 de Frappe, présenté comme un accès refusé (rien ne dit si l'élément existe)
    expect(erreurDepuis(echec({ status: 404 })).sorte).toBe('acces_refuse')
    expect(erreurDepuis(echec({ exc_type: 'DoesNotExistError', messages: ['Aucun dossier'] })).sorte).toBe(
      'acces_refuse',
    )
    expect(erreurDepuis(null).sorte).toBe('hors_ligne')
    expect(erreurDepuis(new TypeError('Failed to fetch')).sorte).toBe('hors_ligne')
    expect(erreurDepuis('panne').sorte).toBe('hors_ligne')
  })
})

describe('requête Frappe réelle (fetch simulé)', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
    delete window.csrf_token
  })

  const reponse = (statut: number, corps: object) =>
    new Response(JSON.stringify(corps), { status: statut, headers: { 'Content-Type': 'application/json' } })

  it('joint le jeton CSRF de la page à chaque écriture et lit le message', async () => {
    window.csrf_token = 'jeton-de-la-page'
    const appel = vi.fn(async () => reponse(200, { message: { copie: 'C1', note: 14.5 } }))
    vi.stubGlobal('fetch', appel)
    const client = new ClientFrappe(frappeRequest)
    expect(await client.ecrire('publier', { copie: 'C1' }, SCHEMA)).toEqual({ copie: 'C1', note: 14.5 })
    const [url, options] = appel.mock.calls[0] as unknown as [string, RequestInit]
    expect(url).toBe(`/api/method/${RACINE}publier`)
    expect(options.method).toBe('POST')
    expect(options.body).toBe('{"copie":"C1"}')
    expect((options.headers as Record<string, string>)['X-Frappe-CSRF-Token']).toBe('jeton-de-la-page')
  })

  it('limitation de débit : HTTP 429 de Frappe', async () => {
    vi.stubGlobal('fetch', async () =>
      reponse(429, {
        exc_type: 'TooManyRequestsError',
        _server_messages: JSON.stringify([JSON.stringify({ message: 'Trop de requêtes' })]),
      }),
    )
    const client = new ClientFrappe(frappeRequest)
    await expect(client.ecrire('corriger', {}, z.unknown())).rejects.toMatchObject({ sorte: 'trop_de_demandes' })
  })

  it('refus métier : HTTP 417 et motifs du serveur', async () => {
    const motif = JSON.stringify({ message: 'un commentaire est obligatoire' })
    vi.stubGlobal('fetch', async () =>
      reponse(417, { exc_type: 'ValidationError', _server_messages: JSON.stringify([motif]) }),
    )
    const client = new ClientFrappe(frappeRequest)
    await expect(client.ecrire('enregistrer_relecture', {}, z.unknown())).rejects.toMatchObject({
      sorte: 'refus',
      details: ['un commentaire est obligatoire'],
    })
  })
})
