// Monte l'application sous <RouterView>, comme en vrai, avec les cas d'usage réels branchés sur des faux ports.
import { flushPromises, mount } from '@vue/test-utils'
import { createMemoryHistory } from 'vue-router'
import App from '../interface/App.vue'
import { CLE_CAS_USAGES } from '../interface/injection'
import { creerRouteur } from '../interface/routeur'
import { fauxCasUsages, fauxPorts, type FauxPorts } from './faux-ports'

export async function monterEcran(chemin: string, ports: FauxPorts = fauxPorts()) {
  const { cas } = fauxCasUsages(ports)
  const routeur = creerRouteur(createMemoryHistory())
  await routeur.push(chemin)
  const w = mount(App, {
    global: { plugins: [routeur], provide: { [CLE_CAS_USAGES as symbol]: cas } },
    attachTo: document.body,
  })
  await flushPromises()
  return { w, routeur, ports }
}

export const touche = async (key: string, options: KeyboardEventInit = {}) => {
  window.dispatchEvent(new KeyboardEvent('keydown', { key, ...options }))
  await flushPromises()
}
