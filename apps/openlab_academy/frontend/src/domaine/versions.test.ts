import { describe, expect, it } from 'vitest'
import { comparerTextes, libelleResume, resumerDiff } from './versions'

describe('comparaison entre versions', () => {
  it('lignes identiques, retirées et ajoutées, dans l’ordre du texte', () => {
    const diff = comparerTextes('Titre\nAncienne idée\nConclusion', 'Titre\nNouvelle idée\nConclusion\nAnnexe')
    expect(diff).toEqual([
      { sorte: 'egal', texte: 'Titre' },
      { sorte: 'retrait', texte: 'Ancienne idée' },
      { sorte: 'ajout', texte: 'Nouvelle idée' },
      { sorte: 'egal', texte: 'Conclusion' },
      { sorte: 'ajout', texte: 'Annexe' },
    ])
    expect(resumerDiff(diff)).toEqual({ ajouts: 2, retraits: 1 })
  })

  it('textes vides, fins de ligne Windows et lignes restantes de l’ancienne version', () => {
    expect(comparerTextes('', '')).toEqual([])
    expect(comparerTextes('', 'a')).toEqual([{ sorte: 'ajout', texte: 'a' }])
    expect(comparerTextes('a\r\nb\rc', 'a')).toEqual([
      { sorte: 'egal', texte: 'a' },
      { sorte: 'retrait', texte: 'b' },
      { sorte: 'retrait', texte: 'c' },
    ])
    expect(comparerTextes('x\na', 'a\ny')).toEqual([
      { sorte: 'retrait', texte: 'x' },
      { sorte: 'egal', texte: 'a' },
      { sorte: 'ajout', texte: 'y' },
    ])
  })

  it('résumé en toutes lettres', () => {
    expect(libelleResume({ ajouts: 0, retraits: 0 })).toBe('Aucune différence')
    expect(libelleResume({ ajouts: 1, retraits: 0 })).toBe('1 ligne ajoutée')
    expect(libelleResume({ ajouts: 2, retraits: 3 })).toBe('2 lignes ajoutées, 3 lignes retirées')
    expect(libelleResume({ ajouts: 0, retraits: 1 })).toBe('1 ligne retirée')
  })
})
