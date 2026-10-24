import { afterEach, describe, expect, it } from 'vitest'
import { ficheIntendance, ligneIntendance } from '../test/fabriques'
import {
  echeanceADecaler,
  etatEcheanceFiche,
  etatLigne,
  detailAction,
  formaterHorodatage,
  isoHorodatage,
  libelleAction,
  libelleEtat,
  montantSaisi,
  parametresFiltres,
  trier,
  validerDelai,
  validerVirement,
  FILTRES_VIDES,
  type EtatLigne,
  type SaisieVirement,
} from './intendance'

const virement = (autres: Partial<SaisieVirement> = {}): SaisieVirement => ({
  montant: '50000',
  reference: 'VIR-2026-001',
  date: '2026-11-02',
  motif: 'Relevé bancaire du 2 novembre',
  ...autres,
})

describe('état d’une ligne (statut du serveur, blocage, rappel)', () => {
  it('bloqué l’emporte, puis le retard, puis le rappel envoyé sur une ligne à jour', () => {
    expect(etatLigne(ligneIntendance({ statut: 'en_retard', bloque: true }))).toBe('bloque')
    expect(etatLigne(ligneIntendance({ statut: 'en_retard', bloque: false }))).toBe('en_retard')
    expect(etatLigne(ligneIntendance({ statut: 'a_jour', rappel_envoye: true }))).toBe('rappel_envoye')
    expect(etatLigne(ligneIntendance({ statut: 'a_jour' }))).toBe('a_jour')
    expect(etatLigne(ligneIntendance({ statut: 'solde', rappel_envoye: true }))).toBe('solde')
    expect(etatLigne(ligneIntendance({ statut: 'dispense' }))).toBe('dispense')
    expect(etatLigne({ statut: 'a_jour', bloque: false })).toBe('a_jour') // fiche : sans drapeau de rappel
  })

  it('chaque état a un libellé écrit', () => {
    const etats: EtatLigne[] = ['a_jour', 'rappel_envoye', 'en_retard', 'bloque', 'solde', 'dispense']
    expect(etats.map(libelleEtat)).toEqual(['À jour', 'Rappel envoyé', 'En retard', 'Bloqué', 'Soldé', 'Dispensé'])
  })
})

describe('filtres', () => {
  it('seules les valeurs saisies partent, sans blancs', () => {
    expect(parametresFiltres(FILTRES_VIDES)).toEqual({})
    expect(parametresFiltres({ ...FILTRES_VIDES, statut: 'bloque' })).toEqual({ statut: 'bloque' })
    expect(
      parametresFiltres({
        ...FILTRES_VIDES,
        parcours: ' data ',
        mode: 'mensuel',
        statut: 'en_retard',
        du: '2026-10-01',
      }),
    ).toEqual({ parcours: 'data', mode: 'mensuel', statut: 'en_retard', du: '2026-10-01' })
  })
})

describe('tri du tableau', () => {
  const a = ligneIntendance({ dossier: 'A', nom: 'Awa Koné', paye: 10000, reste: 90000, statut: 'a_jour' })
  const b = ligneIntendance({
    dossier: 'B',
    nom: 'bamba Yao',
    paye: 0,
    reste: 100000,
    statut: 'en_retard',
    bloque: true,
    prochaine: { date_limite: '2026-10-15', montant: 10000 },
  })
  const c = ligneIntendance({
    dossier: 'C',
    nom: 'Éric Touré',
    paye: 100000,
    reste: 0,
    statut: 'solde',
    prochaine: null,
  })

  it('par nom (accents et casse ignorés), montants, prochaine échéance, état (le plus urgent d’abord)', () => {
    const ids = (cle: Parameters<typeof trier>[1], sens: 'asc' | 'desc' = 'asc') =>
      trier([c, a, b], cle, sens).map((x) => x.dossier)
    expect(ids('nom')).toEqual(['A', 'B', 'C'])
    expect(ids('nom', 'desc')).toEqual(['C', 'B', 'A'])
    expect(ids('paye')).toEqual(['B', 'A', 'C'])
    expect(ids('reste', 'desc')).toEqual(['B', 'A', 'C'])
    expect(ids('prochaine')).toEqual(['B', 'A', 'C']) // sans échéance : en dernier
    expect(ids('prochaine', 'desc')).toEqual(['A', 'B', 'C'])
    expect(ids('etat')).toEqual(['B', 'A', 'C'])
    expect(ids('parcours')).toEqual(['C', 'A', 'B']) // titres égaux : ordre d’arrivée gardé
  })

  it('sans prochaine échéance (ou sans date) : toujours en dernier, entre elles dans l’ordre reçu', () => {
    const d = ligneIntendance({ dossier: 'D', prochaine: { date_limite: null, montant: 10000 } })
    for (const sens of ['asc', 'desc'] as const) {
      expect(trier([c, a], 'prochaine', sens).map((x) => x.dossier)).toEqual(['A', 'C'])
      expect(trier([a, c], 'prochaine', sens).map((x) => x.dossier)).toEqual(['A', 'C'])
      expect(trier([d, c], 'prochaine', sens).map((x) => x.dossier)).toEqual(['D', 'C'])
    }
  })

  it('ne modifie pas la liste reçue', () => {
    const lignes = [c, a]
    trier(lignes, 'nom', 'asc')
    expect(lignes).toEqual([c, a])
  })
})

describe('saisie d’un virement', () => {
  const AUJOURDHUI = '2026-11-02'

  it('saisie complète : aucune erreur, montant lu sans espaces', () => {
    expect(validerVirement(virement({ montant: '50 000' }), AUJOURDHUI)).toEqual({})
    expect(montantSaisi('50 000')).toBe(50000)
  })

  it('montant vide, nul, décimal ou négatif refusé', () => {
    expect(validerVirement(virement({ montant: '' }), AUJOURDHUI).montant).toBe('Indiquez le montant reçu.')
    for (const m of ['0', '12,5', '-100', 'abc', '1e5']) {
      expect(validerVirement(virement({ montant: m }), AUJOURDHUI).montant).toBe(
        'Montant en francs CFA : un nombre entier positif.',
      )
    }
  })

  it('référence obligatoire (blancs compris), 140 caractères au plus', () => {
    expect(validerVirement(virement({ reference: '  ' }), AUJOURDHUI).reference).toBe(
      'Indiquez la référence du virement.',
    )
    expect(validerVirement(virement({ reference: 'x'.repeat(141) }), AUJOURDHUI).reference).toBe(
      'Référence trop longue : 140 caractères au plus.',
    )
  })

  it('date requise et jamais dans le futur ; motif obligatoire', () => {
    expect(validerVirement(virement({ date: '' }), AUJOURDHUI).date).toBe('Indiquez la date du virement.')
    expect(validerVirement(virement({ date: '2026-11-03' }), AUJOURDHUI).date).toBe(
      'La date du virement ne peut pas être dans le futur.',
    )
    expect(validerVirement(virement({ motif: ' ' }), AUJOURDHUI).motif).toBe('Le motif est obligatoire.')
  })
})

describe('délai accordé', () => {
  it('nouvelle date après aujourd’hui et motif obligatoires', () => {
    expect(validerDelai({ jusquau: '2026-11-20', motif: 'Accord avec la famille' }, '2026-11-02')).toEqual({})
    expect(validerDelai({ jusquau: '', motif: 'x' }, '2026-11-02').jusquau).toBe('Indiquez la nouvelle date limite.')
    expect(validerDelai({ jusquau: '2026-11-02', motif: 'x' }, '2026-11-02').jusquau).toBe(
      'La nouvelle date limite doit être après aujourd’hui.',
    )
    expect(validerDelai({ jusquau: '2026-11-20', motif: '' }, '2026-11-02').motif).toBe('Le motif est obligatoire.')
  })

  it('échéance concernée : la première non couverte', () => {
    expect(echeanceADecaler(ficheIntendance())?.date_limite).toBe('2026-11-10')
    expect(
      echeanceADecaler(
        ficheIntendance({ echeances: [{ date_limite: '2026-10-22', montant: 1, libelle: 'x', couverte: true }] }),
      ),
    ).toBeNull()
  })
})

describe('journal', () => {
  it('actions connues en toutes lettres, autres rendues telles quelles', () => {
    expect(libelleAction('virement_enregistre')).toBe('Virement enregistré')
    expect(libelleAction('delai_accorde')).toBe('Délai accordé')
    expect(libelleAction('paiement_confirme')).toBe('Paiement en ligne confirmé')
    expect(libelleAction('mode')).toBe('Mode de paiement changé')
    expect(libelleAction('dispense_parcours_gratuit')).toBe('Dispensé : parcours devenu gratuit')
    expect(libelleAction('autre_chose')).toBe('autre_chose')
  })

  it('détail avant/après en clair : virement, paiement en ligne, mode, délai, dispense', () => {
    const xof = (t: string) => t.replace(/(\d) (?=\d)/g, '$1 ').replace(/ FCFA/g, ' FCFA')
    expect(
      detailAction({
        action: 'virement_enregistre',
        avant: { paye: 0, statut: 'en_retard' },
        apres: { paye: 10000, statut: 'a_jour', montant: 10000, reference: 'VIR-2210', date_paiement: '2026-10-22' },
      }),
    ).toEqual([
      xof('10 000 FCFA · réf. VIR-2210 · versé le 22 octobre 2026'),
      xof('Payé : 0 FCFA → 10 000 FCFA'),
      'Statut : En retard → À jour',
    ])
    expect(
      detailAction({
        action: 'paiement_confirme',
        avant: { statut: 'en_attente', paye: 0, montant: 50000 },
        apres: { statut: 'confirme', paye: 50000, montant: 50000 },
      }),
    ).toEqual([xof('50 000 FCFA'), xof('Payé : 0 FCFA → 50 000 FCFA')])
    expect(
      detailAction({ action: 'mode', avant: { mode: 'une_fois', echeances: [] }, apres: { mode: 'mensuel' } }),
    ).toEqual(['En une fois → Chaque mois'])
    expect(
      detailAction({
        action: 'delai_accorde',
        avant: { delai_jusqu_au: null, statut: 'en_retard' },
        apres: { delai_jusqu_au: '2026-11-20', statut: 'a_jour' },
      }),
    ).toEqual(['Délai : aucun → 20 novembre 2026', 'Statut : En retard → À jour'])
    expect(
      detailAction({
        action: 'dispense_parcours_gratuit',
        avant: { statut: 'en_retard', paye: 0 },
        apres: { statut: 'dispense' },
      }),
    ).toEqual(['Statut : En retard → Dispensé'])
  })

  it('détail : contenu inattendu ignoré, jamais d’erreur', () => {
    expect(detailAction({ action: 'mode', avant: null, apres: 'x' })).toEqual([])
    expect(detailAction({ action: 'mode', avant: { mode: 'turbo' }, apres: { mode: 'mensuel' } })).toEqual([])
    expect(detailAction({ action: 'autre', avant: {}, apres: {} })).toEqual([])
    expect(detailAction({ action: 'delai_accorde', avant: {}, apres: { delai_jusqu_au: 'demain' } })).toEqual([])
    expect(detailAction({ action: 'delai_accorde', avant: {}, apres: {} })).toEqual([])
    expect(
      detailAction({
        action: 'delai_accorde',
        avant: { delai_jusqu_au: '2026-11-20' },
        apres: { delai_jusqu_au: '2026-12-05' },
      }),
    ).toEqual(['Délai : 20 novembre 2026 → 5 décembre 2026'])
    expect(detailAction({ action: 'virement_enregistre', avant: [], apres: { statut: 'a_jour' } })).toEqual([])
  })

  it('horodatage à la française, vide s’il est illisible', () => {
    expect(formaterHorodatage('2026-11-03 21:12:00.123456')).toBe('3 nov. 2026, 21:12')
    expect(formaterHorodatage(null)).toBe('')
    expect(formaterHorodatage('n’importe quoi')).toBe('')
  })

  describe('heure du serveur (Abidjan, UTC), quel que soit le fuseau du navigateur', () => {
    const fuseau = process.env.TZ
    afterEach(() => {
      process.env.TZ = fuseau
    })

    it('New York, Tokyo : même heure affichée, attribut datetime ISO en UTC', () => {
      for (const tz of ['America/New_York', 'Asia/Tokyo']) {
        process.env.TZ = tz
        expect(formaterHorodatage('2026-11-03 21:12:00.123456')).toBe('3 nov. 2026, 21:12')
        expect(isoHorodatage('2026-11-03 21:12:00.123456')).toBe('2026-11-03T21:12:00Z')
      }
      expect(isoHorodatage(null)).toBeUndefined()
      expect(isoHorodatage('n’importe quoi')).toBeUndefined()
    })

    it('Paris : une heure dans le trou du passage à l’heure d’été n’est pas décalée', () => {
      process.env.TZ = 'Europe/Paris'
      expect(formaterHorodatage('2026-03-29 02:30:00')).toBe('29 mars 2026, 02:30')
    })
  })
})

describe('échéance de la fiche', () => {
  const e = (date_limite: string, couverte = false) => ({ date_limite, montant: 50000, libelle: 'Échéance', couverte })
  it('dossier actif : réglée, en retard, due aujourd’hui, à venir', () => {
    expect(etatEcheanceFiche(e('2026-10-10', true), '2026-11-02', false)).toBe('reglee')
    expect(etatEcheanceFiche(e('2026-10-10'), '2026-11-02', false)).toBe('en_retard')
    expect(etatEcheanceFiche(e('2026-11-02'), '2026-11-02', false)).toBe('aujourdhui')
  })
  it('dossier dispensé : ce qui n’est pas couvert est dispensé, jamais en retard', () => {
    expect(etatEcheanceFiche(e('2026-10-10', true), '2026-11-02', true)).toBe('reglee')
    expect(etatEcheanceFiche(e('2026-10-10'), '2026-11-02', true)).toBe('dispensee')
    expect(etatEcheanceFiche(e('2026-11-02'), '2026-11-02', true)).toBe('dispensee')
  })
})
