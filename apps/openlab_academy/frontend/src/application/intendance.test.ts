import { describe, expect, it } from 'vitest'
import { FILTRES_VIDES } from '../domaine/intendance'
import { ficheIntendance, resumeFinances, vueIntendance } from '../test/fabriques'
import { fauxCasUsages, fauxPorts, horlogeFixe } from '../test/faux-ports'
import { ErreurDepot, messageErreur } from './erreurs'

const AUJOURDHUI = new Date('2026-11-02T09:00:00Z')

function monter() {
  const ports = fauxPorts()
  ports.horloge = horlogeFixe(AUJOURDHUI)
  return fauxCasUsages(ports)
}

describe('intendance', () => {
  it('filtres appliqués à l’API : seules les valeurs saisies partent', async () => {
    const { ports, cas } = monter()
    const vue = vueIntendance()
    ports.intendance.intendance.mockResolvedValue(vue)
    const filtres = { ...FILTRES_VIDES, parcours: 'python-avance', statut: 'en_retard' as const, au: '2026-10-31' }
    expect(await cas.consulterIntendance.executer(filtres)).toBe(vue)
    expect(ports.intendance.intendance).toHaveBeenCalledWith({
      parcours: 'python-avance',
      statut: 'en_retard',
      au: '2026-10-31',
    })
  })

  it('lien d’export Excel avec les mêmes filtres', () => {
    const { ports, cas } = monter()
    ports.intendance.lienExport.mockReturnValue('/api/x')
    expect(cas.lienExport.executer({ ...FILTRES_VIDES, mode: 'mensuel' })).toBe('/api/x')
    expect(ports.intendance.lienExport).toHaveBeenCalledWith({ mode: 'mensuel' })
  })

  it('fiche d’un dossier, avec le jour courant', async () => {
    const { ports, cas } = monter()
    const f = ficheIntendance()
    ports.intendance.fiche.mockResolvedValue(f)
    expect(await cas.ouvrirFiche.executer('DP-0001')).toEqual({ fiche: f, aujourdhui: '2026-11-02' })
    expect(ports.intendance.fiche).toHaveBeenCalledWith('DP-0001')
  })

  it('virement : saisie relue (montant entier, blancs ôtés) puis envoyée', async () => {
    const { ports, cas } = monter()
    await cas.enregistrerVirement.executer('DP-0001', {
      montant: '50 000',
      reference: ' VIR-1 ',
      date: '2026-11-02',
      motif: ' Relevé ',
    })
    expect(ports.intendance.enregistrerVirement).toHaveBeenCalledWith('DP-0001', {
      montant: 50000,
      reference: 'VIR-1',
      date_paiement: '2026-11-02',
      motif: 'Relevé',
    })
  })

  it('virement : montant vide ou référence manquante refusés sans appel au serveur', async () => {
    const { ports, cas } = monter()
    const erreur = await cas.enregistrerVirement
      .executer('DP-0001', { montant: '', reference: '', date: '2026-11-02', motif: 'x' })
      .catch((e: unknown) => e)
    expect(erreur).toBeInstanceOf(ErreurDepot)
    expect(messageErreur(erreur)).toBe('Indiquez le montant reçu. Indiquez la référence du virement.')
    expect(ports.intendance.enregistrerVirement).not.toHaveBeenCalled()
  })

  it('délai : date après aujourd’hui et motif, sinon refus local', async () => {
    const { ports, cas } = monter()
    await cas.accorderDelai.executer('DP-0002', { jusquau: '2026-11-20', motif: ' Accord ' })
    expect(ports.intendance.accorderDelai).toHaveBeenCalledWith('DP-0002', '2026-11-20', 'Accord')
    const erreur = await cas.accorderDelai
      .executer('DP-0002', { jusquau: '2026-11-02', motif: '' })
      .catch((e: unknown) => e)
    expect(messageErreur(erreur)).toBe('La nouvelle date limite doit être après aujourd’hui. Le motif est obligatoire.')
    expect(ports.intendance.accorderDelai).toHaveBeenCalledTimes(1)
  })

  it('résumé des finances et droits des écrans', async () => {
    const { ports, cas } = monter()
    const r = resumeFinances()
    ports.intendance.resume.mockResolvedValue(r)
    expect(await cas.consulterResume.executer()).toBe(r)
    expect(cas.consulterDroits.executer()).toEqual({ intendance: false, finances: false, pilotage: false })
    ports.session.droits.mockReturnValue({ intendance: true, finances: true, pilotage: false })
    expect(cas.consulterDroits.executer()).toEqual({ intendance: true, finances: true, pilotage: false })
  })
})
