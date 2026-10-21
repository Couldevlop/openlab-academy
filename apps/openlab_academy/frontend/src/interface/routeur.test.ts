import { enableAutoUnmount, mount } from '@vue/test-utils'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { defineComponent } from 'vue'
import { monterEcran } from '../test/monter'
import { utiliserCasUsages } from './injection'
import { parametre } from './routeur'

enableAutoUnmount(afterEach)

describe('routeur et accueil', () => {
  it('accueil : relectures et correction ; titre de la page', async () => {
    const { w } = await monterEcran('/')
    expect(w.findAll('.lien').map((a) => a.attributes('href'))).toEqual(['/relecture', '/correcteur'])
    expect(document.title).toBe('Mon espace · OpenLab Academy')
  })

  it('une adresse inconnue ramène à l’accueil', async () => {
    const { routeur } = await monterEcran('/nulle/part')
    expect(routeur.currentRoute.value.name).toBe('accueil')
  })

  it('paramètre de route lu comme un texte', () => {
    expect(parametre('C1')).toBe('C1')
    expect(parametre(['C1', 'C2'])).toBe('C1')
    expect(parametre(null)).toBe('')
    expect(parametre(undefined)).toBe('')
  })
})

describe('injection des cas d’usage', () => {
  it('un écran monté sans cas d’usage échoue clairement', () => {
    const Ecran = defineComponent({
      setup() {
        utiliserCasUsages()
        return () => null
      },
    })
    vi.spyOn(console, 'warn').mockImplementation(() => undefined)
    expect(() => mount(Ecran)).toThrow("cas d'usage non fournis")
    vi.restoreAllMocks()
  })
})
