import { describe, expect, it, vi } from 'vitest'
import { ErreurDepot } from '../../application/erreurs'
import { fileCorrection, resumeRelecture, retour, critereRetour, vueCopie, vueRelecture } from '../../test/fabriques'
import { ClientFrappe, type RequeteFrappe } from './client'
import { DepotCorrectionFrappe, DepotRelectureFrappe, DepotRetourFrappe } from './depots'

const RACINE = 'openlab_academy.entrypoints.evaluation_api.'

/** Requête simulée : rend la réponse prévue et garde les appels (méthode, verbe, paramètres). */
function serveur(reponse: unknown) {
  const requete = vi.fn<RequeteFrappe>(async () => reponse)
  const appels = () => requete.mock.calls.map(([o]) => [o.url.slice(RACINE.length), o.method, o.params])
  return { client: new ClientFrappe(requete), appels }
}

const invalide = (promesse: Promise<unknown>) => expect(promesse).rejects.toMatchObject({ sorte: 'reponse_invalide' })

describe('dépôt de correction (Frappe)', () => {
  it('file de correction, filtrée par exercice ou non', async () => {
    const file = fileCorrection(['C1', 'C2'], [['C1', 'C2']])
    const { client, appels } = serveur(file)
    const depot = new DepotCorrectionFrappe(client)
    expect(await depot.file('ASG-1')).toEqual(file)
    await depot.file()
    expect(appels()).toEqual([
      ['file_correction', 'GET', { exercice: 'ASG-1' }],
      ['file_correction', 'GET', {}],
    ])
  })

  it('copie à corriger, avec ou sans IA, correction et délégation', async () => {
    const formateur = { niveaux: { pertinence: 1 }, commentaires: { general: 'Bien.' }, auteur: 'f', au_nom_de: 'g' }
    const vue = vueCopie({
      formateur,
      au_nom_de: 'g@exemple.ci',
      auto_evaluation: { pertinence: 2 },
      echeance: '2026-11-03 21:12:00',
    })
    const { client, appels } = serveur(vue)
    expect(await new DepotCorrectionFrappe(client).copie('C2')).toEqual(vue)
    expect(appels()).toEqual([['copie_a_corriger', 'GET', { copie: 'C2' }]])
    const sansIa = vueCopie({ ia: null, role: 'jury' })
    expect(await new DepotCorrectionFrappe(serveur(sansIa).client).copie('C2')).toEqual(sansIa)
  })

  it('copie malformée : erreur typée', async () => {
    await invalide(new DepotCorrectionFrappe(serveur({ ...vueCopie(), role: 'pair' }).client).copie('C2'))
    await invalide(new DepotCorrectionFrappe(serveur({ ...vueCopie(), note_sur: '20' }).client).copie('C2'))
    const { grille: _grille, ...sansGrille } = vueCopie()
    await invalide(new DepotCorrectionFrappe(serveur(sansGrille).client).copie('C2'))
  })

  it('corriger et publier', async () => {
    const { client, appels } = serveur(null)
    const charge = { copie: 'C2', niveaux: { pertinence: 2 }, commentaires: { general: 'Bien.' } }
    await new DepotCorrectionFrappe(client).corriger(charge)
    expect(appels()).toEqual([['corriger', 'POST', charge]])
    const publication = serveur({ copie: 'C2', note: 16.5 })
    expect(await new DepotCorrectionFrappe(publication.client).publier('C2')).toBe(16.5)
    expect(publication.appels()).toEqual([['publier', 'POST', { copie: 'C2' }]])
    await invalide(new DepotCorrectionFrappe(serveur({ copie: 'C2' }).client).publier('C2'))
  })

  it('valider un lot, avec ou sans publication', async () => {
    const { client, appels } = serveur({ copies: ['C1', 'C3'], publiees: ['C1', 'C3'] })
    const depot = new DepotCorrectionFrappe(client)
    expect(await depot.validerLot(['C1', 'C3'], true)).toEqual({ copies: ['C1', 'C3'], publiees: ['C1', 'C3'] })
    await depot.validerLot(['C1'], false)
    expect(appels()).toEqual([
      ['valider_lot', 'POST', { copies: ['C1', 'C3'], et_publier: 1 }],
      ['valider_lot', 'POST', { copies: ['C1'], et_publier: 0 }],
    ])
  })
})

describe('dépôt de relecture (Frappe)', () => {
  it('mes relectures et une relecture', async () => {
    const liste = [resumeRelecture('R1'), resumeRelecture('R2', { echeance: null })]
    const { client, appels } = serveur(liste)
    expect(await new DepotRelectureFrappe(client).mesRelectures()).toEqual(liste)
    const vue = vueRelecture()
    const lecture = serveur(vue)
    expect(await new DepotRelectureFrappe(lecture.client).relecture('R1')).toEqual(vue)
    expect([...appels(), ...lecture.appels()]).toEqual([
      ['mes_relectures', 'GET', undefined],
      ['relecture', 'GET', { relecture_id: 'R1' }],
    ])
    await invalide(new DepotRelectureFrappe(serveur([{ relecture: 'R1' }]).client).mesRelectures())
    await invalide(new DepotRelectureFrappe(serveur({ ...vue, anonymat_garanti: 'oui' }).client).relecture('R1'))
  })

  it('enregistrer : niveaux et conseils envoyés comme commentaires', async () => {
    const { client, appels } = serveur(null)
    await new DepotRelectureFrappe(client).enregistrer('R1', { niveaux: { a: 1 }, conseils: { a: 'Bien.' } })
    expect(appels()).toEqual([
      ['enregistrer_relecture', 'POST', { relecture_id: 'R1', niveaux: { a: 1 }, commentaires: { a: 'Bien.' } }],
    ])
  })
})

describe('dépôt de retour (Frappe)', () => {
  it('mon retour, note publiée ou en attente', async () => {
    const publie = retour({
      note: 15,
      note_sur: 20,
      reussite: true,
      criteres: [critereRetour('a', 2, { auto_evaluation: 1 })],
    })
    const { client, appels } = serveur(publie)
    expect(await new DepotRetourFrappe(client).monRetour('C1')).toEqual(publie)
    expect(appels()).toEqual([['mon_retour', 'GET', { copie: 'C1' }]])
    const masque = retour({ masquee: true, message: 'Votre note sera visible…' })
    expect(await new DepotRetourFrappe(serveur(masque).client).monRetour('C1')).toEqual(masque)
  })

  it('retour malformé : erreur typée, jamais un affichage silencieux', async () => {
    const erreur = await new DepotRetourFrappe(serveur({ ...retour(), note: '15' }).client)
      .monRetour('C1')
      .catch((e: unknown) => e)
    expect(erreur).toBeInstanceOf(ErreurDepot)
    expect((erreur as ErreurDepot).details).toEqual([expect.stringMatching(/^mon_retour\.note : /)])
  })
})
