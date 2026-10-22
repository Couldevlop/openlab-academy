// Schémas des réponses de l'API d'évaluation (openlab_academy/entrypoints/evaluation_api.py et les cas d'usage
// Python qu'elle appelle) : une réponse d'une autre forme est refusée à la frontière, jamais affichée à moitié.
import * as z from 'zod/mini'
import type { FileCorrection, ResultatLot, VueCopie } from '../../domaine/correction'
import type { Grille } from '../../domaine/grille'
import type { DossierPaiement } from '../../domaine/paiement'
import type { ResumeRelecture, VueRelecture } from '../../domaine/relecture'
import type { Retour } from '../../domaine/retour'

const texte = z.string()
const date = z.nullable(z.string()) // « 2026-11-03 21:12:00 », comme Frappe sérialise un datetime
const indice = z.int()
const niveaux = z.record(z.string(), indice)
const textes = z.record(z.string(), texte)
const role = z.enum(['formateur', 'jury'])

// Grille.vers_dict()
export const schemaGrille: z.ZodMiniType<Grille> = z.object({
  criteres: z.array(
    z.object({
      code: texte,
      libelle: texte,
      description: texte,
      poids: z.number(),
      niveaux: z.array(z.object({ libelle: texte, descripteur: texte, points: z.number() })),
      controles: z.array(texte),
    }),
  ),
})

// ConsulterCorrection.file
export const schemaFile: z.ZodMiniType<FileCorrection> = z.object({
  copies: z.array(
    z.object({
      copie: texte,
      apprenant: texte,
      exercice: texte,
      cohorte: texte,
      version: indice,
      statut: texte,
      etape: texte,
      echeance: date,
      role,
      confiance: z.nullable(z.number()),
      ecarts: z.array(texte),
      signalee: z.boolean(),
      corrigee: z.boolean(),
    }),
  ),
  lots: z.array(z.array(texte)),
})

// ConsulterCorrection.copie
export const schemaVueCopie: z.ZodMiniType<VueCopie> = z.object({
  copie: texte,
  apprenant: texte,
  exercice: texte,
  cohorte: texte,
  titre: texte,
  note_sur: z.number(),
  seuil_reussite: z.number(),
  version: indice,
  statut: texte,
  etape: texte,
  echeance: date,
  role,
  au_nom_de: z.nullable(texte),
  contenu: texte,
  source_url: texte,
  commit: texte,
  consigne: texte,
  grille: schemaGrille,
  auto_evaluation: z.nullable(niveaux),
  controles: z.array(texte),
  ia: z.nullable(z.object({ niveaux, justifications: textes, citations: textes, confiance: z.nullable(z.number()) })),
  pairs: z.object({ mediane: niveaux, nombre: indice, commentaires: z.array(textes) }),
  jury: z.object({ mediane: niveaux, nombre: indice, attendus: indice }),
  formateur: z.nullable(z.object({ niveaux, commentaires: textes, auteur: texte, au_nom_de: z.nullable(texte) })),
  ecarts: z.array(texte),
  signalement: texte,
})

// publier
export const schemaPublication = z.object({ copie: texte, note: z.number() })

// valider_lot
export const schemaResultatLot: z.ZodMiniType<ResultatLot> = z.object({
  copies: z.array(texte),
  publiees: z.array(texte),
})

// écritures sans résultat (corriger, enregistrer_relecture) : la réponse est ignorée
export const sansResultat = z.unknown()

// ConsulterRelectures.mes_relectures
export const schemaMesRelectures: z.ZodMiniType<ResumeRelecture[]> = z.array(
  z.object({ relecture: texte, exercice: texte, statut: texte, echeance: date, rang: indice, total: indice }),
)

// ConsulterRelectures.relecture
export const schemaRelecture: z.ZodMiniType<VueRelecture> = z.object({
  relecture: texte,
  exercice: texte,
  titre: texte,
  consigne: texte,
  contenu: texte,
  grille: schemaGrille,
  statut: texte,
  echeance: date,
  rang: indice,
  total: indice,
  anonymat_garanti: z.boolean(),
})

// ConsulterRetour.executer
export const schemaRetour: z.ZodMiniType<Retour> = z.object({
  copie: texte,
  exercice: texte,
  titre: texte,
  statut: texte,
  provisoire: z.boolean(),
  masquee: z.boolean(),
  note: z.nullable(z.number()),
  note_sur: z.nullable(z.number()),
  reussite: z.nullable(z.boolean()),
  criteres: z.array(
    z.object({
      code: texte,
      libelle: texte,
      poids: z.number(),
      niveau: z.nullable(indice),
      niveau_libelle: texte,
      niveaux: z.array(texte),
      auto_evaluation: z.nullable(indice),
      commentaire: texte,
      pairs: z.array(texte),
    }),
  ),
  commentaire_general: texte,
  message: texte,
})

// paiement_api.mon_dossier et choisir_mode (application/tableaux_paiement.vue_apprenant)
const montant = z.int()
export const schemaDossierPaiement: z.ZodMiniType<DossierPaiement> = z.object({
  cours: texte,
  titre: texte,
  mode: z.enum(['une_fois', 'deux_tranches', 'mensuel']),
  telephone: texte,
  tarif: z.object({ frais_inscription: montant, une_fois: montant, deux_tranches: montant, mensuel: montant }),
  echeances: z.array(z.object({ date_limite: texte, montant, libelle: texte, couverte: z.boolean() })),
  paye: montant,
  reste: montant,
  statut: z.enum(['a_jour', 'en_retard', 'solde', 'dispense']),
  prochaine: z.nullable(z.object({ date_limite: z.nullable(texte), montant })),
  paiement_en_ligne: z.boolean(),
  bloque: z.boolean(),
  instructions_virement: texte,
})

// paiement_api.payer : adresse de la page CinetPay (vérifiée https par le cas d'usage avant d'y aller)
export const schemaPaiement = z.object({ url: texte })
