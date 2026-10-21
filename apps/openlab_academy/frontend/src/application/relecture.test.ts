import { describe, expect, it } from 'vitest'
import { DUREE_BROUILLON_MS } from '../domaine/relecture'
import { resumeRelecture, vueRelecture } from '../test/fabriques'
import { MAINTENANT, fauxCasUsages } from '../test/faux-ports'
import { ErreurDepot } from './erreurs'

const COMPLETE = {
  niveaux: { pertinence: 2, rigueur: 1 },
  conseils: { pertinence: 'Question précise.', rigueur: 'Cite tes sources.' },
}
const ilYa = (ms: number) => new Date(MAINTENANT.getTime() - ms).toISOString()

describe('relectures', () => {
  it('liste de mes relectures', async () => {
    const { ports, cas } = fauxCasUsages()
    const liste = [resumeRelecture('R1')]
    ports.relecture.mesRelectures.mockResolvedValue(liste)
    expect(await cas.consulterRelectures.executer()).toBe(liste)
  })

  it('ouvrir une relecture reprend le brouillon gardé sur l’appareil', async () => {
    const { ports, cas } = fauxCasUsages()
    ports.relecture.relecture.mockResolvedValue(vueRelecture())
    ports.brouillons.garder('R1', { ...COMPLETE, enregistre: ilYa(1000) })
    const { vue, saisie } = await cas.ouvrirRelecture.executer('R1')
    expect(ports.relecture.relecture).toHaveBeenCalledWith('R1')
    expect(vue.relecture).toBe('R1')
    expect(saisie).toEqual(COMPLETE)
  })

  it('sans brouillon : saisie vierge', async () => {
    const { ports, cas } = fauxCasUsages()
    ports.relecture.relecture.mockResolvedValue(vueRelecture())
    expect((await cas.ouvrirRelecture.executer('R1')).saisie).toEqual({ niveaux: {}, conseils: {} })
  })

  it('un brouillon périmé est oublié', async () => {
    const { ports, cas } = fauxCasUsages()
    ports.relecture.relecture.mockResolvedValue(vueRelecture())
    ports.brouillons.garder('R1', { ...COMPLETE, enregistre: ilYa(DUREE_BROUILLON_MS + 1) })
    expect((await cas.ouvrirRelecture.executer('R1')).saisie).toEqual({ niveaux: {}, conseils: {} })
    expect(ports.brouillons.lire('R1')).toBeNull()
  })

  it('relecture déjà envoyée : son brouillon est oublié (appareil partagé)', async () => {
    const { ports, cas } = fauxCasUsages()
    ports.relecture.relecture.mockResolvedValue(vueRelecture({ statut: 'faite' }))
    ports.brouillons.garder('R1', { ...COMPLETE, enregistre: ilYa(1000) })
    expect((await cas.ouvrirRelecture.executer('R1')).saisie).toEqual({ niveaux: {}, conseils: {} })
    expect(ports.brouillons.lire('R1')).toBeNull()
  })

  it('garder le brouillon le date', () => {
    const { ports, cas } = fauxCasUsages()
    cas.garderBrouillon.executer('R1', COMPLETE)
    expect(ports.brouillons.lire('R1')).toEqual({ ...COMPLETE, enregistre: MAINTENANT.toISOString() })
  })

  it("relecture incomplète : rien n'est envoyé, les critères manquants sont rendus", async () => {
    const { ports, cas } = fauxCasUsages()
    const saisie = { niveaux: { pertinence: 1 }, conseils: { pertinence: 'Bien.' } }
    expect(await cas.envoyerRelecture.executer('R1', vueRelecture().grille, saisie)).toEqual({
      envoyee: false,
      incomplets: ['rigueur'],
    })
    expect(ports.relecture.enregistrer).not.toHaveBeenCalled()
  })

  it('envoyer : enregistre, oublie le brouillon et désigne la relecture suivante', async () => {
    const { ports, cas } = fauxCasUsages()
    ports.brouillons.garder('R1', COMPLETE)
    const liste = [resumeRelecture('R1', { statut: 'faite' }), resumeRelecture('R2')]
    ports.relecture.mesRelectures.mockResolvedValue(liste)
    expect(await cas.envoyerRelecture.executer('R1', vueRelecture().grille, COMPLETE)).toEqual({
      envoyee: true,
      liste,
      suivante: 'R2',
    })
    expect(ports.relecture.enregistrer).toHaveBeenCalledWith('R1', COMPLETE)
    expect(ports.brouillons.lire('R1')).toBeNull()
  })

  it('dernière relecture envoyée : pas de suivante', async () => {
    const { ports, cas } = fauxCasUsages()
    ports.relecture.mesRelectures.mockResolvedValue([resumeRelecture('R1', { statut: 'faite' })])
    const resultat = await cas.envoyerRelecture.executer('R1', vueRelecture().grille, COMPLETE)
    expect(resultat).toMatchObject({ envoyee: true, suivante: null })
  })

  it('envoi refusé : le brouillon reste', async () => {
    const { ports, cas } = fauxCasUsages()
    ports.brouillons.garder('R1', COMPLETE)
    ports.relecture.enregistrer.mockRejectedValue(new ErreurDepot('trop_de_demandes'))
    await expect(cas.envoyerRelecture.executer('R1', vueRelecture().grille, COMPLETE)).rejects.toBeInstanceOf(
      ErreurDepot,
    )
    expect(ports.brouillons.lire('R1')).toEqual(COMPLETE)
  })
})
