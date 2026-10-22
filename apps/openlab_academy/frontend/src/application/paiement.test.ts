import { describe, expect, it } from 'vitest'
import { dossierPaiement } from '../test/fabriques'
import { fauxCasUsages, fauxPorts, horlogeFixe } from '../test/faux-ports'
import { ErreurDepot, messageErreur } from './erreurs'
import { LIEN_REFUSE, TELEPHONE_INVALIDE } from './paiement'

describe('mes paiements', () => {
  it('charger son dossier, avec le jour courant pour situer les échéances', async () => {
    const ports = fauxPorts()
    ports.horloge = horlogeFixe(new Date('2026-11-11T08:00:00Z'))
    const { cas } = fauxCasUsages(ports)
    const d = dossierPaiement()
    ports.paiement.monDossier.mockResolvedValue(d)
    expect(await cas.chargerDossier.executer('fondamentaux-data')).toEqual({ dossier: d, aujourdhui: '2026-11-11' })
    expect(ports.paiement.monDossier).toHaveBeenCalledWith('fondamentaux-data')
  })

  it('choisir un mode : téléphone normalisé avant l’envoi, dossier à jour rendu', async () => {
    const { ports, cas } = fauxCasUsages()
    const apres = dossierPaiement({ mode: 'mensuel' })
    ports.paiement.choisirMode.mockResolvedValue(apres)
    expect(await cas.choisirMode.executer('C1', 'mensuel', '07 00 00 00 02')).toBe(apres)
    expect(ports.paiement.choisirMode).toHaveBeenCalledWith('C1', 'mensuel', '+2250700000002')
  })

  it('téléphone invalide : refusé sans appel au serveur', async () => {
    const { ports, cas } = fauxCasUsages()
    const erreur = await cas.choisirMode.executer('C1', 'mensuel', '0700').catch((e: unknown) => e)
    expect(erreur).toBeInstanceOf(ErreurDepot)
    expect(messageErreur(erreur)).toBe(TELEPHONE_INVALIDE)
    expect(ports.paiement.choisirMode).not.toHaveBeenCalled()
  })

  it('payer : redirection vers la page https rendue par le serveur', async () => {
    const { ports, cas } = fauxCasUsages()
    ports.paiement.payer.mockResolvedValue('https://checkout.cinetpay.com/payment/abc')
    await cas.payer.executer('C1')
    expect(ports.paiement.payer).toHaveBeenCalledWith('C1')
    expect(ports.navigateur.aller).toHaveBeenCalledWith('https://checkout.cinetpay.com/payment/abc')
  })

  it('payer : un lien non https n’est jamais suivi', async () => {
    const { ports, cas } = fauxCasUsages()
    ports.paiement.payer.mockResolvedValue('javascript:alert(1)')
    const erreur = await cas.payer.executer('C1').catch((e: unknown) => e)
    expect(messageErreur(erreur)).toBe(LIEN_REFUSE)
    expect(ports.navigateur.aller).not.toHaveBeenCalled()
  })

  it('payer : un refus du serveur remonte tel quel, sans redirection', async () => {
    const { ports, cas } = fauxCasUsages()
    ports.paiement.payer.mockRejectedValue(
      new ErreurDepot('refus', ["Le paiement en ligne n'est pas disponible pour le moment."]),
    )
    await expect(cas.payer.executer('C1')).rejects.toMatchObject({ sorte: 'refus' })
    expect(ports.navigateur.aller).not.toHaveBeenCalled()
  })
})
