import { describe, expect, it } from 'vitest'
import { reglagesEffectifs } from '../test/fabriques'
import {
  formaterReste,
  libelleActionSouffrance,
  libelleChamp,
  libelleProvenance,
  libelleTypeExercice,
  lignesEquipe,
  lignesReglages,
  valeurLisible,
} from './pilotage'

describe('réglages appliqués', () => {
  it('libellés des champs, des étapes, des types et des provenances (inconnus laissés tels quels)', () => {
    expect(libelleChamp('nb_pairs')).toBe('Relectures par les pairs')
    expect(libelleChamp('etape.formateur')).toBe('Étape : Formateur')
    expect(libelleChamp('etape.oracle')).toBe('Étape : oracle')
    expect(libelleChamp('inconnu')).toBe('inconnu')
    expect(libelleTypeExercice('livrable')).toBe('Livrable')
    expect(libelleTypeExercice('autre')).toBe('autre')
    expect(libelleProvenance('suppleants')).toBe('Suppléants')
    expect(libelleProvenance('autre')).toBe('autre')
  })

  it('valeurs lisibles : étapes, booléens, nombres, jours, textes et formes inattendues', () => {
    expect(valeurLisible('etape.pairs', { active: false, delai_heures: 72, expiration: 'passer' })).toBe('Inactive')
    expect(valeurLisible('etape.formateur', { active: true, delai_heures: 48, expiration: 'escalader' })).toBe(
      'Active · délai 48 h · à l’expiration : escalader',
    )
    expect(valeurLisible('etape.ia', { active: true, delai_heures: 1, expiration: 'neuve' })).toBe(
      'Active · délai 1 h · à l’expiration : neuve',
    )
    expect(valeurLisible('anonymat', true)).toBe('Oui')
    expect(valeurLisible('anonymat', false)).toBe('Non')
    expect(valeurLisible('seuil_reussite', 10.5)).toBe('10,5')
    expect(valeurLisible('pairs_attente_max_jours', 7)).toBe('7 jours')
    expect(valeurLisible('pairs_attente_max_jours', 1)).toBe('1 jour')
    expect(valeurLisible('note', 'vingt')).toBe('vingt')
    expect(valeurLisible('liste', [1, 2])).toBe('[1,2]')
    expect(valeurLisible('rien', undefined)).toBe('')
  })

  it('lignes dans l’ordre de la chaîne, chacune avec son origine', () => {
    const lignes = lignesReglages(reglagesEffectifs())
    expect(lignes.map((l) => l.champ)).toEqual(['nb_pairs', 'note_sur', 'etape.ia', 'etape.formateur', 'zeta'])
    expect(lignes[1]).toEqual({ champ: 'note_sur', libelle: 'Note sur', valeur: '10', source: 'cohorte COH' })
    const inconnus = reglagesEffectifs({
      chaine: { b: { valeur: 1, source: 's' }, a: { valeur: 2, source: 's' }, nb_pairs: { valeur: 3, source: 's' } },
    })
    expect(lignesReglages(inconnus).map((l) => l.champ)).toEqual(['nb_pairs', 'a', 'b'])
  })

  it('équipe en lignes, provenance absente laissée vide', () => {
    expect(lignesEquipe(reglagesEffectifs().equipe)).toEqual([
      { champ: 'titulaires', libelle: 'Titulaires', valeur: 'formateur@exemple.ci', source: 'cohorte COH' },
      { champ: 'suppleants', libelle: 'Suppléants', valeur: '', source: '' },
      { champ: 'responsable', libelle: 'Responsable', valeur: 'responsable@exemple.ci', source: 'réglages' },
    ])
  })
})

describe('copies en souffrance', () => {
  it('action prévue et temps restant', () => {
    expect(libelleActionSouffrance('rien')).toBe('Attend une décision (rappel quotidien)')
    expect(libelleActionSouffrance('publier_provisoire')).toBe('Publication d’une note provisoire')
    expect(libelleActionSouffrance('autre')).toBe('autre')
    expect(formaterReste(null)).toBe('')
    expect(formaterReste(0)).toBe('imminente')
    expect(formaterReste(4.2)).toBe('dans 5 h')
    expect(formaterReste(48)).toBe('dans 2 j')
    expect(formaterReste(51)).toBe('dans 2 j 3 h')
  })
})
