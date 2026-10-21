// Les écrans reçoivent les cas d'usage par provide/inject : ils ne connaissent ni le réseau ni le stockage.
import { inject, type InjectionKey } from 'vue'
import type { CasUsages } from '../application/cas-usages'

export const CLE_CAS_USAGES: InjectionKey<CasUsages> = Symbol('cas-usages')

export function utiliserCasUsages(): CasUsages {
  const cas = inject(CLE_CAS_USAGES, null)
  if (!cas) throw new Error("cas d'usage non fournis : l'application doit les fournir (provide) au démarrage")
  return cas
}
