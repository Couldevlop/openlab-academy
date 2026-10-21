import { describe, expect, it } from 'vitest'
import { critere, grille, resumeRelecture } from '../test/fabriques'
import {
  DUREE_BROUILLON_MS,
  aFaire,
  brouillonPerime,
  critereIncomplet,
  criteresIncomplets,
  progression,
  prochaineAFaire,
} from './relecture'

describe('relectures', () => {
  const faite = resumeRelecture('R1', { statut: 'faite' })
  const liste = [faite, resumeRelecture('R2'), resumeRelecture('R3', { exercice: 'ASG-2' })]

  it('la prochaine relecture à faire', () => {
    expect(aFaire('à_faire')).toBe(true)
    expect(aFaire('faite')).toBe(false)
    expect(prochaineAFaire(liste)?.relecture).toBe('R2')
    expect(prochaineAFaire([faite])).toBeUndefined()
  })

  it("progression sur l'exercice de la relecture ouverte, le total annoncé à défaut", () => {
    expect(progression(liste, 'ASG-1', 3)).toEqual({ faites: 1, sur: 2 })
    expect(progression([], 'ASG-1', 3)).toEqual({ faites: 0, sur: 3 })
  })

  it('un critère est complet avec un niveau et un conseil non vide', () => {
    const g = grille(critere('pertinence', 50), critere('rigueur', 50))
    const saisie = { niveaux: { pertinence: 1, rigueur: 2 }, conseils: { pertinence: 'Bien.', rigueur: '   ' } }
    expect(critereIncomplet(saisie, 'pertinence')).toBe(false)
    expect(critereIncomplet(saisie, 'rigueur')).toBe(true)
    expect(critereIncomplet({ niveaux: {}, conseils: { pertinence: 'x' } }, 'pertinence')).toBe(true)
    expect(criteresIncomplets(g, saisie)).toEqual(['rigueur'])
  })

  it('un brouillon expire après sa durée de conservation', () => {
    const maintenant = new Date('2026-11-10T12:00:00Z')
    const ilYa = (ms: number) => new Date(maintenant.getTime() - ms).toISOString()
    const b = { niveaux: {}, conseils: {} }
    expect(brouillonPerime({ ...b, enregistre: ilYa(DUREE_BROUILLON_MS - 1) }, maintenant)).toBe(false)
    expect(brouillonPerime({ ...b, enregistre: ilYa(DUREE_BROUILLON_MS + 1) }, maintenant)).toBe(true)
    expect(brouillonPerime({ ...b, enregistre: 'pas une date' }, maintenant)).toBe(true)
    // brouillon d'une version antérieure, sans date : conservé
    expect(brouillonPerime(b, maintenant)).toBe(false)
  })
})
