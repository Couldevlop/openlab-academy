import { describe, expect, it } from 'vitest'
import { DepotBrouillonsNavigateur } from './brouillons'
import { horlogeSysteme } from './horloge'

const BROUILLON = { niveaux: { a: 1 }, conseils: { a: 'Bien.' }, enregistre: '2026-11-03T10:00:00.000Z' }

const indisponible = (): Storage => {
  throw new DOMException('stockage refusé', 'SecurityError')
}

describe('brouillons gardés dans le navigateur', () => {
  it('garde, relit et oublie un brouillon par relecture', () => {
    localStorage.clear()
    const depot = new DepotBrouillonsNavigateur(() => localStorage)
    depot.garder('R1', BROUILLON)
    expect(localStorage.getItem('openlab-relecture-R1')).toBe(JSON.stringify(BROUILLON))
    expect(depot.lire('R1')).toEqual(BROUILLON)
    expect(depot.lire('R2')).toBeNull()
    depot.oublier('R1')
    expect(depot.lire('R1')).toBeNull()
  })

  it('relit un brouillon d’une version antérieure, sans date', () => {
    localStorage.setItem('openlab-relecture-R1', JSON.stringify({ niveaux: {}, conseils: { a: 'x' } }))
    expect(new DepotBrouillonsNavigateur(() => localStorage).lire('R1')).toEqual({ niveaux: {}, conseils: { a: 'x' } })
  })

  it('un brouillon illisible ou altéré est ignoré', () => {
    const depot = new DepotBrouillonsNavigateur(() => localStorage)
    localStorage.setItem('openlab-relecture-R1', '{pas du json')
    expect(depot.lire('R1')).toBeNull()
    localStorage.setItem('openlab-relecture-R1', JSON.stringify({ niveaux: { a: 'x' }, conseils: {} }))
    expect(depot.lire('R1')).toBeNull()
  })

  it('stockage indisponible (navigation privée) : rien à garder, jamais d’échec', () => {
    const depot = new DepotBrouillonsNavigateur(indisponible)
    expect(() => depot.garder('R1', BROUILLON)).not.toThrow()
    expect(depot.lire('R1')).toBeNull()
    expect(() => depot.oublier('R1')).not.toThrow()
  })
})

describe('horloge système', () => {
  it("donne l'heure courante", () => {
    const avant = Date.now()
    const t = horlogeSysteme.maintenant().getTime()
    expect(t).toBeGreaterThanOrEqual(avant)
    expect(t).toBeLessThanOrEqual(Date.now())
  })
})
