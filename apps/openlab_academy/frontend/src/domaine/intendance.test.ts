import { describe, expect, it } from 'vitest'
import { ficheIntendance, ligneIntendance } from '../test/fabriques'
import {
  echeanceADecaler,
  etatLigne,
  formaterHorodatage,
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
    expect(libelleAction('autre_chose')).toBe('autre_chose')
  })

  it('horodatage à la française, vide s’il est illisible', () => {
    expect(formaterHorodatage('2026-11-03 21:12:00.123456')).toBe('3 nov. 2026, 21:12')
    expect(formaterHorodatage(null)).toBe('')
    expect(formaterHorodatage('n’importe quoi')).toBe('')
  })
})
