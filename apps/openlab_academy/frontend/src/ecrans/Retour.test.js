import { enableAutoUnmount, flushPromises, mount } from '@vue/test-utils'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { createMemoryHistory } from 'vue-router'
import { creerRouteur } from '../routeur'
import Retour from './Retour.vue'

const lire = vi.fn()
vi.mock('../lib/api', async (original) => ({ ...(await original()), lire: (...a) => lire(...a) }))

const NIVEAUX = ['Insuffisant', 'À consolider', 'Satisfaisant', 'Excellent']
const BASE = {
  copie: 'C1', exercice: 'ASG-1', titre: 'La baisse des ventes à Bouaké', statut: 'publiee', provisoire: false,
  masquee: false, note: null, note_sur: null, reussite: null, criteres: [], commentaire_general: '', message: '',
}
const critere = (code, niveau, autres = {}) => ({
  code, libelle: code, poids: 50, niveau, niveau_libelle: NIVEAUX[niveau], niveaux: NIVEAUX,
  auto_evaluation: null, commentaire: '', pairs: [], ...autres,
})

async function afficher(retour) {
  lire.mockResolvedValue(retour)
  const routeur = creerRouteur(createMemoryHistory())
  await routeur.push('/retour/C1')
  const w = mount(Retour, { global: { plugins: [routeur] } })
  await flushPromises()
  return w
}

enableAutoUnmount(afterEach)

describe('Mon retour', () => {
  beforeEach(() => {
    lire.mockReset()
  })

  it('note en attente tant que les relectures ne sont pas faites', async () => {
    const w = await afficher({ ...BASE, masquee: true, message: 'Votre note sera visible dès que vous aurez terminé vos relectures.' })
    expect(lire).toHaveBeenCalledWith('mon_retour', { copie: 'C1' })
    expect(w.find('.attente h2').text()).toBe('Note en attente')
    expect(w.find('.attente a').attributes('href')).toBe('/relecture')
    expect(w.find('.valeur').exists()).toBe(false)
  })

  it('note publiée, niveaux et commentaires par critère', async () => {
    const w = await afficher({
      ...BASE, note: 15, note_sur: 20, reussite: true, commentaire_general: 'Très bonne reformulation.',
      criteres: [critere('pertinence', 2, { auto_evaluation: 2 }), critere('ancrage', 3, { pairs: ['Pense aux sources.'] })],
    })
    expect(w.find('.valeur').text()).toBe('15')
    expect(w.find('.reussi').text()).toBe('Validé')
    expect(w.find('.provisoire').exists()).toBe(false)
    const barres = w.findAll('.barre')
    expect(barres[0].findAll('span').map((s) => s.classes()[0])).toEqual(['atteint', 'atteint', 'atteint', 'vide'])
    expect(barres[1].findAll('span').map((s) => s.classes()[0])).toEqual(['atteint', 'atteint', 'atteint', 'sommet'])
    expect(w.find('.detail').text()).toContain('Votre auto-évaluation : Satisfaisant.')
    expect(w.find('.pairs').text()).toContain('« Pense aux sources. »')
  })

  it('mention « provisoire » sur une note provisoire', async () => {
    const w = await afficher({
      ...BASE, statut: 'provisoire', provisoire: true, note: 10, note_sur: 20, reussite: true,
      message: 'Note provisoire, en attente de validation par le formateur.', criteres: [critere('pertinence', 1)],
    })
    expect(w.find('.provisoire').text()).toBe('provisoire')
    expect(w.find('.mention').text()).toBe('Note provisoire, en attente de validation par le formateur.')
  })

  it('commentaire du formateur (ou justification IA validée) en texte brut', async () => {
    const piege = '<img src=x onerror=alert(1)> **gras**'
    const w = await afficher({
      ...BASE, note: 12, note_sur: 20, reussite: true, commentaire_general: piege,
      criteres: [critere('pertinence', 1, { commentaire: piege })],
    })
    expect(w.find('img').exists()).toBe(false)
    expect(w.find('strong').exists()).toBe(false)
    expect(w.find('.general').text()).toBe(piege)
    expect(w.find('.detail').text()).toBe(piege)
  })

  it('copie en cours de correction : message seul', async () => {
    const w = await afficher({ ...BASE, statut: 'a_corriger', message: 'Votre copie est en cours de correction.' })
    expect(w.find('.bandeau-info').text()).toBe('Votre copie est en cours de correction.')
    expect(w.find('.criteres').exists()).toBe(false)
  })

  it('erreur d’accès affichée clairement', async () => {
    lire.mockRejectedValue(Object.assign(new Error('403'), { status: 403 }))
    const routeur = creerRouteur(createMemoryHistory())
    await routeur.push('/retour/C9')
    const w = mount(Retour, { global: { plugins: [routeur] } })
    await flushPromises()
    expect(w.find('[role="alert"]').text()).toContain("n'existe pas ou ne vous est pas ouvert")
  })
})
