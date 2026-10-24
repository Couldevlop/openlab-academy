import { describe, expect, it } from 'vitest'
import { dossierPaiement, parcoursGratuit } from '../test/fabriques'
import {
  estGratuit,
  MODES,
  calendrierMode,
  changement,
  enSouffrance,
  etatEcheance,
  formaterJour,
  formaterTelephone,
  formaterXof,
  jourIso,
  libelleMode,
  libelleStatut,
  libelleStatutDossier,
  lignesEcheancier,
  normaliserTelephone,
  progression,
  urlPaiementSure,
} from './paiement'

const FINE = ' '

describe('montants en francs CFA', () => {
  it('groupes de trois chiffres et unité séparés par des espaces fines insécables', () => {
    expect(formaterXof(187500)).toBe(`187${FINE}500${FINE}FCFA`)
    expect(formaterXof(1250000)).toBe(`1${FINE}250${FINE}000${FINE}FCFA`)
    expect(formaterXof(500)).toBe(`500${FINE}FCFA`)
    expect(formaterXof(0)).toBe(`0${FINE}FCFA`)
    expect(formaterXof(-10000)).toBe(`-10${FINE}000${FINE}FCFA`)
    expect(formaterXof(99999.6)).toBe(`100${FINE}000${FINE}FCFA`)
  })
})

describe('libellés', () => {
  it('statut, mode et calendrier de chaque mode', () => {
    expect(['a_jour', 'en_retard', 'solde', 'dispense'].map((s) => libelleStatut(s as never))).toEqual([
      'À jour',
      'En retard',
      'Soldé',
      'Dispensé',
    ])
    expect(MODES.map(libelleMode)).toEqual(['En une fois', 'En deux tranches', 'Chaque mois'])
    expect(MODES.map(calendrierMode)).toEqual([
      'Un seul versement, à la prochaine échéance du mois',
      'Deux versements, l’un au début, l’autre au milieu du parcours',
      'Un versement par mois jusqu’à la fin du parcours',
    ])
  })

  it('dates à la française, sans heure', () => {
    expect(formaterJour('2026-11-10')).toBe('10 novembre 2026')
    expect(formaterJour(null)).toBe('')
    expect(formaterJour('pas une date')).toBe('')
  })

  it('jour courant en UTC (fuseau d’Abidjan)', () => {
    expect(jourIso(new Date('2026-11-10T23:30:00Z'))).toBe('2026-11-10')
  })
})

describe('échéancier', () => {
  it('chaque échéance réglée, en retard (dès le lendemain de sa date) ou à venir', () => {
    const e = { date_limite: '2026-11-10', montant: 50000, libelle: 'Échéance', couverte: false }
    expect(etatEcheance(e, '2026-11-09')).toBe('a_venir')
    expect(etatEcheance(e, '2026-11-10')).toBe('aujourdhui')
    expect(etatEcheance(e, '2026-11-11')).toBe('en_retard')
    expect(etatEcheance({ ...e, couverte: true }, '2026-12-01')).toBe('reglee')
  })

  it('la prochaine échéance à payer est repérée une seule fois', () => {
    const d = dossierPaiement({
      echeances: [
        { date_limite: '2026-10-22', montant: 10000, libelle: 'Frais d’inscription', couverte: true },
        { date_limite: '2026-11-10', montant: 50000, libelle: 'Échéance', couverte: false },
        { date_limite: '2027-01-10', montant: 50000, libelle: 'Échéance', couverte: false },
      ],
    })
    expect(lignesEcheancier(d, '2026-11-02').map((l) => [l.etat, l.prochaine])).toEqual([
      ['reglee', false],
      ['a_venir', true],
      ['a_venir', false],
    ])
    expect(lignesEcheancier(dossierPaiement({ echeances: [] }), '2026-11-02')).toEqual([])
  })

  it('en souffrance : une échéance passée non réglée (pas celle du jour)', () => {
    const d = dossierPaiement()
    expect(enSouffrance(d, '2026-11-10')).toBe(false)
    expect(enSouffrance(d, '2026-11-11')).toBe(true)
    expect(enSouffrance(dossierPaiement({ echeances: [] }), '2027-12-01')).toBe(false)
  })

  it('statut du dossier : « À régler » tant que seule l’échéance du jour est due, « En retard » ensuite', () => {
    const d = dossierPaiement({ statut: 'en_retard' })
    expect(libelleStatutDossier(d, '2026-11-10')).toBe('À régler')
    expect(libelleStatutDossier(d, '2026-11-11')).toBe('En retard')
    expect(libelleStatutDossier(dossierPaiement({ statut: 'a_jour' }), '2026-11-11')).toBe('À jour')
  })

  it('part réglée du parcours, en pourcentage entier', () => {
    expect(progression(dossierPaiement({ paye: 10000, reste: 100000 }))).toBe(9)
    expect(progression(dossierPaiement({ paye: 110000, reste: 0 }))).toBe(100)
    expect(progression(dossierPaiement({ paye: 0, reste: 0 }))).toBe(100)
  })

  it('changement de mode : nouveau prix global, déjà versé conservé, reste jamais négatif', () => {
    const d = dossierPaiement({ paye: 60000 })
    expect(changement(d, 'mensuel')).toEqual({ total: 120000, dejaVerse: 60000, reste: 60000 })
    expect(changement(dossierPaiement({ paye: 130000 }), 'une_fois')).toEqual({
      total: 100000,
      dejaVerse: 130000,
      reste: 0,
    })
  })
})

describe('téléphone', () => {
  it('numéro ivoirien de 10 chiffres, indicatif +225 facultatif, rendu au format international', () => {
    expect(normaliserTelephone('07 00 00 00 01')).toBe('+2250700000001')
    expect(normaliserTelephone('+225 07.00.00-00-01')).toBe('+2250700000001')
    expect(normaliserTelephone('00225 0700000001')).toBe('+2250700000001')
    expect(normaliserTelephone('  0501020304 ')).toBe('+2250501020304')
  })

  it('affiché par paires de chiffres', () => {
    expect(formaterTelephone('+2250700000001')).toBe('+225 07 00 00 00 01')
    expect(formaterTelephone('')).toBe('')
    expect(formaterTelephone('+33612345678')).toBe('+33612345678')
  })

  it('tout autre format refusé', () => {
    for (const n of ['', '0700', '07000000011', '+33612345678', '+225 7000000', 'abcdefghij', '+2250700000001x']) {
      expect(normaliserTelephone(n)).toBeNull()
    }
  })
})

describe('lien de paiement', () => {
  it('seule une adresse https est suivie', () => {
    expect(urlPaiementSure('https://checkout.cinetpay.com/payment/abc')).toBe(true)
    for (const u of [
      'http://checkout.cinetpay.com/payment/abc',
      'javascript:alert(1)',
      'data:text/html,x',
      '/espace',
      '//pirate.example',
      'https://',
      '',
    ]) {
      expect(urlPaiementSure(u)).toBe(false)
    }
  })
})

describe('parcours gratuit (MOOC)', () => {
  it('distingue l’état gratuit d’un dossier de paiement', () => {
    expect(estGratuit(parcoursGratuit())).toBe(true)
    expect(estGratuit(dossierPaiement())).toBe(false)
    expect(estGratuit(dossierPaiement({ statut: 'dispense' }))).toBe(false)
  })
})
