import { describe, expect, it } from 'vitest'
import { critere, grille, vueCopie } from '../test/fabriques'
import {
  GENERAL,
  chargeCorrection,
  copieApresPublication,
  libelleStatut,
  niveauParTouche,
  propositionRetenue,
  saisieInitiale,
} from './correction'

describe('copie à corriger', () => {
  it('libellé du statut, le code brut à défaut', () => {
    expect(libelleStatut('a_corriger')).toBe('à corriger')
    expect(libelleStatut('provisoire')).toBe('note provisoire publiée')
    expect(libelleStatut('en_relecture')).toBe('en_relecture')
  })

  it("copie signalée (injection) : la proposition de l'IA est écartée", () => {
    const vue = vueCopie()
    expect(propositionRetenue(vue)).toBe(vue.ia)
    expect(propositionRetenue({ ...vue, signalement: 'copie signalée' })).toBeNull()
    expect(propositionRetenue({ ...vue, ia: null })).toBeNull()
  })

  it('le formateur retrouve sa correction ; le commentaire général est séparé', () => {
    const formateur = {
      niveaux: { pertinence: 1 },
      commentaires: { [GENERAL]: 'Bien.', rigueur: 'Sources ?' },
      auteur: 'f@exemple.ci',
      au_nom_de: null,
    }
    expect(saisieInitiale(vueCopie({ formateur }))).toEqual({
      niveaux: { pertinence: 1 },
      commentaires: { rigueur: 'Sources ?' },
      general: 'Bien.',
    })
    expect(saisieInitiale(vueCopie({ formateur: { ...formateur, commentaires: {} } })).general).toBe('')
  })

  it('saisie vierge sans correction, ou pour un juré', () => {
    const vide = { niveaux: {}, commentaires: {}, general: '' }
    expect(saisieInitiale(vueCopie())).toEqual(vide)
    const formateur = { niveaux: { pertinence: 1 }, commentaires: {}, auteur: 'f', au_nom_de: null }
    expect(saisieInitiale(vueCopie({ role: 'jury', formateur }))).toEqual(vide)
  })

  it('la charge envoyée réunit niveaux et commentaires, général compris', () => {
    const saisie = { niveaux: { pertinence: 2 }, commentaires: { rigueur: 'x' }, general: 'Bien.' }
    expect(chargeCorrection('C2', saisie)).toEqual({
      copie: 'C2',
      niveaux: { pertinence: 2 },
      commentaires: { rigueur: 'x', general: 'Bien.' },
    })
  })
})

describe('après publication', () => {
  it('la copie suivante si elle reste à corriger, sinon une autre que la courante', () => {
    expect(copieApresPublication(['C1', 'C3'], 'C3', 'C2')).toBe('C3')
    expect(copieApresPublication(['C1', 'C2'], 'C3', 'C2')).toBe('C1')
    expect(copieApresPublication(['C1'], undefined, 'C2')).toBe('C1')
    expect(copieApresPublication(['C2'], undefined, 'C2')).toBeUndefined()
  })
})

describe('touches 1 à 9', () => {
  const g = grille(critere('pertinence', 50), critere('rigueur', 50))

  it('niveau du critère actif, puis le critère suivant devient actif', () => {
    expect(niveauParTouche(g, 'pertinence', '3')).toEqual({ code: 'pertinence', indice: 2, actif: 'rigueur' })
    expect(niveauParTouche(g, 'rigueur', '4')).toEqual({ code: 'rigueur', indice: 3, actif: 'rigueur' })
  })

  it('sans critère actif connu : le premier', () => {
    expect(niveauParTouche(g, '', '1')).toEqual({ code: 'pertinence', indice: 0, actif: 'rigueur' })
  })

  it('touche hors des niveaux, autre touche ou grille vide : rien', () => {
    expect(niveauParTouche(g, 'pertinence', '5')).toBeNull()
    expect(niveauParTouche(g, 'pertinence', '0')).toBeNull()
    expect(niveauParTouche(g, 'pertinence', 'j')).toBeNull()
    expect(niveauParTouche(grille(), '', '1')).toBeNull()
  })
})
