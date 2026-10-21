import { describe, expect, it } from 'vitest'
import { elementFile } from '../test/fabriques'
import { lotsAffiches } from './lots'

describe('lots affichés', () => {
  it("chaque lot porte ses copies, l'exercice et la plus faible confiance", () => {
    const file = {
      copies: [elementFile('C1', { confiance: 0.9 }), elementFile('C3', { confiance: 0.82 })],
      lots: [['C1', 'C3']],
    }
    const [lot] = lotsAffiches(file)
    expect(lot).toMatchObject({ ids: ['C1', 'C3'], exercice: 'ASG-1', confiance: 0.82 })
    expect(lot?.copies.map((c) => c.copie)).toEqual(['C1', 'C3'])
  })

  it('une copie absente de la file reste listée par son identifiant ; confiance inconnue comptée 1', () => {
    const [lot] = lotsAffiches({ copies: [elementFile('C1')], lots: [['C9', 'C1']] })
    expect(lot).toMatchObject({ exercice: '', confiance: 1 })
    expect(lot?.copies[0]).toEqual({ copie: 'C9' })
  })

  it('aucun lot', () => {
    expect(lotsAffiches({ copies: [], lots: [] })).toEqual([])
  })
})
