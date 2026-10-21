import { enableAutoUnmount, flushPromises, mount } from '@vue/test-utils'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { createMemoryHistory } from 'vue-router'
import { TROP_DE_DEMANDES } from '../lib/api'
import { creerRouteur } from '../routeur'
import App from '../App.vue'

const lire = vi.fn()
const ecrire = vi.fn()
vi.mock('../lib/api', async (original) => ({
  ...(await original()), lire: (...a) => lire(...a), ecrire: (...a) => ecrire(...a),
}))

const LIBELLES = ['Insuffisant', 'À consolider', 'Satisfaisant', 'Excellent']
const critere = (code, poids) => ({
  code, libelle: code, description: code, poids, controles: [],
  niveaux: LIBELLES.map((l, i) => ({ libelle: l, descripteur: l, points: i })),
})
const COPIE = {
  copie: 'C2', apprenant: 'a@x.ci', exercice: 'ASG-1', cohorte: 'COH', titre: 'La baisse des ventes', version: 1,
  statut: 'a_corriger', etape: 'formateur', echeance: null, role: 'formateur', au_nom_de: null, note_sur: 20,
  seuil_reussite: 10, contenu: 'Je chercherais pourquoi les ventes baissent à Bouaké.', source_url: '', commit: '',
  consigne: 'Rédigez la question.', grille: { criteres: [critere('pertinence', 50), critere('rigueur', 50)] },
  auto_evaluation: null, controles: [], ia: { niveaux: { pertinence: 2, rigueur: 2 }, justifications: {},
    citations: { pertinence: 'pourquoi les ventes', rigueur: 'Bouaké' }, confiance: 0.9 },
  pairs: { mediane: {}, nombre: 0, commentaires: [] }, jury: { mediane: {}, nombre: 0, attendus: 0 },
  formateur: null, ecarts: [], signalement: '',
}
const FILE = { copies: ['C1', 'C2', 'C3'].map((copie) => ({ copie })), lots: [['C1', 'C3']] }

async function ouvrir(copie = COPIE) {
  lire.mockImplementation(async (methode) => (methode === 'file_correction' ? FILE : copie))
  const routeur = creerRouteur(createMemoryHistory())
  await routeur.push('/correcteur/C2')
  const w = mount(App, { global: { plugins: [routeur] }, attachTo: document.body }) // sous <RouterView>, comme en vrai
  await flushPromises()
  return { w, routeur }
}

const touche = async (key) => {
  window.dispatchEvent(new KeyboardEvent('keydown', { key }))
  await flushPromises()
}

enableAutoUnmount(afterEach)

describe('Correcteur', () => {
  beforeEach(() => {
    lire.mockReset()
    ecrire.mockReset()
  })

  it('position dans la file, onglet des lots et citation du critère actif surlignée', async () => {
    const { w } = await ouvrir()
    expect(w.find('.position').text()).toBe('Copie 2 sur 3')
    expect(w.find('.onglets').text()).toContain('Lots (1)')
    expect(w.find('mark.citation').element.textContent).toBe('pourquoi les ventes')
    expect(w.find('.note').text()).toBe('– / 20')
  })

  it('touches 1 à 4 : niveau du critère actif, puis critère suivant ; note recalculée', async () => {
    const { w } = await ouvrir()
    await touche('3')
    expect(w.find('mark.citation').element.textContent).toBe('Bouaké')
    await touche('4')
    expect(w.find('.note').text()).toBe('16,5 / 20')
    expect(w.findAll('[aria-pressed="true"]').map((b) => b.find('span').text())).toEqual(['Satisfaisant', 'Excellent'])
  })

  it('J et K : copie suivante et précédente, jamais pendant la saisie', async () => {
    const { w, routeur } = await ouvrir()
    w.find('#commentaire-general').element.dispatchEvent(new KeyboardEvent('keydown', { key: 'j', bubbles: true }))
    await flushPromises()
    expect(routeur.currentRoute.value.params.copie).toBe('C2')
    await touche('j')
    expect(routeur.currentRoute.value.params.copie).toBe('C3')
    await touche('k')
    expect(routeur.currentRoute.value.params.copie).toBe('C2')
  })

  it("montre le signalement d'injection porté par la copie", async () => {
    const { w } = await ouvrir({ ...COPIE, ia: null, signalement: "copie signalée : tentative d'instruction à l'IA" })
    expect(w.find('.signalement').text()).toContain("copie signalée : tentative d'instruction à l'IA")
  })

  it('publier enregistre la correction puis publie, et passe à la copie suivante', async () => {
    const { w, routeur } = await ouvrir()
    ecrire.mockImplementation(async (methode) => (methode === 'publier' ? { copie: 'C2', note: 16.5 } : null))
    await touche('3')
    await touche('4')
    await w.find('#commentaire-general').setValue('Très bonne reformulation.')
    await w.find('.bouton-principal').trigger('click')
    await flushPromises()
    expect(ecrire.mock.calls[0]).toEqual(['corriger', {
      copie: 'C2', niveaux: { pertinence: 2, rigueur: 3 }, commentaires: { general: 'Très bonne reformulation.' },
    }])
    expect(ecrire.mock.calls[1]).toEqual(['publier', { copie: 'C2' }])
    expect(routeur.currentRoute.value.params.copie).toBe('C3')
    expect(w.find('[role="status"]').text()).toBe('Note publiée : 16,5 / 20.')
  })

  it('publication en échec : la copie reste gardée contre une sortie sans confirmation', async () => {
    const { w, routeur } = await ouvrir()
    ecrire.mockImplementation(async (methode) => {
      if (methode === 'publier') throw new Error('Publication refusée.')
      return null
    })
    await touche('3')
    await touche('4')
    await w.find('.bouton-principal').trigger('click')
    await flushPromises()
    expect(w.find('[role="alert"]').exists()).toBe(true)
    const confirmer = vi.spyOn(window, 'confirm').mockReturnValue(false)
    await touche('j')
    expect(confirmer).toHaveBeenCalledTimes(1)
    expect(routeur.currentRoute.value.params.copie).toBe('C2')
    confirmer.mockRestore()
  })

  it('limitation de débit : message clair, saisie conservée', async () => {
    const { w } = await ouvrir()
    ecrire.mockRejectedValue(Object.assign(new Error('429'), { status: 429 }))
    await touche('1')
    await touche('2')
    await w.findAll('.actions .bouton')[0].trigger('click')
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
    confirmer.mockReturnValue(true)
    await touche('j')
    expect(confirmer).toHaveBeenCalledTimes(4)
    expect(routeur.currentRoute.value.params.copie).toBe('C3')
    confirmer.mockRestore()
  })

  it('sans modification : on change de copie sans confirmation', async () => {
    const { routeur } = await ouvrir()
    const confirmer = vi.spyOn(window, 'confirm')
    await touche('j')
    expect(confirmer).not.toHaveBeenCalled()
    expect(routeur.currentRoute.value.params.copie).toBe('C3')
    confirmer.mockRestore()
  })

  it('fermeture ou rechargement de la page retenus tant que la copie est modifiée', async () => {
    await ouvrir()
    const quitter = () => {
      const e = new Event('beforeunload', { cancelable: true })
      window.dispatchEvent(e)
      return e.defaultPrevented
    }
    expect(quitter()).toBe(false)
    await touche('2')
    expect(quitter()).toBe(true)
  })

  it("copie signalée : la proposition de l'IA est écartée de la grille et de la copie", async () => {
    const ia = { ...COPIE.ia, justifications: { pertinence: 'Justification piégée' } }
    const { w } = await ouvrir({ ...COPIE, ia, signalement: "copie signalée : tentative d'instruction à l'IA" })
    expect(w.find('.signalement').exists()).toBe(true)
    expect(w.findAll('.puce').map((p) => p.text())).not.toContain('IA')
    expect(w.find('.ia-ligne').exists()).toBe(false)
    expect(w.find('mark.citation').exists()).toBe(false)
    expect(w.text()).not.toContain('Justification piégée')
  })

  it('un juré enregistre sa note mais ne publie pas', async () => {
    const { w } = await ouvrir({ ...COPIE, role: 'jury', jury: { mediane: {}, nombre: 1, attendus: 3 } })
    expect(w.findAll('.actions button').map((b) => b.text())).toEqual(['Enregistrer ma note'])
  })
})
