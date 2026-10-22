import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, it, vi } from 'vitest'

// Script injecté dans l'interface LMS (servi tel quel par Frappe) : exécuté ici sur une fenêtre simulée.
const SOURCE = readFileSync(resolve(__dirname, '../../../openlab_academy/public/js/paiement.js'), 'utf-8')
const ORIGINE = 'http://lms.localhost:8000'

interface Fenetre {
  fetch: (...args: unknown[]) => Promise<Response>
  location: { origin: string; assign: ReturnType<typeof vi.fn> }
}

function fenetre(reponse: () => Response): Fenetre {
  return { fetch: vi.fn(async () => reponse()), location: { origin: ORIGINE, assign: vi.fn() } }
}

function charger(w: Fenetre): void {
  // eslint-disable-next-line @typescript-eslint/no-implied-eval
  new Function('window', SOURCE)(w)
}

function json(corps: unknown, statut = 417): Response {
  return new Response(JSON.stringify(corps), {
    status: statut,
    headers: { 'content-type': 'application/json' },
  })
}

async function appeler(w: Fenetre): Promise<Response> {
  const r = await w.fetch('/api/method/lms.lms.utils.get_lesson')
  await new Promise((fin) => setTimeout(fin, 0))
  return r
}

describe('script de paiement de l’interface LMS', () => {
  it('redirige vers la page de paiement sur ParcoursBloque, réponse intacte pour l’appelant', async () => {
    const w = fenetre(() => json({ exc_type: 'ParcoursBloque', redirection: '/espace/paiement/python' }))
    charger(w)
    const r = await appeler(w)
    expect(w.location.assign).toHaveBeenCalledWith('/espace/paiement/python')
    expect((await r.json()).exc_type).toBe('ParcoursBloque')
  })

  it('n’enveloppe fetch qu’une fois', async () => {
    const w = fenetre(() => json({ exc_type: 'ParcoursBloque', redirection: '/espace/paiement/python' }))
    charger(w)
    const enveloppe = w.fetch
    charger(w)
    expect(w.fetch).toBe(enveloppe)
    await appeler(w)
    expect(w.location.assign).toHaveBeenCalledOnce()
  })

  it.each([
    ['autre site', 'https://evil.example/espace/paiement/x'],
    ['schéma relatif', '//evil.example/espace/paiement/x'],
    ['hors du préfixe', '/app/user'],
    ['remontée', '/espace/paiement/../../app'],
    ['javascript', 'javascript:alert(1)'],
    ['non textuelle', 42],
  ])('ignore une redirection %s', async (_cas, redirection) => {
    const w = fenetre(() => json({ exc_type: 'ParcoursBloque', redirection }))
    charger(w)
    await appeler(w)
    expect(w.location.assign).not.toHaveBeenCalled()
  })

  it('ignore les autres erreurs, les succès et les réponses non JSON', async () => {
    for (const r of [
      json({ exc_type: 'ValidationError', redirection: '/espace/paiement/x' }),
      json({ exc_type: 'ParcoursBloque', redirection: '/espace/paiement/x' }, 200),
      new Response('<html>', { status: 500, headers: { 'content-type': 'text/html' } }),
      new Response('pas du json', { status: 417, headers: { 'content-type': 'application/json' } }),
      json(null),
    ]) {
      const w = fenetre(() => r)
      charger(w)
      const recue = await appeler(w)
      expect(recue).toBe(r)
      expect(w.location.assign).not.toHaveBeenCalled()
    }
  })

  it('sans fetch, ne fait rien', () => {
    const w = { location: { origin: ORIGINE } } as unknown as Fenetre
    charger(w)
    expect(w.fetch).toBeUndefined()
  })

  it('URL invalide ignorée', async () => {
    const w = fenetre(() => json({ exc_type: 'ParcoursBloque', redirection: 'http://[' }))
    charger(w)
    await appeler(w)
    expect(w.location.assign).not.toHaveBeenCalled()
  })
})
