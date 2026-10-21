import { describe, expect, it } from 'vitest'
import { critereRetour, retour } from '../test/fabriques'
import { detailVisible, libelleAutoEvaluation, remarquesPairs, segments } from './retour'

describe('mon retour', () => {
  it('barre de niveaux : atteints, sommet, vides', () => {
    expect(segments(critereRetour('a', 2))).toEqual(['atteint', 'atteint', 'atteint', 'vide'])
    expect(segments(critereRetour('a', 3))).toEqual(['atteint', 'atteint', 'atteint', 'sommet'])
    expect(segments(critereRetour('a', null))).toEqual(['vide', 'vide', 'vide', 'vide'])
  })

  it('remarques des pairs dédoublonnées', () => {
    const r = retour({
      criteres: [critereRetour('a', 1, { pairs: ['Sources ?', 'Bien.'] }), critereRetour('b', 1, { pairs: ['Bien.'] })],
    })
    expect(remarquesPairs(r)).toEqual(['Sources ?', 'Bien.'])
    expect(remarquesPairs(null)).toEqual([])
  })

  it('détail visible seulement pour une note montrée avec ses critères', () => {
    expect(detailVisible(retour({ criteres: [critereRetour('a', 1)] }))).toBe(true)
    expect(detailVisible(retour({ masquee: true, criteres: [critereRetour('a', 1)] }))).toBe(false)
    expect(detailVisible(retour())).toBe(false)
    expect(detailVisible(null)).toBe(false)
  })

  it("libellé de l'auto-évaluation", () => {
    expect(libelleAutoEvaluation(critereRetour('a', 1, { auto_evaluation: 2 }))).toBe('Satisfaisant')
    expect(libelleAutoEvaluation(critereRetour('a', 1))).toBe('')
    expect(libelleAutoEvaluation(critereRetour('a', 1, { auto_evaluation: 9 }))).toBe('')
  })
})
