import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import GrilleCorrecteur from './GrilleCorrecteur.vue'

const LIBELLES = ['Insuffisant', 'À consolider', 'Satisfaisant', 'Excellent']
const critere = (code, libelle, poids) => ({
  code, libelle, poids, description: libelle, controles: [],
  niveaux: LIBELLES.map((l, i) => ({ libelle: l, descripteur: `${l} (${code})`, points: i })),
})
const GRILLE = { criteres: [critere('pertinence', 'Pertinence de la question', 60), critere('rigueur', 'Rigueur des données', 40)] }
const IA = {
  niveaux: { pertinence: 2, rigueur: 1 },
  justifications: { pertinence: 'La question cible un écart chiffré.', rigueur: '<img src=x onerror=alert(1)>' },
  citations: { pertinence: 'pourquoi', rigueur: 'données' },
  confiance: 0.86,
}
const PAIRS = { mediane: { pertinence: 2, rigueur: 3 }, nombre: 3, commentaires: [{ rigueur: '<b>Cite tes sources</b>' }] }

function monter(props = {}) {
  return mount(GrilleCorrecteur, {
    props: {
      grille: GRILLE, niveaux: {}, commentaires: {}, actif: 'pertinence',
      auto: { pertinence: 2, rigueur: 3 }, ia: IA, pairs: PAIRS, ...props,
    },
  })
}

const boutons = (w, code) => w.find(`[data-critere="${code}"]`).findAll('button.niveau')

describe('GrilleCorrecteur', () => {
  it('place les sources A, IA et P sur leurs niveaux', () => {
    const w = monter()
    const satisfaisant = boutons(w, 'pertinence')[2]
    expect(satisfaisant.findAll('.puce').map((p) => p.text())).toEqual(['A', 'IA', 'P'])
    expect(satisfaisant.find('.sr-only').text()).toContain('auto-évaluation, IA, médiane des pairs')
    expect(boutons(w, 'rigueur')[1].findAll('.puce').map((p) => p.text())).toEqual(['IA'])
    expect(boutons(w, 'rigueur')[3].findAll('.puce').map((p) => p.text())).toEqual(['A', 'P'])
    expect(w.find('.legende').text()).toContain('médiane des pairs (3)')
  })

  it('le niveau choisi est pressé et émet le nouveau choix et le critère actif', async () => {
    const w = monter({ niveaux: { pertinence: 1 } })
    expect(boutons(w, 'pertinence')[1].attributes('aria-pressed')).toBe('true')
    expect(boutons(w, 'pertinence')[2].attributes('aria-pressed')).toBe('false')
    await boutons(w, 'rigueur')[3].trigger('click')
    expect(w.emitted('update:niveaux').at(-1)).toEqual([{ pertinence: 1, rigueur: 3 }])
    expect(w.emitted('update:actif').at(-1)).toEqual(['rigueur'])
  })

  it("signale l'écart de plus d'un niveau entre l'IA et les pairs", () => {
    const w = monter()
    expect(w.find('[data-critere="pertinence"] .ecart').exists()).toBe(false)
    expect(w.find('[data-critere="rigueur"] .ecart').text()).toContain('à trancher')
  })

  it("affiche la justification de l'IA et les pairs en texte brut, jamais en HTML", () => {
    const w = monter()
    expect(w.find('[data-critere="pertinence"] .ia-ligne').text()).toBe(
      'IA, confiance 0,86 : « La question cible un écart chiffré. »',
    )
    expect(w.find('img').exists()).toBe(false)
    expect(w.find('[data-critere="rigueur"] .ia-ligne').text()).toContain('<img src=x onerror=alert(1)>')
    expect(w.find('[data-critere="rigueur"] .pairs').html()).toContain('&lt;b&gt;Cite tes sources&lt;/b&gt;')
  })

  it('sans IA ni pairs : ni puce, ni écart, ni justification', () => {
    const w = monter({ ia: null, pairs: { mediane: {}, nombre: 0, commentaires: [] }, auto: null })
    expect(w.findAll('.niveaux .puce')).toHaveLength(0)
    expect(w.find('.ecart').exists()).toBe(false)
    expect(w.find('.ia-ligne').exists()).toBe(false)
  })

  it('le commentaire par critère est émis tel quel', async () => {
    const w = monter({ commentaires: { general: 'x' } })
    await w.find('#commentaire-rigueur').setValue('Discutez la fiabilité.')
    expect(w.emitted('update:commentaires').at(-1)).toEqual([{ general: 'x', rigueur: 'Discutez la fiabilité.' }])
  })

  it('le critère actif est marqué', () => {
    const w = monter({ actif: 'rigueur' })
    expect(w.find('[data-critere="rigueur"]').classes()).toContain('actif')
    expect(w.find('[data-critere="pertinence"]').classes()).not.toContain('actif')
  })
})
