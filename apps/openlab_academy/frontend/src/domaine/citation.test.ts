import { describe, expect, it } from 'vitest'
import { localiserCitation, normaliser } from './citation'

describe('normaliser', () => {
  it('réduit les blancs', () => {
    expect(normaliser('  a \n\t b ')).toBe('a b')
    expect(normaliser(undefined)).toBe('')
    expect(normaliser(null)).toBe('')
  })
})

describe('localiserCitation', () => {
  it('trouve la citation dans un seul texte, blancs normalisés', () => {
    expect(localiserCitation(['Je cherche pourquoi les\nventes baissent'], 'pourquoi les  ventes')).toEqual([
      { texte: 0, de: 11, a: 30 },
    ])
  })

  it('traverse plusieurs textes (mise en forme) et ignore les morceaux faits de blancs', () => {
    expect(localiserCitation(['un ', 'point clé', ' ici'], 'point clé ici')).toEqual([
      { texte: 1, de: 0, a: 9 },
      { texte: 2, de: 0, a: 4 },
    ])
    expect(localiserCitation(['a', '\n', 'b'], 'a b')).toEqual([
      { texte: 0, de: 0, a: 1 },
      { texte: 2, de: 0, a: 1 },
    ])
  })

  it('les blancs de tête sont ignorés', () => {
    expect(localiserCitation(['  \n  début'], 'début')).toEqual([{ texte: 0, de: 5, a: 10 }])
  })

  it('aucune plage quand la citation est absente ou vide', () => {
    expect(localiserCitation(['texte'], 'introuvable')).toBeNull()
    expect(localiserCitation(['texte'], '   ')).toBeNull()
    expect(localiserCitation([], 'x')).toBeNull()
  })

  it('compte en unités UTF-16, comme les nœuds texte', () => {
    expect(localiserCitation(['😀 fin'], 'fin')).toEqual([{ texte: 0, de: 3, a: 6 }])
  })
})
