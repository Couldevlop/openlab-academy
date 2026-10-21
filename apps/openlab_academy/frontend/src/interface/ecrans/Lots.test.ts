import { enableAutoUnmount, flushPromises } from '@vue/test-utils'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { ErreurDepot, TROP_DE_DEMANDES } from '../../application/erreurs'
import { elementFile } from '../../test/fabriques'
import { fauxPorts } from '../../test/faux-ports'
import { monterEcran } from '../../test/monter'

const FILE = {
  copies: [elementFile('C1', { confiance: 0.92 }), elementFile('C3', { confiance: 0.86, version: 2 })],
  lots: [['C1', 'C3']],
}

async function ouvrir(chemin = '/lots') {
  const ports = fauxPorts()
  ports.correction.file.mockResolvedValue(FILE)
  return monterEcran(chemin, ports)
}

enableAutoUnmount(afterEach)
afterEach(() => vi.restoreAllMocks())

describe('Lots', () => {
  it('chaque lot : copies, exercice, plus faible confiance ; filtre d’exercice gardé', async () => {
    const { w, ports } = await ouvrir('/lots?exercice=ASG-1')
    expect(ports.correction.file).toHaveBeenCalledWith('ASG-1')
    expect(w.find('.lot h2').text()).toBe('Lot de 2 copies')
    expect(w.find('.lot-tete .discret').text()).toBe('confiance IA ≥ 0,86')
    expect(w.find('.exercice').text()).toBe('Exercice ASG-1')
    expect(w.findAll('.lot li').map((li) => li.text())).toEqual(['Copie C1 · version 1', 'Copie C3 · version 2'])
    expect(w.find('.lot li a').attributes('href')).toBe('/correcteur/C1?exercice=ASG-1')
    expect(w.find('.onglets').text()).toContain('Lots (1)')
  })

  it('valider le lot sans publier', async () => {
    const { w, ports } = await ouvrir()
    ports.correction.validerLot.mockResolvedValue({ copies: ['C1', 'C3'], publiees: [] })
    await w.find('.actions .bouton').trigger('click')
    await flushPromises()
    expect(ports.correction.validerLot).toHaveBeenCalledWith(['C1', 'C3'], false)
    expect(w.find('[role="status"]').text()).toBe('2 copies validées. Publiez-les depuis chaque copie.')
    expect(ports.correction.file).toHaveBeenCalledTimes(2)
  })

  it('valider et publier, après confirmation', async () => {
    const { w, ports } = await ouvrir()
    ports.correction.validerLot.mockResolvedValue({ copies: ['C1', 'C3'], publiees: ['C1', 'C3'] })
    const confirmer = vi.spyOn(window, 'confirm').mockReturnValueOnce(false).mockReturnValue(true)
    await w.find('.bouton-principal').trigger('click')
    expect(ports.correction.validerLot).not.toHaveBeenCalled()
    await w.find('.bouton-principal').trigger('click')
    await flushPromises()
    expect(confirmer).toHaveBeenCalledWith('Valider et publier les notes de 2 copies ?')
    expect(ports.correction.validerLot).toHaveBeenCalledWith(['C1', 'C3'], true)
    expect(w.find('[role="status"]').text()).toBe('2 notes validées et publiées.')
  })

  it('un seul envoi à la fois', async () => {
    const { w, ports } = await ouvrir()
    ports.correction.validerLot.mockReturnValue(new Promise(() => undefined))
    await w.find('.actions .bouton').trigger('click')
    await w.find('.actions .bouton').trigger('click')
    expect(ports.correction.validerLot).toHaveBeenCalledOnce()
  })

  it('limitation de débit : message clair', async () => {
    const { w, ports } = await ouvrir()
    ports.correction.validerLot.mockRejectedValue(new ErreurDepot('trop_de_demandes'))
    await w.find('.actions .bouton').trigger('click')
    await flushPromises()
    expect(w.find('[role="alert"]').text()).toBe(TROP_DE_DEMANDES)
  })

  it('aucun lot ; file illisible', async () => {
    const ports = fauxPorts()
    ports.correction.file.mockResolvedValue({ copies: [], lots: [] })
    const { w } = await monterEcran('/lots', ports)
    expect(w.find('.vide').text()).toBe('Aucun lot à valider pour le moment.')
    const panne = fauxPorts()
    panne.correction.file.mockRejectedValue(new ErreurDepot('hors_ligne'))
    const ecran = await monterEcran('/lots', panne)
    expect(ecran.w.find('[role="alert"]').text()).toContain('Le serveur ne répond pas.')
  })
})
