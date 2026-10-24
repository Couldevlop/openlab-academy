// Dépôts sur les API de Frappe (évaluation, paiement) : un point d'API par opération, réponse validée par son schéma.
import type {
  DepotCorrection,
  DepotIntendance,
  DepotPaiement,
  DepotPilotage,
  DepotRelecture,
  DepotRetour,
  Virement,
} from '../../application/ports'
import type { ChargeCorrection } from '../../domaine/correction'
import type { Mode } from '../../domaine/paiement'
import type { SaisieRelecture } from '../../domaine/relecture'
import { RACINE_PAIEMENT, type ClientFrappe } from './client'
import {
  sansResultat,
  schemaDossierPaiement,
  schemaFicheIntendance,
  schemaMonPaiement,
  schemaFile,
  schemaMesRelectures,
  schemaPaiement,
  schemaResumeFinances,
  schemaSansRetour,
  schemaVueIntendance,
  schemaPublication,
  schemaRelecture,
  schemaResultatLot,
  schemaRetour,
  schemaVueCopie,
  schemaAccuseDepot,
  schemaReglagesEffectifs,
  schemaSouffrances,
  schemaVersionTexte,
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

  versionPrecedente(copie: string, precedente: string) {
    return this.client.lire('version_precedente', { copie, precedente }, schemaVersionTexte)
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

  accuse(copie: string) {
    return this.client.lire('accuse_depot', { copie }, schemaAccuseDepot)
  }
}

/** API de pilotage de l'évaluation : réservée par le serveur au super administrateur et au responsable pédagogique. */
export class DepotPilotageFrappe implements DepotPilotage {
  constructor(private readonly client: ClientFrappe) {}

  async souffrances() {
    return (await this.client.lire('copies_en_souffrance', undefined, schemaSouffrances)).copies
  }

  reglagesEffectifs(exercice: string, cohorte?: string) {
    const params = cohorte ? { exercice, cohorte } : { exercice }
    return this.client.lire('reglages_effectifs', params, schemaReglagesEffectifs)
  }
}

/** API de paiement : le dossier est toujours celui de l'utilisateur de la session pour le parcours demandé. */
export class DepotPaiementFrappe implements DepotPaiement {
  constructor(private readonly client: ClientFrappe) {}

  monDossier(cours: string) {
    return this.client.lire('mon_dossier', { cours }, schemaMonPaiement)
  }

  choisirMode(cours: string, mode: Mode, telephone: string) {
    return this.client.ecrire('choisir_mode', { cours, mode, telephone }, schemaDossierPaiement)
  }

  async payer(cours: string) {
    return (await this.client.ecrire('payer', { cours }, schemaPaiement)).url
  }
}

/** API des agents : le serveur vérifie le rôle (intendant ou administrateur) et journalise l'acteur de la session. */
export class DepotIntendanceFrappe implements DepotIntendance {
  constructor(private readonly client: ClientFrappe) {}

  intendance(filtres: Record<string, string>) {
    return this.client.lire('intendance', filtres, schemaVueIntendance)
  }

  fiche(dossier: string) {
    return this.client.lire('fiche', { dossier }, schemaFicheIntendance)
  }

  async enregistrerVirement(dossier: string, v: Virement) {
    await this.client.ecrire('enregistrer_virement', { dossier, ...v }, schemaSansRetour)
  }

  async accorderDelai(dossier: string, jusquau: string, motif: string) {
    await this.client.ecrire('accorder_delai', { dossier, jusqu_au: jusquau, motif }, schemaSansRetour)
  }

  /** Téléchargement direct (GET, même origine, cookie de session) : aucune donnée ne transite par l'écran. */
  lienExport(filtres: Record<string, string>) {
    const requete = new URLSearchParams(filtres).toString()
    return `/api/method/${RACINE_PAIEMENT}export_intendance${requete ? `?${requete}` : ''}`
  }

  resume() {
    return this.client.lire('resume', undefined, schemaResumeFinances)
  }
}
