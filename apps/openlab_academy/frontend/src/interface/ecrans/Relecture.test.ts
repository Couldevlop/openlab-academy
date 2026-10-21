import { enableAutoUnmount, flushPromises } from '@vue/test-utils'
import { afterEach, describe, expect, it } from 'vitest'
import { ErreurDepot, TROP_DE_DEMANDES } from '../../application/erreurs'
import type { ResumeRelecture, VueRelecture } from '../../domaine/relecture'
import { resumeRelecture, vueRelecture } from '../../test/fabriques'
import { MAINTENANT, fauxPorts } from '../../test/faux-ports'
import { monterEcran } from '../../test/monter'

const LISTE = [resumeRelecture('R1'), resumeRelecture('R2', { rang: 2 }), resumeRelecture('R3', { exercice: 'ASG-2' })]

async function ouvrir(vue: VueRelecture = vueRelecture(), liste: ResumeRelecture[] = LISTE, chemin = '/relecture/R1') {
  const ports = fauxPorts()
  ports.relecture.mesRelectures.mockResolvedValue(liste)
  ports.relecture.relecture.mockImplementation(async (id) => ({ ...vue, relecture: id }))
  return { ...(await monterEcran(chemin, ports)), ports }
}

enableAutoUnmount(afterEach)

describe('Relecture', () => {
  it('copie anonyme, échéance, progression et consigne', async () => {
    const { w } = await ouvrir()
    expect(w.find('.position').text()).toBe('Relecture 1 sur 3')
    expect(w.find('.surtitre').text()).toMatch(/^Copie anonyme · à relire avant le 3 novembre/)
    expect(w.find('[role="progressbar"]').attributes()).toMatchObject({ 'aria-valuenow': '0', 'aria-valuemax': '2' })
    expect(w.find('.consigne .copie').text()).toBe('Rédigez la question.')
    expect(w.find('.bandeau-alerte').exists()).toBe(false)
    expect(w.findAll('fieldset')).toHaveLength(2)
  })

  it('copie rendue par lien : avertissement sur l’anonymat', async () => {
    const { w } = await ouvrir(vueRelecture({ anonymat_garanti: false, echeance: null }))
    expect(w.find('.surtitre').text()).toBe('Copie rendue par lien')
    expect(w.find('.bandeau-alerte').text()).toContain('jugez le travail, pas la personne')
  })

  it('sans relecture dans l’adresse : la prochaine à faire', async () => {
    const { routeur } = await ouvrir(vueRelecture(), LISTE, '/relecture')
    expect(routeur.currentRoute.value.params.relecture).toBe('R1')
  })

  it('aucune relecture à faire', async () => {
    const { w } = await ouvrir(vueRelecture(), [resumeRelecture('R1', { statut: 'faite' })], '/relecture')
    expect(w.find('.fin h1').text()).toBe('Aucune relecture à faire')
  })

  it('envoi incomplet : chaque manque est signalé, le premier critère incomplet reçoit le focus', async () => {
    const { w, ports } = await ouvrir()
    await w.find('form').trigger('submit')
    await flushPromises()
    expect(ports.relecture.enregistrer).not.toHaveBeenCalled()
    expect(w.findAll('.manque').map((m) => m.text())).toEqual([
      'Choisissez un niveau et ajoutez un conseil.',
      'Choisissez un niveau et ajoutez un conseil.',
    ])
    expect(document.activeElement?.id).toBe('critere-pertinence')
    expect(w.find('#critere-pertinence').attributes('aria-describedby')).toBe('erreur-pertinence')
    await w.findAll('#critere-pertinence button.niveau')[2]!.trigger('click')
    expect(w.find('#critere-pertinence .manque').text()).toBe('Ajoutez un conseil.')
    expect(w.find('#conseil-pertinence').attributes('aria-invalid')).toBe('true')
    await w.find('#conseil-pertinence').setValue('Question précise.')
    expect(w.find('#critere-pertinence .manque').exists()).toBe(false)
    await w.find('form').trigger('submit')
    await flushPromises()
    expect(document.activeElement?.id).toBe('critere-rigueur')
  })

  it('le descripteur du niveau choisi est lisible sans survol', async () => {
    const { w } = await ouvrir()
    const bouton = w.findAll('#critere-pertinence button.niveau')[1]!
    expect(bouton.attributes('aria-describedby')).toBe('descripteur-pertinence-1')
    expect(w.find('#descripteur-pertinence-1').text()).toBe('À consolider (pertinence)')
    expect(w.find('#critere-pertinence .descripteur').exists()).toBe(false)
    await bouton.trigger('click')
    expect(w.find('#critere-pertinence .descripteur').text()).toBe('À consolider (pertinence)')
  })

  it('le brouillon est gardé sur l’appareil et repris à la réouverture', async () => {
    const { w, ports } = await ouvrir()
    await w.findAll('#critere-pertinence button.niveau')[2]!.trigger('click')
    await w.find('#conseil-pertinence').setValue('Question précise.')
    expect(ports.brouillons.lire('R1')).toEqual({
      niveaux: { pertinence: 2 },
      conseils: { pertinence: 'Question précise.' },
      enregistre: MAINTENANT.toISOString(),
    })
    w.unmount()
    const ecran = await monterEcran('/relecture/R1', ports)
    expect(ecran.w.find('#critere-pertinence [aria-pressed="true"]').text()).toBe('Satisfaisant')
    expect((ecran.w.find('#conseil-pertinence').element as HTMLTextAreaElement).value).toBe('Question précise.')
  })

  it('relecture déjà envoyée : pas de formulaire, brouillon oublié', async () => {
    const ports = fauxPorts()
    ports.relecture.mesRelectures.mockResolvedValue(LISTE)
    ports.relecture.relecture.mockResolvedValue(vueRelecture({ statut: 'faite' }))
    ports.brouillons.garder('R1', { niveaux: { pertinence: 1 }, conseils: { pertinence: 'Brouillon partagé' } })
    const { w } = await monterEcran('/relecture/R1', ports)
    expect(w.find('form').exists()).toBe(false)
    expect(w.find('[role="status"]').text()).toBe('Cette relecture est déjà envoyée. Merci !')
    expect(ports.brouillons.lire('R1')).toBeNull()
  })

  async function remplir(w: Awaited<ReturnType<typeof ouvrir>>['w']) {
    for (const code of ['pertinence', 'rigueur']) {
      await w.findAll(`#critere-${code} button.niveau`)[1]!.trigger('click')
      await w.find(`#conseil-${code}`).setValue(`Conseil sur ${code}.`)
    }
  }

  it('envoyer : relecture enregistrée, brouillon oublié, relecture suivante ouverte', async () => {
    const { w, ports, routeur } = await ouvrir()
    ports.relecture.mesRelectures.mockResolvedValue([resumeRelecture('R1', { statut: 'faite' }), resumeRelecture('R2')])
    await remplir(w)
    await w.find('form').trigger('submit')
    await flushPromises()
    expect(ports.relecture.enregistrer).toHaveBeenCalledWith('R1', {
      niveaux: { pertinence: 1, rigueur: 1 },
      conseils: { pertinence: 'Conseil sur pertinence.', rigueur: 'Conseil sur rigueur.' },
    })
    expect(ports.brouillons.lire('R1')).toBeNull()
    expect(routeur.currentRoute.value.params.relecture).toBe('R2')
  })

  it('dernière relecture envoyée : relectures terminées', async () => {
    const { w, ports } = await ouvrir()
    ports.relecture.mesRelectures.mockResolvedValue([resumeRelecture('R1', { statut: 'faite' })])
    await remplir(w)
    await w.find('form').trigger('submit')
    await flushPromises()
    expect(w.find('.fin h1').text()).toBe('Relectures terminées')
  })

  it('limitation de débit : message clair, saisie et brouillon conservés', async () => {
    const { w, ports } = await ouvrir()
    ports.relecture.enregistrer.mockRejectedValue(new ErreurDepot('trop_de_demandes'))
    await remplir(w)
    await w.find('form').trigger('submit')
    await flushPromises()
    expect(w.find('[role="alert"]').text()).toBe(TROP_DE_DEMANDES)
    expect((w.find('#conseil-rigueur').element as HTMLTextAreaElement).value).toBe('Conseil sur rigueur.')
    expect(ports.brouillons.lire('R1')).not.toBeNull()
  })

  it('relecture refusée : message clair', async () => {
    const ports = fauxPorts()
    ports.relecture.mesRelectures.mockResolvedValue(LISTE)
    ports.relecture.relecture.mockRejectedValue(new ErreurDepot('acces_refuse'))
    const { w } = await monterEcran('/relecture/R9', ports)
    expect(w.find('[role="alert"]').text()).toContain("n'existe pas ou ne vous est pas ouvert")
  })
})
