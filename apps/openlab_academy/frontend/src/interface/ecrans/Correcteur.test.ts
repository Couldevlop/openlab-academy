import { enableAutoUnmount, flushPromises } from '@vue/test-utils'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { ErreurDepot, TROP_DE_DEMANDES } from '../../application/erreurs'
import type { VueCopie } from '../../domaine/correction'
import { fileCorrection, vueCopie } from '../../test/fabriques'
import { fauxPorts } from '../../test/faux-ports'
import { monterEcran, touche } from '../../test/monter'

const FILE = fileCorrection(['C1', 'C2', 'C3'], [['C1', 'C3']])

async function ouvrir(copie: VueCopie = vueCopie(), chemin = '/correcteur/C2') {
  const ports = fauxPorts()
  ports.correction.file.mockResolvedValue(FILE)
  ports.correction.copie.mockImplementation(async (id) => ({ ...copie, copie: id }))
  return monterEcran(chemin, ports)
}

enableAutoUnmount(afterEach)
afterEach(() => vi.restoreAllMocks())

describe('Correcteur', () => {
  it('position dans la file, onglet des lots et citation du critère actif surlignée', async () => {
    const { w } = await ouvrir()
    expect(w.find('.position').text()).toBe('Copie 2 sur 3')
    expect(w.find('.onglets').text()).toContain('Lots (1)')
    expect(w.find('mark.citation').element.textContent).toBe('pourquoi les ventes')
    expect(w.find('.note').text()).toBe('– / 20')
    expect(w.find('.surtitre').text()).toBe('Version 1 · à corriger')
    expect(w.find('.consigne .copie').text()).toBe('Rédigez la question.')
  })

  it('sans copie dans l’adresse : la première de la file', async () => {
    const { routeur } = await ouvrir(vueCopie(), '/correcteur')
    expect(routeur.currentRoute.value.params.copie).toBe('C1')
  })

  it('file vide : rien à corriger', async () => {
    const ports = fauxPorts()
    ports.correction.file.mockResolvedValue({ copies: [], lots: [] })
    const { w } = await monterEcran('/correcteur', ports)
    expect(w.find('.vide').text()).toBe('Aucune copie à corriger pour le moment.')
  })

  it('copie refusée : message clair', async () => {
    const ports = fauxPorts()
    ports.correction.file.mockRejectedValue(new ErreurDepot('hors_ligne'))
    ports.correction.copie.mockRejectedValue(new ErreurDepot('acces_refuse'))
    const { w } = await monterEcran('/correcteur/C9', ports)
    expect(w.find('[role="alert"]').text()).toContain("n'existe pas ou ne vous est pas ouvert")
  })

  it('touches 1 à 4 : niveau du critère actif, puis critère suivant ; note recalculée et verdict', async () => {
    const { w } = await ouvrir()
    await touche('3')
    expect(w.find('mark.citation').element.textContent).toBe('Bouaké')
    await touche('4')
    expect(w.find('.note').text()).toBe('16,5 / 20')
    expect(w.find('.verdict').text()).toBe('Validé au seuil de 10')
    expect(w.findAll('[aria-pressed="true"]').map((b) => b.find('span').text())).toEqual(['Satisfaisant', 'Excellent'])
    await touche('1')
    await touche('1')
    expect(w.find('.verdict').text()).toBe('Non validé au seuil de 10')
  })

  it('touche maintenue, composition, modificateur ou touche hors grille : aucun effet', async () => {
    const { w } = await ouvrir()
    await touche('3', { repeat: true })
    await touche('3', { isComposing: true })
    await touche('3', { ctrlKey: true })
    await touche('7')
    await touche('x')
    expect(w.findAll('[aria-pressed="true"]')).toHaveLength(0)
  })

  it('J et K : copie suivante et précédente, jamais pendant la saisie ni en touche maintenue', async () => {
    const { w, routeur } = await ouvrir()
    w.find('#commentaire-general').element.dispatchEvent(new KeyboardEvent('keydown', { key: 'j', bubbles: true }))
    await flushPromises()
    expect(routeur.currentRoute.value.params.copie).toBe('C2')
    await touche('j', { repeat: true })
    expect(routeur.currentRoute.value.params.copie).toBe('C2')
    await touche('j')
    expect(routeur.currentRoute.value.params.copie).toBe('C3')
    await touche('j') // dernière copie : on reste
    expect(routeur.currentRoute.value.params.copie).toBe('C3')
    await touche('k')
    expect(routeur.currentRoute.value.params.copie).toBe('C2')
  })

  it('boutons précédente et suivante', async () => {
    const { w, routeur } = await ouvrir()
    await w.findAll('.navigation button')[1]!.trigger('click')
    await flushPromises()
    expect(routeur.currentRoute.value.params.copie).toBe('C3')
    await w.findAll('.navigation button')[0]!.trigger('click')
    await flushPromises()
    expect(routeur.currentRoute.value.params.copie).toBe('C2')
  })

  it("montre le signalement d'injection, la délégation et le dépôt sûr", async () => {
    const { w } = await ouvrir(
      vueCopie({
        ia: null,
        signalement: "copie signalée : tentative d'instruction à l'IA",
        au_nom_de: 'koné@exemple.ci',
        source_url: 'https://github.com/a/b',
        commit: 'abc123',
        controles: ['longueur faible'],
        pairs: { mediane: { pertinence: 1 }, nombre: 3, commentaires: [] },
      }),
    )
    expect(w.find('.signalement').text()).toContain("copie signalée : tentative d'instruction à l'IA")
    expect(w.find('.contexte').text()).toContain('Contrôles automatiques : longueur faible.')
    expect(w.find('.contexte').text()).toContain('Relue par 3 pairs.')
    expect(w.find('.contexte').text()).toContain('au nom de koné@exemple.ci')
    expect(w.find('.contexte a').attributes('href')).toBe('https://github.com/a/b')
    expect(w.find('.contexte').text()).toContain('version abc123')
  })

  it('un lien de dépôt non http(s) n’est jamais rendu', async () => {
    const { w } = await ouvrir(vueCopie({ source_url: 'javascript:alert(1)' }))
    expect(w.find('.contexte a').exists()).toBe(false)
  })

  it('le formateur retrouve sa correction déjà enregistrée', async () => {
    const formateur = {
      niveaux: { pertinence: 1, rigueur: 2 },
      commentaires: { general: 'Bien.' },
      auteur: 'f',
      au_nom_de: null,
    }
    const { w } = await ouvrir(vueCopie({ formateur }))
    expect((w.find('#commentaire-general').element as HTMLTextAreaElement).value).toBe('Bien.')
    expect(w.find('.note').text()).toBe('10 / 20')
  })

  it('enregistrer : correction gardée, file rechargée', async () => {
    const { w, ports } = await ouvrir()
    await touche('3')
    await touche('4')
    await w.find('[data-critere="rigueur"] textarea').setValue('Sources ?')
    await w.findAll('.actions .bouton')[0]!.trigger('click')
    await flushPromises()
    expect(ports.correction.corriger).toHaveBeenCalledWith({
      copie: 'C2',
      niveaux: { pertinence: 2, rigueur: 3 },
      commentaires: { rigueur: 'Sources ?', general: '' },
    })
    expect(w.find('[role="status"]').text()).toBe(
      "Correction enregistrée. Elle n'est pas encore visible par l'apprenant.",
    )
    expect(ports.correction.file).toHaveBeenCalledTimes(2)
  })

  it('publier enregistre la correction puis publie, et passe à la copie suivante', async () => {
    const { w, routeur, ports } = await ouvrir()
    ports.correction.publier.mockResolvedValue(16.5)
    await touche('3')
    await touche('4')
    await w.find('#commentaire-general').setValue('Très bonne reformulation.')
    await w.find('.bouton-principal').trigger('click')
    await flushPromises()
    expect(ports.correction.corriger).toHaveBeenCalledWith({
      copie: 'C2',
      niveaux: { pertinence: 2, rigueur: 3 },
      commentaires: { general: 'Très bonne reformulation.' },
    })
    expect(ports.correction.publier).toHaveBeenCalledWith('C2')
    expect(routeur.currentRoute.value.params.copie).toBe('C3')
    expect(w.find('[role="status"]').text()).toBe('Note publiée : 16,5 / 20.')
  })

  it('publier la dernière copie de la file : la copie reste affichée', async () => {
    const { w, routeur, ports } = await ouvrir()
    ports.correction.file.mockResolvedValue(fileCorrection(['C2']))
    ports.correction.publier.mockResolvedValue(12)
    await touche('2')
    await touche('3')
    await w.find('.bouton-principal').trigger('click')
    await flushPromises()
    expect(routeur.currentRoute.value.params.copie).toBe('C2')
    expect(w.find('[role="status"]').text()).toBe('Note publiée : 12 / 20.')
  })

  it('publication en échec : la copie reste gardée contre une sortie sans confirmation', async () => {
    const { w, routeur, ports } = await ouvrir()
    ports.correction.publier.mockRejectedValue(new ErreurDepot('refus', ['Publication refusée.']))
    await touche('3')
    await touche('4')
    await w.find('.bouton-principal').trigger('click')
    await flushPromises()
    expect(w.find('[role="alert"]').text()).toBe('Publication refusée.')
    const confirmer = vi.spyOn(window, 'confirm').mockReturnValue(false)
    await touche('j')
    expect(confirmer).toHaveBeenCalledTimes(1)
    expect(routeur.currentRoute.value.params.copie).toBe('C2')
  })

  it('limitation de débit : message clair, saisie conservée', async () => {
    const { w, ports } = await ouvrir()
    ports.correction.corriger.mockRejectedValue(new ErreurDepot('trop_de_demandes'))
    await touche('1')
    await touche('2')
    await w.findAll('.actions .bouton')[0]!.trigger('click')
    await flushPromises()
    expect(w.find('[role="alert"]').text()).toBe(TROP_DE_DEMANDES)
    expect(w.findAll('[aria-pressed="true"]')).toHaveLength(2)
  })

  it('modifications non enregistrées : confirmation avant de changer de copie (J, onglet, URL)', async () => {
    const { routeur } = await ouvrir()
    const confirmer = vi.spyOn(window, 'confirm').mockReturnValue(false)
    await touche('2')
    await touche('j')
    expect(confirmer).toHaveBeenCalledTimes(1)
    expect(routeur.currentRoute.value.params.copie).toBe('C2')
    await routeur.push({ name: 'correcteur' }) // onglet « À corriger » : même route, autre paramètre
    expect(confirmer).toHaveBeenCalledTimes(2)
    expect(routeur.currentRoute.value.params.copie).toBe('C2')
    await routeur.push('/correcteur/C1') // retour arrière ou lien direct
    expect(routeur.currentRoute.value.params.copie).toBe('C2')
    await routeur.push({ name: 'lots' }) // autre écran
    expect(routeur.currentRoute.value.name).toBe('correcteur')
    confirmer.mockReturnValue(true)
    await touche('j')
    expect(confirmer).toHaveBeenCalledTimes(5)
    expect(routeur.currentRoute.value.params.copie).toBe('C3')
  })

  it('un commentaire saisi compte comme une modification', async () => {
    const { w, routeur } = await ouvrir()
    const confirmer = vi.spyOn(window, 'confirm').mockReturnValue(false)
    await w.find('[data-critere="pertinence"] textarea').setValue('À revoir')
    await touche('j')
    await w.find('#commentaire-general').setValue('Bien.')
    await touche('j')
    expect(confirmer).toHaveBeenCalledTimes(2)
    expect(routeur.currentRoute.value.params.copie).toBe('C2')
  })

  it('sans modification : on change de copie sans confirmation', async () => {
    const { routeur } = await ouvrir()
    const confirmer = vi.spyOn(window, 'confirm')
    await touche('j')
    expect(confirmer).not.toHaveBeenCalled()
    expect(routeur.currentRoute.value.params.copie).toBe('C3')
  })

  it('fermeture ou rechargement de la page retenus tant que la copie est modifiée', async () => {
    const { w, ports } = await ouvrir()
    const quitter = () => {
      const e = new Event('beforeunload', { cancelable: true })
      window.dispatchEvent(e)
      return e.defaultPrevented
    }
    expect(quitter()).toBe(false)
    await touche('2')
    expect(quitter()).toBe(true)
    await touche('3')
    await w.findAll('.actions .bouton')[0]!.trigger('click')
    await flushPromises()
    expect(ports.correction.corriger).toHaveBeenCalled()
    expect(quitter()).toBe(false)
  })

  it("copie signalée : la proposition de l'IA est écartée de la grille et de la copie", async () => {
    const ia = { ...vueCopie().ia!, justifications: { pertinence: 'Justification piégée' } }
    const { w } = await ouvrir(vueCopie({ ia, signalement: "copie signalée : tentative d'instruction à l'IA" }))
    expect(w.find('.signalement').exists()).toBe(true)
    expect(w.findAll('.puce').map((p) => p.text())).not.toContain('IA')
    expect(w.find('.ia-ligne').exists()).toBe(false)
    expect(w.find('mark.citation').exists()).toBe(false)
    expect(w.text()).not.toContain('Justification piégée')
  })

  it('un juré enregistre sa note mais ne publie pas', async () => {
    const { w, ports } = await ouvrir(vueCopie({ role: 'jury', jury: { mediane: {}, nombre: 1, attendus: 3 } }))
    expect(w.findAll('.actions button').map((b) => b.text())).toEqual(['Enregistrer ma note'])
    expect(w.find('.contexte').text()).toContain('Vous notez comme juré (1 note sur 3).')
    await touche('1')
    await touche('2')
    await w.find('.actions .bouton').trigger('click')
    await flushPromises()
    expect(w.find('[role="status"]').text()).toBe('Votre note de juré est enregistrée.')
    expect(ports.correction.publier).not.toHaveBeenCalled()
  })
})
