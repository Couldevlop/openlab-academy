import { describe, expect, it, vi } from 'vitest'
import { DepotBrouillonsNavigateur } from './navigateur/brouillons'
import { horlogeSysteme } from './navigateur/horloge'
import {
  DepotCorrectionFrappe,
  DepotIntendanceFrappe,
  DepotPaiementFrappe,
  DepotPilotageFrappe,
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
      () => ({ intendance: true, finances: false, pilotage: false }),
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
    expect(ports.pilotage).toBeInstanceOf(DepotPilotageFrappe)
    await ports.pilotage.souffrances().catch(() => undefined)
    expect(requete).toHaveBeenLastCalledWith(
      expect.objectContaining({
        url: 'openlab_academy.entrypoints.evaluation_api.copies_en_souffrance',
        method: 'GET',
      }),
    )
    expect(ports.session.droits()).toEqual({ intendance: true, finances: false, pilotage: false, paiements: [] })
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
    const tous = { intendance: true, finances: true, pilotage: true, paiements: [{ cours: 'c', titre: 'C' }] }
    expect(droits(tous).session.droits()).toEqual(tous)
    expect(droits({ intendance: true, finances: true, pilotage: true }).session.droits().paiements).toEqual([])
    const malformes = [
      undefined,
      null,
      'oui',
      { intendance: 'true', finances: false, pilotage: false },
      { intendance: true },
      { intendance: true, finances: true },
      { intendance: true, finances: true, pilotage: true, paiements: [{ cours: 1 }] },
    ]
    for (const v of malformes) {
      expect(droits(v).session.droits()).toEqual({ intendance: false, finances: false, pilotage: false, paiements: [] })
    }
  })
})
