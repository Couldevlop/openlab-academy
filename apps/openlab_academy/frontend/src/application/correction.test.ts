import { describe, expect, it } from 'vitest'
import { ErreurDepot } from './erreurs'
import { fileCorrection, vueCopie } from '../test/fabriques'
import { fauxCasUsages } from '../test/faux-ports'

const SAISIE = { niveaux: { pertinence: 2, rigueur: 3 }, commentaires: { rigueur: 'Sources ?' }, general: 'Bien.' }
const CHARGE = {
  copie: 'C2',
  niveaux: { pertinence: 2, rigueur: 3 },
  commentaires: { rigueur: 'Sources ?', general: 'Bien.' },
}

describe('correction', () => {
  it('charger la file, filtrée par exercice ou non', async () => {
    const { ports, cas } = fauxCasUsages()
    const file = fileCorrection(['C1', 'C2'], [['C1', 'C2']])
    ports.correction.file.mockResolvedValue(file)
    expect(await cas.consulterFile.executer('ASG-1')).toBe(file)
    expect(await cas.consulterFile.executer()).toBe(file)
    expect(ports.correction.file.mock.calls).toEqual([['ASG-1'], [undefined]])
  })

  it('ouvrir une copie à corriger', async () => {
    const { ports, cas } = fauxCasUsages()
    const vue = vueCopie()
    ports.correction.copie.mockResolvedValue(vue)
    expect(await cas.ouvrirCopie.executer('C2')).toBe(vue)
    expect(ports.correction.copie).toHaveBeenCalledWith('C2')
  })

  it('enregistrer envoie niveaux et commentaires, général compris', async () => {
    const { ports, cas } = fauxCasUsages()
    await cas.enregistrerCorrection.executer('C2', SAISIE)
    expect(ports.correction.corriger).toHaveBeenCalledWith(CHARGE)
  })

  it('publier enregistre la saisie puis publie, et rend la note', async () => {
    const { ports, cas } = fauxCasUsages()
    ports.correction.publier.mockResolvedValue(16.5)
    expect(await cas.publierNote.executer('C2', SAISIE)).toBe(16.5)
    expect(ports.correction.corriger).toHaveBeenCalledWith(CHARGE)
    expect(ports.correction.publier).toHaveBeenCalledWith('C2')
    expect(ports.correction.corriger.mock.invocationCallOrder[0]).toBeLessThan(
      ports.correction.publier.mock.invocationCallOrder[0]!,
    )
  })

  it("rien n'est publié si l'enregistrement échoue", async () => {
    const { ports, cas } = fauxCasUsages()
    ports.correction.corriger.mockRejectedValue(new ErreurDepot('trop_de_demandes'))
    await expect(cas.publierNote.executer('C2', SAISIE)).rejects.toMatchObject({ sorte: 'trop_de_demandes' })
    expect(ports.correction.publier).not.toHaveBeenCalled()
  })

  it('valider un lot, avec ou sans publication', async () => {
    const { ports, cas } = fauxCasUsages()
    ports.correction.validerLot.mockResolvedValue({ copies: ['C1', 'C3'], publiees: [] })
    expect(await cas.validerLot.executer(['C1', 'C3'], false)).toEqual({ copies: ['C1', 'C3'], publiees: [] })
    expect(ports.correction.validerLot).toHaveBeenCalledWith(['C1', 'C3'], false)
  })
})
