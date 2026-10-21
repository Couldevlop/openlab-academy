import { describe, expect, it } from 'vitest'
import { retour } from '../test/fabriques'
import { fauxCasUsages } from '../test/faux-ports'

describe('mon retour', () => {
  it('consulter le retour de sa copie', async () => {
    const { ports, cas } = fauxCasUsages()
    const r = retour({ note: 15, note_sur: 20 })
    ports.retour.monRetour.mockResolvedValue(r)
    expect(await cas.consulterRetour.executer('C1')).toBe(r)
    expect(ports.retour.monRetour).toHaveBeenCalledWith('C1')
  })
})
