import { describe, expect, it } from 'vitest'
import { copieEnSouffrance, reglagesEffectifs } from '../test/fabriques'
import { fauxCasUsages } from '../test/faux-ports'
import { ErreurDepot } from './erreurs'

describe('pilotage', () => {
  it('copies en souffrance lues telles que le serveur les rend', async () => {
    const { ports, cas } = fauxCasUsages()
    ports.pilotage.souffrances.mockResolvedValue([copieEnSouffrance('C1')])
    expect(await cas.consulterSouffrances.executer()).toEqual([copieEnSouffrance('C1')])
  })

  it('réglages appliqués : exercice obligatoire, saisies nettoyées, cohorte vide omise', async () => {
    const { ports, cas } = fauxCasUsages()
    ports.pilotage.reglagesEffectifs.mockResolvedValue(reglagesEffectifs())
    await expect(cas.consulterReglagesEffectifs.executer('  ')).rejects.toEqual(
      new ErreurDepot('refus', ["Indiquez l'exercice à examiner."]),
    )
    expect(ports.pilotage.reglagesEffectifs).not.toHaveBeenCalled()
    expect(await cas.consulterReglagesEffectifs.executer(' ASG-1 ', ' COH ')).toEqual(reglagesEffectifs())
    await cas.consulterReglagesEffectifs.executer('ASG-1', ' ')
    await cas.consulterReglagesEffectifs.executer('ASG-1')
    expect(ports.pilotage.reglagesEffectifs.mock.calls).toEqual([
      ['ASG-1', 'COH'],
      ['ASG-1', undefined],
      ['ASG-1', undefined],
    ])
  })
})
