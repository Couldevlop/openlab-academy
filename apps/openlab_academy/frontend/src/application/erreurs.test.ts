import { describe, expect, it } from 'vitest'
import { ACCES_REFUSE, ErreurDepot, HORS_LIGNE, REPONSE_INVALIDE, TROP_DE_DEMANDES, messageErreur } from './erreurs'

describe('erreurs des dépôts', () => {
  it('un message clair par sorte d’erreur', () => {
    expect(messageErreur(new ErreurDepot('trop_de_demandes'))).toBe(TROP_DE_DEMANDES)
    expect(messageErreur(new ErreurDepot('acces_refuse'))).toBe(ACCES_REFUSE)
    expect(messageErreur(new ErreurDepot('hors_ligne'))).toBe(HORS_LIGNE)
    expect(messageErreur(new ErreurDepot('reponse_invalide', ['copie : attendu une chaîne']))).toBe(REPONSE_INVALIDE)
  })

  it('un refus métier donne les motifs du serveur', () => {
    expect(messageErreur(new ErreurDepot('refus', ['un commentaire est obligatoire', 'niveau inconnu']))).toBe(
      'un commentaire est obligatoire niveau inconnu',
    )
  })

  it('une erreur imprévue est présentée comme une panne', () => {
    expect(messageErreur(new TypeError('Failed to fetch'))).toBe(HORS_LIGNE)
    expect(messageErreur(undefined)).toBe(HORS_LIGNE)
  })

  it("l'erreur garde sa sorte et ses détails", () => {
    const e = new ErreurDepot('reponse_invalide', ['a', 'b'])
    expect(e).toBeInstanceOf(Error)
    expect(e.name).toBe('ErreurDepot')
    expect(e.message).toBe('reponse_invalide : a ; b')
    expect(new ErreurDepot('hors_ligne').message).toBe('hors_ligne')
  })
})
