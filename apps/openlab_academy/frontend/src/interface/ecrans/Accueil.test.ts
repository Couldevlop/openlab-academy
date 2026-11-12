import { enableAutoUnmount } from '@vue/test-utils'
import { afterEach, describe, expect, it } from 'vitest'
import { fauxPorts } from '../../test/faux-ports'
import { monterEcran } from '../../test/monter'

enableAutoUnmount(afterEach)

describe('Accueil', () => {
  it('« Mes paiements » de chaque parcours payant de l’apprenant', async () => {
    const ports = fauxPorts()
    ports.session.droits.mockReturnValue({
      intendance: false,
      finances: false,
      pilotage: false,
      paiements: [{ cours: 'data-science', titre: 'Fondamentaux de la Data Science' }],
    })
    const { w } = await monterEcran('/', ports)
    const liens = w.findAll('a.paiement')
    expect(liens).toHaveLength(1)
    expect(liens[0]!.attributes('href')).toBe('/paiement/data-science')
    expect(liens[0]!.text()).toContain('Mes paiements')
    expect(liens[0]!.text()).toContain('Fondamentaux de la Data Science')
  })

  it('sans parcours payant : aucun lien de paiement', async () => {
    const { w } = await monterEcran('/')
    expect(w.find('a.paiement').exists()).toBe(false)
  })
})
