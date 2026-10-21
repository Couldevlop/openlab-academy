import { describe, expect, it, vi } from 'vitest'
import { DepotBrouillonsNavigateur } from './navigateur/brouillons'
import { horlogeSysteme } from './navigateur/horloge'
import { DepotCorrectionFrappe, DepotRelectureFrappe, DepotRetourFrappe } from './frappe/depots'
import { creerPorts } from './ports'

describe('adaptateurs', () => {
  it("branchent chaque port sur Frappe, l'appareil et l'horloge système", async () => {
    const requete = vi.fn(async () => ({ copie: 'C1', note: 12 }))
    const ports = creerPorts(requete, () => localStorage)
    expect(ports.correction).toBeInstanceOf(DepotCorrectionFrappe)
    expect(ports.relecture).toBeInstanceOf(DepotRelectureFrappe)
    expect(ports.retour).toBeInstanceOf(DepotRetourFrappe)
    expect(ports.brouillons).toBeInstanceOf(DepotBrouillonsNavigateur)
    expect(ports.horloge).toBe(horlogeSysteme)
    expect(await ports.correction.publier('C1')).toBe(12)
    expect(requete).toHaveBeenCalledOnce()
  })
})
