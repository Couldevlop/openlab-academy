import { describe, expect, it } from 'vitest'
import {
  calculerNote,
  complet,
  descripteurChoisi,
  descripteurUtile,
  ecart,
  formaterNombre,
  reussie,
  type Grille,
  type Niveau,
} from './grille'

const niveaux = (n: number): Niveau[] =>
  Array.from({ length: n }, (_, i) => ({ libelle: `N${i}`, descripteur: '', points: i }))
const critere = (code: string, poids: number, n = niveaux(4)) => ({
  code,
  libelle: code,
  description: code,
  poids,
  niveaux: n,
  controles: [],
})
const GRILLE: Grille = {
  criteres: [critere('pertinence', 30), critere('rigueur', 30), critere('clarte', 20), critere('ancrage', 20)],
}
const points = (...p: number[]): Niveau[] => p.map((x) => ({ libelle: '', descripteur: '', points: x }))

describe('calculerNote', () => {
  it('somme pondérée arrondie au demi-point', () => {
    expect(calculerNote(GRILLE, { pertinence: 2, rigueur: 2, clarte: 2, ancrage: 3 }, 20)).toBe(14.5)
    expect(calculerNote(GRILLE, { pertinence: 3, rigueur: 3, clarte: 3, ancrage: 3 }, 20)).toBe(20)
    expect(calculerNote(GRILLE, { pertinence: 0, rigueur: 0, clarte: 0, ancrage: 0 }, 20)).toBe(0)
  })

  it('arrondit le demi-pas au supérieur comme le domaine Python', () => {
    const note = (milieu: number, haut: number, sur = 20) =>
      calculerNote({ criteres: [critere('a', 100, points(0, milieu, haut))] }, { a: 1 }, sur)
    expect(note(41, 80)).toBe(10.5) // 10,25 -> 20,5 demi-points -> 21 -> 10,5
    expect(note(39, 80)).toBe(10) // 9,75 -> 19,5 -> 20 -> 10
    expect(note(1, 8, 10)).toBe(1.5) // 1,25 -> 2,5 -> 3 -> 1,5
    expect(note(49, 80, 10)).toBe(6) // 6,125 -> 12,25 -> 12 -> 6
    expect(note(10249999999, 20000000000)).toBe(10) // 10,249999999 : pas de bascule
    const t: Grille = { criteres: [critere('a', 100, points(0, 1, 3))] }
    expect(calculerNote(t, { a: 1 }, 10)).toBe(3.5) // 3,33 -> 6,67 demi-points -> 7
  })

  it('null tant que la grille est incomplète ou invalide', () => {
    expect(calculerNote(GRILLE, { pertinence: 2 }, 20)).toBeNull()
    expect(calculerNote(GRILLE, { pertinence: 9, rigueur: 0, clarte: 0, ancrage: 0 }, 20)).toBeNull()
    expect(calculerNote(GRILLE, { pertinence: -1, rigueur: 0, clarte: 0, ancrage: 0 }, 20)).toBeNull()
    expect(calculerNote(GRILLE, { pertinence: 1.5, rigueur: 0, clarte: 0, ancrage: 0 }, 20)).toBeNull()
    expect(complet(GRILLE, { pertinence: 1, rigueur: 1, clarte: 1 })).toBe(false)
    expect(complet(GRILLE, { pertinence: 1, rigueur: 1, clarte: 1, ancrage: 0 })).toBe(true)
  })
})

describe('affichage, écarts et réussite', () => {
  it('formate à la française', () => {
    expect(formaterNombre(14.5)).toBe('14,5')
    expect(formaterNombre(0.86)).toBe('0,86')
    expect(formaterNombre(null)).toBe('–')
    expect(formaterNombre(undefined)).toBe('–')
  })

  it('écart de plus d’un niveau entre sources présentes', () => {
    expect(ecart(1, 3)).toBe(true)
    expect(ecart(2, 3)).toBe(false)
    expect(ecart(1, undefined)).toBe(false)
  })

  it('réussite au seuil, comme le domaine Python ; inconnue sans note', () => {
    expect(reussie(10, 10)).toBe(true)
    expect(reussie(9.5, 10)).toBe(false)
    expect(reussie(null, 10)).toBeNull()
  })
})

describe('descripteur du niveau choisi', () => {
  it('celui du niveau choisi, vide sans choix', () => {
    const c = critere('a', 100, [
      { libelle: 'Bas', descripteur: 'Question vague', points: 0 },
      { libelle: 'Haut', descripteur: 'Question chiffrée', points: 1 },
    ])
    expect(descripteurChoisi(c, { a: 1 })).toBe('Question chiffrée')
    expect(descripteurChoisi(c, {})).toBe('')
    expect(descripteurChoisi(c, { a: 5 })).toBe('')
  })

  it('un descripteur qui répète le libellé est tu', () => {
    expect(descripteurUtile({ libelle: 'Excellent', descripteur: 'Excellent ', points: 3 })).toBe('')
    expect(descripteurChoisi(critere('a', 100, points(0, 1)), { a: 1 })).toBe('')
  })
})
