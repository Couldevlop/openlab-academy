import { describe, expect, it, vi } from 'vitest'
import { ErreurDepot } from '../../application/erreurs'
import {
  critereRetour,
  dossierPaiement,
  ficheIntendance,
  fileCorrection,
  resumeFinances,
  vueIntendance,
  resumeRelecture,
  retour,
  vueCopie,
  vueRelecture,
} from '../../test/fabriques'
import { ClientFrappe, type RequeteFrappe } from './client'
import {
  DepotCorrectionFrappe,
  DepotIntendanceFrappe,
  DepotPaiementFrappe,
  DepotRelectureFrappe,
  DepotRetourFrappe,
} from './depots'

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

describe('dépôt de paiement (Frappe)', () => {
  const RACINE_PAIEMENT = 'openlab_academy.entrypoints.paiement_api.'

  function serveurPaiement(reponse: unknown) {
    const requete = vi.fn<RequeteFrappe>(async () => reponse)
    const appels = () => requete.mock.calls.map(([o]) => [o.url.slice(RACINE_PAIEMENT.length), o.method, o.params])
    return { depot: new DepotPaiementFrappe(new ClientFrappe(requete, RACINE_PAIEMENT)), appels }
  }

  it('mon dossier (GET), choix du mode (POST) et paiement (POST) sur l’API de paiement', async () => {
    const d = dossierPaiement({ prochaine: { date_limite: null, montant: 10000 } })
    const lecture = serveurPaiement(d)
    expect(await lecture.depot.monDossier('C1')).toEqual(d)
    expect(await lecture.depot.choisirMode('C1', 'mensuel', '+2250700000002')).toEqual(d)
    expect(lecture.appels()).toEqual([
      ['mon_dossier', 'GET', { cours: 'C1' }],
      ['choisir_mode', 'POST', { cours: 'C1', mode: 'mensuel', telephone: '+2250700000002' }],
    ])
    const paiement = serveurPaiement({ url: 'https://checkout.cinetpay.com/payment/abc' })
    expect(await paiement.depot.payer('C1')).toBe('https://checkout.cinetpay.com/payment/abc')
    expect(paiement.appels()).toEqual([['payer', 'POST', { cours: 'C1' }]])
  })

  it('dossier soldé ou dispensé : aucune prochaine échéance', async () => {
    const d = dossierPaiement({ statut: 'solde', prochaine: null, reste: 0 })
    expect(await serveurPaiement(d).depot.monDossier('C1')).toEqual(d)
  })

  it('parcours gratuit : état calme reconnu, jamais pris pour un dossier', async () => {
    const g = { cours: 'initiation-ia', titre: 'Initiation à l’IA', gratuit: true }
    expect(await serveurPaiement(g).depot.monDossier('initiation-ia')).toEqual(g)
    await invalide(serveurPaiement({ ...g, gratuit: false }).depot.monDossier('initiation-ia'))
    await invalide(serveurPaiement({ ...g, titre: 3 }).depot.monDossier('initiation-ia'))
  })

  it('réponse malformée : erreur typée', async () => {
    const invalidePaiement = (r: unknown) => invalide(serveurPaiement(r).depot.monDossier('C1'))
    await invalidePaiement({ ...dossierPaiement(), mode: 'trimestriel' })
    await invalidePaiement({ ...dossierPaiement(), statut: 'bloque' })
    await invalidePaiement({ ...dossierPaiement(), paye: '0' })
    const { bloque: _b, ...sansBlocage } = dossierPaiement()
    await invalidePaiement(sansBlocage)
    await invalide(serveurPaiement({ url: 42 }).depot.payer('C1'))
  })
})

describe('dépôt de l’intendance (Frappe)', () => {
  const RACINE_PAIEMENT = 'openlab_academy.entrypoints.paiement_api.'

  function serveurIntendance(reponse: unknown) {
    const requete = vi.fn<RequeteFrappe>(async () => reponse)
    const appels = () => requete.mock.calls.map(([o]) => [o.url.slice(RACINE_PAIEMENT.length), o.method, o.params])
    return { depot: new DepotIntendanceFrappe(new ClientFrappe(requete, RACINE_PAIEMENT)), appels }
  }

  it('vue filtrée, fiche et résumé en GET, réponses validées', async () => {
    const vue = vueIntendance()
    const lecture = serveurIntendance(vue)
    expect(await lecture.depot.intendance({ parcours: 'C1', statut: 'en_retard' })).toEqual(vue)
    expect(lecture.appels()).toEqual([['intendance', 'GET', { parcours: 'C1', statut: 'en_retard' }]])
    const f = ficheIntendance({ delai_jusqu_au: '2026-11-20', telephone: '' })
    const fiche = serveurIntendance(f)
    expect(await fiche.depot.fiche('DP-0001')).toEqual(f)
    expect(fiche.appels()).toEqual([['fiche', 'GET', { dossier: 'DP-0001' }]])
    const r = resumeFinances({ evolution_pct: null, taux_recouvrement: null })
    const resume = serveurIntendance(r)
    expect(await resume.depot.resume()).toEqual(r)
    expect(resume.appels()).toEqual([['resume', 'GET', undefined]])
  })

  it('virement et délai en POST (jeton CSRF joint par la requête Frappe)', async () => {
    const { depot, appels } = serveurIntendance(null)
    await depot.enregistrerVirement('DP-1', {
      montant: 50000,
      reference: 'VIR-1',
      date_paiement: '2026-11-02',
      motif: 'Relevé',
    })
    await depot.accorderDelai('DP-1', '2026-11-20', 'Accord')
    expect(appels()).toEqual([
      [
        'enregistrer_virement',
        'POST',
        { dossier: 'DP-1', montant: 50000, reference: 'VIR-1', date_paiement: '2026-11-02', motif: 'Relevé' },
      ],
      ['accorder_delai', 'POST', { dossier: 'DP-1', jusqu_au: '2026-11-20', motif: 'Accord' }],
    ])
  })

  it('lien d’export : point de l’API avec les filtres encodés', () => {
    const { depot } = serveurIntendance(null)
    expect(depot.lienExport({})).toBe('/api/method/openlab_academy.entrypoints.paiement_api.export_intendance')
    expect(depot.lienExport({ parcours: 'data & ia', au: '2026-10-31' })).toBe(
      '/api/method/openlab_academy.entrypoints.paiement_api.export_intendance?parcours=data+%26+ia&au=2026-10-31',
    )
  })

  it('réponse malformée : erreur typée', async () => {
    await invalide(serveurIntendance({ ...vueIntendance(), tronque: 'non' }).depot.intendance({}))
    const ligne = { ...vueIntendance().lignes[0], rappel_envoye: undefined }
    await invalide(serveurIntendance({ ...vueIntendance(), lignes: [ligne] }).depot.intendance({}))
    await invalide(serveurIntendance({ ...ficheIntendance(), journal: [{ acteur: 1 }] }).depot.fiche('D'))
    await invalide(serveurIntendance({ ...resumeFinances(), modes: { une_fois: 1 } }).depot.resume())
  })
})
