import type { Navigateur } from '../../application/ports'

/** Navigation de la page entière vers une adresse externe (page de paiement). */
export function navigateurSur(lieu: () => Pick<Location, 'assign'>): Navigateur {
  return { aller: (url) => lieu().assign(url) }
}
