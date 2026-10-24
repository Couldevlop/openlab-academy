import { enableAutoUnmount, flushPromises, type VueWrapper } from '@vue/test-utils'
import { afterEach, describe, expect, it } from 'vitest'
import { ErreurDepot } from '../../application/erreurs'
import { copieEnSouffrance, reglagesEffectifs } from '../../test/fabriques'
import { fauxPorts, type FauxPorts } from '../../test/faux-ports'
import { monterEcran } from '../../test/monter'

const net = (w: Pick<VueWrapper, 'text'>) => w.text().replace(/\s+/g, ' ').trim()
const SUPERVISEUR = { intendance: false, finances: false, pilotage: true }

function portsSuperviseur(): FauxPorts {
  const ports = fauxPorts()
  ports.session.droits.mockReturnValue(SUPERVISEUR)
  return ports
}

enableAutoUnmount(afterEach)

describe('Pilotage', () => {
  it('réservé aux superviseurs : aucun appel sans le droit', async () => {
    const { w, ports } = await monterEcran('/pilotage')
    expect(document.title).toBe('Pilotage · OpenLab Academy')
    expect(w.find('.reserve').text()).toContain('réservé au super administrateur et au responsable pédagogique')
    expect(ports.pilotage.souffrances).not.toHaveBeenCalled()
    expect(w.find('.souffrances').exists()).toBe(false)
  })

  it('copies en souffrance : depuis quand, à qui, action prévue et temps restant, lien vers le correcteur', async () => {
    const ports = portsSuperviseur()
    ports.pilotage.souffrances.mockResolvedValue([
      copieEnSouffrance('C1', { reste_heures: 12 }),
      copieEnSouffrance('C2', { action: 'rien', reste_heures: null, escalade_a: '', cohorte: '', depuis: null }),
    ])
    const { w } = await monterEcran('/pilotage', ports)
    expect(w.find('.nav-agents').text()).toContain('Pilotage')
    const lignes = w.findAll('.souffrances tbody tr')
    expect(lignes).toHaveLength(2)
    expect(lignes[0]!.find('a').attributes('href')).toBe('/correcteur/C1')
    expect(net(lignes[0]!.find('.qui .discret'))).toBe('c1@exemple.ci · ASG-1 · COH')
    expect(lignes[0]!.find('time').attributes('datetime')).toBe('2026-11-01T08:00:00Z')
    expect(lignes[0]!.find('.escalade').text()).toBe('responsable@exemple.ci')
    expect(lignes[0]!.find('.reste').text()).toBe('dans 12 h')
    expect(lignes[0]!.find('.reste').classes()).toContain('urgent')
    expect(net(lignes[1]!.find('.qui .discret'))).toBe('c2@exemple.ci · ASG-1')
    expect(lignes[1]!.find('time').text()).toBe('—')
    expect(lignes[1]!.find('.escalade').text()).toBe('—')
    expect(lignes[1]!.text()).toContain('Attend une décision (rappel quotidien)')
    expect(lignes[1]!.find('.reste').exists()).toBe(false)
  })

  it('aucune copie en souffrance ; refus du serveur affiché', async () => {
    const { w } = await monterEcran('/pilotage', portsSuperviseur())
    expect(w.find('.vide').text()).toBe('Aucune copie en souffrance : la chaîne suit son cours.')
    w.unmount()
    const ports = portsSuperviseur()
    ports.pilotage.souffrances.mockRejectedValue(new ErreurDepot('acces_refuse'))
    const refus = await monterEcran('/pilotage', ports)
    expect(refus.w.find('[role="alert"]').text()).toBe("Cet élément n'existe pas ou ne vous est pas ouvert.")
  })

  it('réglages appliqués : chaque valeur avec son origine, et l’équipe avec sa provenance', async () => {
    const ports = portsSuperviseur()
    ports.pilotage.reglagesEffectifs.mockResolvedValue(reglagesEffectifs())
    const { w } = await monterEcran('/pilotage', ports)
    await w.find('#pilotage-exercice').setValue(' ASG-1 ')
    await w.find('#pilotage-cohorte').setValue('COH')
    await w.find('form.recherche').trigger('submit')
    await flushPromises()
    expect(ports.pilotage.reglagesEffectifs).toHaveBeenCalledWith('ASG-1', 'COH')
    expect(net(w.find('.cible'))).toBe('Livrable · exercice ASG-1 · cohorte COH')
    const lignes = w.findAll('.reglages:not(.equipe) tbody tr').map((l) => l.findAll('th, td').map((c) => c.text()))
    expect(lignes[1]).toEqual(['Note sur', '10', 'cohorte COH'])
    expect(lignes[3]).toEqual([
      'Étape : Formateur',
      'Active · délai 48 h · à l’expiration : escalader',
      'type livrable',
    ])
    const equipe = w.findAll('.equipe tr').map((l) => l.findAll('th, td').map((c) => c.text()))
    expect(equipe).toEqual([
      ['Titulaires', 'formateur@exemple.ci', 'cohorte COH'],
      ['Suppléants', '—', ''],
      ['Responsable', 'responsable@exemple.ci', 'réglages'],
    ])
  })

  it('réglages : exercice manquant refusé sans appel, refus du serveur affiché', async () => {
    const ports = portsSuperviseur()
    const { w } = await monterEcran('/pilotage', ports)
    await w.find('#pilotage-exercice').setValue('   ')
    await w.find('form.recherche').trigger('submit')
    await flushPromises()
    expect(w.find('.bandeau-erreur').text()).toBe("Indiquez l'exercice à examiner.")
    expect(ports.pilotage.reglagesEffectifs).not.toHaveBeenCalled()
    ports.pilotage.reglagesEffectifs.mockRejectedValue(new ErreurDepot('refus', ['exercice sans grille OpenLab']))
    await w.find('#pilotage-exercice').setValue('X')
    await w.find('form.recherche').trigger('submit')
    await flushPromises()
    expect(w.find('.bandeau-erreur').text()).toBe('exercice sans grille OpenLab')
    expect(w.find('.cible').exists()).toBe(false)
  })

  it('depuis une copie en souffrance : réglages de son exercice dans sa cohorte, sans cohorte s’il n’y en a pas', async () => {
    const ports = portsSuperviseur()
    ports.pilotage.souffrances.mockResolvedValue([copieEnSouffrance('C1', { cohorte: '' })])
    ports.pilotage.reglagesEffectifs.mockResolvedValue(reglagesEffectifs())
    const { w } = await monterEcran('/pilotage', ports)
    await w.find('.souffrances .bouton').trigger('click')
    await flushPromises()
    expect(ports.pilotage.reglagesEffectifs).toHaveBeenCalledWith('ASG-1', undefined)
    expect((w.find('#pilotage-exercice').element as HTMLInputElement).value).toBe('ASG-1')
    expect(net(w.find('.cible'))).toBe('Livrable · exercice ASG-1')
  })
})
