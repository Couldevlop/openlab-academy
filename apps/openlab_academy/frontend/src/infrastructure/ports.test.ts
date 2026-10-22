import { describe, expect, it, vi } from 'vitest'
import { DepotBrouillonsNavigateur } from './navigateur/brouillons'
import { horlogeSysteme } from './navigateur/horloge'
import {
  DepotCorrectionFrappe,
  DepotIntendanceFrappe,
  DepotPaiementFrappe,
  DepotRelectureFrappe,
  DepotRetourFrappe,
} from './frappe/depots'
import { creerPorts } from './ports'

describe('adaptateurs', () => {
  it("branchent chaque port sur Frappe, l'appareil et l'horloge système", async () => {
    const requete = vi.fn(async () => ({ copie: 'C1', note: 12 }))
    const lieu = { assign: vi.fn() }
    const ports = creerPorts(
      requete,
      () => localStorage,
      () => lieu,
      () => ({ intendance: true, finances: false }),
    )
    expect(ports.correction).toBeInstanceOf(DepotCorrectionFrappe)
    expect(ports.relecture).toBeInstanceOf(DepotRelectureFrappe)
    expect(ports.retour).toBeInstanceOf(DepotRetourFrappe)
    expect(ports.brouillons).toBeInstanceOf(DepotBrouillonsNavigateur)
    expect(ports.horloge).toBe(horlogeSysteme)
    expect(await ports.correction.publier('C1')).toBe(12)
    expect(requete).toHaveBeenCalledOnce()
    expect(ports.paiement).toBeInstanceOf(DepotPaiementFrappe)
    await ports.paiement.payer('C1').catch(() => undefined)
    expect(requete).toHaveBeenLastCalledWith(
      expect.objectContaining({ url: 'openlab_academy.entrypoints.paiement_api.payer', method: 'POST' }),
    )
    expect(ports.intendance).toBeInstanceOf(DepotIntendanceFrappe)
    await ports.intendance.resume().catch(() => undefined)
    expect(requete).toHaveBeenLastCalledWith(
      expect.objectContaining({ url: 'openlab_academy.entrypoints.paiement_api.resume', method: 'GET' }),
    )
    expect(ports.session.droits()).toEqual({ intendance: true, finances: false })
    ports.navigateur.aller('https://checkout.cinetpay.com/payment/abc')
    expect(lieu.assign).toHaveBeenCalledWith('https://checkout.cinetpay.com/payment/abc')
  })
})

describe('droits de la session', () => {
  it('lus sur la page ; absents ou malformés : aucun écran d’agent', () => {
    const droits = (valeur: unknown) =>
      creerPorts(
        vi.fn(),
        () => localStorage,
        () => ({ assign: vi.fn() }),
        () => valeur,
      )
    expect(droits({ intendance: true, finances: true }).session.droits()).toEqual({ intendance: true, finances: true })
    for (const v of [undefined, null, 'oui', { intendance: 'true', finances: false }, { intendance: true }]) {
      expect(droits(v).session.droits()).toEqual({ intendance: false, finances: false })
    }
  })
})
