import { describe, expect, it, vi } from 'vitest'

vi.mock('frappe-ui-requete', () => ({ frappeRequest: vi.fn(async (options) => options) }))

const { ACCES_REFUSE, HORS_LIGNE, TROP_DE_DEMANDES, ecrire, lire, messageErreur } = await import('./api')

describe('api', () => {
  it('lit en GET et écrit en POST sur les points de l’API d’évaluation', async () => {
    expect(await lire('mon_retour', { copie: 'C1' })).toEqual({
      url: 'openlab_academy.entrypoints.evaluation_api.mon_retour', method: 'GET', params: { copie: 'C1' },
    })
    expect((await ecrire('publier', { copie: 'C1' })).method).toBe('POST')
  })

  it('message clair pour la limitation de débit (429)', () => {
    expect(messageErreur({ status: 429 })).toBe(TROP_DE_DEMANDES)
    expect(messageErreur({ exc_type: 'TooManyRequestsError' })).toBe(TROP_DE_DEMANDES)
  })

  it('accès refusé, refus métier et panne', () => {
    expect(messageErreur({ status: 403 })).toBe(ACCES_REFUSE)
    expect(messageErreur({ status: 417, exc_type: 'ValidationError', messages: ['un commentaire est obligatoire'] }))
      .toBe('un commentaire est obligatoire')
    expect(messageErreur(new TypeError('Failed to fetch'))).toBe(HORS_LIGNE)
  })
})
