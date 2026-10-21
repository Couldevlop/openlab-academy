// Dépôts sur l'API d'évaluation de Frappe : un point d'API par opération, réponse validée par son schéma.
import type { DepotCorrection, DepotRelecture, DepotRetour } from '../../application/ports'
import type { ChargeCorrection } from '../../domaine/correction'
import type { SaisieRelecture } from '../../domaine/relecture'
import type { ClientFrappe } from './client'
import {
  sansResultat,
  schemaFile,
  schemaMesRelectures,
  schemaPublication,
  schemaRelecture,
  schemaResultatLot,
  schemaRetour,
  schemaVueCopie,
} from './schemas'

export class DepotCorrectionFrappe implements DepotCorrection {
  constructor(private readonly client: ClientFrappe) {}

  file(exercice?: string) {
    return this.client.lire('file_correction', exercice ? { exercice } : {}, schemaFile)
  }

  copie(copie: string) {
    return this.client.lire('copie_a_corriger', { copie }, schemaVueCopie)
  }

  async corriger(charge: ChargeCorrection) {
    await this.client.ecrire('corriger', { ...charge }, sansResultat)
  }

  async publier(copie: string) {
    return (await this.client.ecrire('publier', { copie }, schemaPublication)).note
  }

  validerLot(copies: string[], etPublier: boolean) {
    return this.client.ecrire('valider_lot', { copies, et_publier: etPublier ? 1 : 0 }, schemaResultatLot)
  }
}

export class DepotRelectureFrappe implements DepotRelecture {
  constructor(private readonly client: ClientFrappe) {}

  mesRelectures() {
    return this.client.lire('mes_relectures', undefined, schemaMesRelectures)
  }

  relecture(relecture: string) {
    return this.client.lire('relecture', { relecture_id: relecture }, schemaRelecture)
  }

  async enregistrer(relecture: string, saisie: SaisieRelecture) {
    const params = { relecture_id: relecture, niveaux: saisie.niveaux, commentaires: saisie.conseils }
    await this.client.ecrire('enregistrer_relecture', params, sansResultat)
  }
}

export class DepotRetourFrappe implements DepotRetour {
  constructor(private readonly client: ClientFrappe) {}

  monRetour(copie: string) {
    return this.client.lire('mon_retour', { copie }, schemaRetour)
  }
}
