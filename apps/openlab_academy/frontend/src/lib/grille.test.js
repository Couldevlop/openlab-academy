import { describe, expect, it } from 'vitest'
import { calculerNote, complet, ecart, formaterNombre } from './grille'

const niveaux = (n) => Array.from({ length: n }, (_, i) => ({ libelle: `N${i}`, descripteur: '', points: i }))
const GRILLE = {
  criteres: [
    { code: 'pertinence', poids: 30, niveaux: niveaux(4) },
    { code: 'rigueur', poids: 30, niveaux: niveaux(4) },
    { code: 'clarte', poids: 20, niveaux: niveaux(4) },
    { code: 'ancrage', poids: 20, niveaux: niveaux(4) },
  ],
}

describe('calculerNote', () => {
  it('somme pondérée arrondie au demi-point', () => {
    expect(calculerNote(GRILLE, { pertinence: 2, rigueur: 2, clarte: 2, ancrage: 3 }, 20)).toBe(14.5)
    expect(calculerNote(GRILLE, { pertinence: 3, rigueur: 3, clarte: 3, ancrage: 3 }, 20)).toBe(20)
    expect(calculerNote(GRILLE, { pertinence: 0, rigueur: 0, clarte: 0, ancrage: 0 }, 20)).toBe(0)
  })

  it('arrondit au pair comme le domaine Python', () => {
    const g = { criteres: [{ code: 'a', poids: 100, niveaux: [{ points: 0 }, { points: 49 }, { points: 80 }] }] }
    // 49/80*10 = 6,125 -> 12,25 demi-points -> 12 ; 61,25 % de 2 = 1,225 -> 2,45 -> 2 (pair)
    expect(calculerNote(g, { a: 1 }, 10)).toBe(6)
    const h = { criteres: [{ code: 'a', poids: 100, niveaux: [{ points: 0 }, { points: 1 }, { points: 8 }] }] }
    expect(calculerNote(h, { a: 1 }, 10)).toBe(1) // 1,25 -> 2,5 demi-points -> 2 (pair) -> 1
    expect(calculerNote(h, { a: 1 }, 14)).toBe(2) // 1,75 -> 3,5 -> 4 (pair) -> 2
  })

  it('null tant que la grille est incomplète ou invalide', () => {
    expect(calculerNote(GRILLE, { pertinence: 2 }, 20)).toBeNull()
    expect(calculerNote(GRILLE, { pertinence: 9, rigueur: 0, clarte: 0, ancrage: 0 }, 20)).toBeNull()
    expect(complet(GRILLE, { pertinence: 1, rigueur: 1, clarte: 1 })).toBe(false)
    expect(complet(GRILLE, { pertinence: 1, rigueur: 1, clarte: 1, ancrage: 0 })).toBe(true)
  })
})

describe('affichage et écarts', () => {
  it('formate à la française', () => {
    expect(formaterNombre(14.5)).toBe('14,5')
    expect(formaterNombre(0.86)).toBe('0,86')
    expect(formaterNombre(null)).toBe('–')
  })

  it('écart de plus d’un niveau entre sources présentes', () => {
    expect(ecart(1, 3)).toBe(true)
    expect(ecart(2, 3)).toBe(false)
    expect(ecart(1, undefined)).toBe(false)
  })
})
