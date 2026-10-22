// Paiements vus par l'intendance et l'administration : lignes de dossiers (statut et blocage calculés par le serveur),
// fiche d'un dossier, résumé ; état affiché d'une ligne, tri, filtres et règles des saisies (virement, délai).
import type { EcheancePaiement, Mode, Prochaine, StatutPaiement, Tarif } from './paiement'

export interface LigneIntendance {
  dossier: string
  apprenant: string
  nom: string
  email: string
  parcours: string
  titre: string
  cohorte: string
  /** Titre de la cohorte (à défaut, son identifiant). */
  cohorte_titre: string
  mode: Mode
  paye: number
  total: number
  reste: number
  prochaine: Prochaine | null
  statut: StatutPaiement
  bloque: boolean
  /** Un rappel est parti pour la prochaine échéance. */
  rappel_envoye: boolean
}

export interface IndicateursIntendance {
  encaisse_mois: number
  /** À échoir sur 30 jours. */
  encours_30j: number
  en_retard: { montant: number; apprenants: number }
  bloques: number
}

export interface VueIntendance {
  indicateurs: IndicateursIntendance
  lignes: LigneIntendance[]
  /** Plus de lignes que le serveur n'en rend : affiner les filtres. */
  tronque: boolean
}

export interface PaiementRecu {
  montant: number
  moyen: 'cinetpay' | 'virement'
  reference: string
  statut: 'en_attente' | 'confirme' | 'echoue'
  date_paiement: string | null
  auteur: string
  cree: string | null
}

export interface RappelEnvoye {
  date_limite: string | null
  jours_avant: number
  canal: 'email' | 'sms' | 'whatsapp'
  statut: 'envoye' | 'echec' | 'ignore'
  cree: string | null
}

export interface ActionJournal {
  dossier: string
  /** Apprenant et parcours du dossier, nommés. */
  apprenant: string
  nom: string
  parcours: string
  titre: string
  acteur: string
  action: string
  motif: string
  horodatage: string | null
  avant: unknown
  apres: unknown
}

export interface FicheIntendance extends Omit<LigneIntendance, 'rappel_envoye'> {
  telephone: string
  tarif: Tarif
  inscription: string
  echeances: EcheancePaiement[]
  arriere: number
  dispense: boolean
  delai_jusqu_au: string | null
  paiements: PaiementRecu[]
  rappels: RappelEnvoye[]
  journal: ActionJournal[]
}

export interface ParcoursResume {
  parcours: string
  titre: string
  inscrits: number
  encaisse: number
  reste: number
}

export interface ResumeFinances {
  encaisse_mois: number
  /** Évolution par rapport à la même période du mois précédent ; null sans base. */
  evolution_pct: number | null
  /** Part de l'exigible recouvrée, en % ; null si rien n'est exigible. */
  taux_recouvrement: number | null
  retards: number
  bloques: number
  par_parcours: ParcoursResume[]
  modes: Record<Mode, number>
  dernieres_actions: ActionJournal[]
}

export interface Filtres {
  parcours: string
  cohorte: string
  mode: Mode | ''
  /** Statut du domaine, ou « bloque » (arriéré sans délai), filtré par le serveur. */
  statut: StatutPaiement | 'bloque' | ''
  /** Période d'inscription, AAAA-MM-JJ. */
  du: string
  au: string
}

export const FILTRES_VIDES: Filtres = { parcours: '', cohorte: '', mode: '', statut: '', du: '', au: '' }

/** Paramètres de l'API : seules les valeurs saisies, sans blancs. */
export function parametresFiltres(f: Filtres): Record<string, string> {
  const parametres: Record<string, string> = {}
  for (const [cle, valeur] of Object.entries(f) as [keyof Filtres, string][]) {
    if (valeur.trim()) parametres[cle] = valeur.trim()
  }
  return parametres
}

export type EtatLigne = 'bloque' | 'en_retard' | 'rappel_envoye' | 'a_jour' | 'solde' | 'dispense'

/** Du plus urgent au moins urgent. */
export const ETATS: readonly EtatLigne[] = ['bloque', 'en_retard', 'rappel_envoye', 'a_jour', 'solde', 'dispense']

const LIBELLES_ETAT: Record<EtatLigne, string> = {
  a_jour: 'À jour',
  rappel_envoye: 'Rappel envoyé',
  en_retard: 'En retard',
  bloque: 'Bloqué',
  solde: 'Soldé',
  dispense: 'Dispensé',
}

export function libelleEtat(etat: EtatLigne): string {
  return LIBELLES_ETAT[etat]
}

/** Bloqué l'emporte ; un retard sous délai reste « En retard » ; une ligne à jour signale le rappel envoyé. */
export function etatLigne(l: { statut: StatutPaiement; bloque: boolean; rappel_envoye?: boolean }): EtatLigne {
  if (l.bloque) return 'bloque'
  if (l.statut === 'a_jour' && l.rappel_envoye) return 'rappel_envoye'
  return l.statut
}

export type CleTri = 'nom' | 'parcours' | 'paye' | 'reste' | 'prochaine' | 'etat'
export type Sens = 'asc' | 'desc'

const comparateur = new Intl.Collator('fr', { sensitivity: 'base' })

function comparer(a: LigneIntendance, b: LigneIntendance, cle: CleTri): number {
  switch (cle) {
    case 'nom':
      return comparateur.compare(a.nom, b.nom)
    case 'parcours':
      return comparateur.compare(a.titre, b.titre)
    case 'paye':
    case 'reste':
      return a[cle] - b[cle]
    case 'etat':
      return ETATS.indexOf(etatLigne(a)) - ETATS.indexOf(etatLigne(b))
    case 'prochaine':
      return (a.prochaine?.date_limite ?? '').localeCompare(b.prochaine?.date_limite ?? '')
  }
}

/** Copie triée ; sans prochaine échéance, une ligne va toujours en dernier ; à égalité, l'ordre reçu est gardé. */
export function trier(lignes: readonly LigneIntendance[], cle: CleTri, sens: Sens): LigneIntendance[] {
  const signe = sens === 'asc' ? 1 : -1
  return [...lignes].sort((a, b) => {
    if (cle === 'prochaine') {
      const sansA = !a.prochaine?.date_limite
      const sansB = !b.prochaine?.date_limite
      if (sansA !== sansB) return sansA ? 1 : -1
    }
    return signe * comparer(a, b, cle)
  })
}

export interface SaisieVirement {
  montant: string
  reference: string
  /** AAAA-MM-JJ */
  date: string
  motif: string
}

export interface SaisieDelai {
  /** AAAA-MM-JJ */
  jusquau: string
  motif: string
}

export type Erreurs<T> = Partial<Record<keyof T, string>>

export const REFERENCE_MAX = 140
const MOTIF_OBLIGATOIRE = 'Le motif est obligatoire.'

/** Montant tapé (espaces de groupes admis) en francs CFA ; NaN s'il n'est pas un entier. */
export function montantSaisi(brut: string): number {
  const compact = brut.replace(/[\s  ]/g, '')
  return /^\d{1,12}$/.test(compact) ? Number(compact) : Number.NaN
}

export function validerVirement(s: SaisieVirement, aujourdhui: string): Erreurs<SaisieVirement> {
  const erreurs: Erreurs<SaisieVirement> = {}
  const montant = montantSaisi(s.montant)
  if (!s.montant.trim()) erreurs.montant = 'Indiquez le montant reçu.'
  else if (!(montant > 0)) erreurs.montant = 'Montant en francs CFA : un nombre entier positif.'
  const reference = s.reference.trim()
  if (!reference) erreurs.reference = 'Indiquez la référence du virement.'
  else if (reference.length > REFERENCE_MAX) erreurs.reference = 'Référence trop longue : 140 caractères au plus.'
  if (!s.date) erreurs.date = 'Indiquez la date du virement.'
  else if (s.date > aujourdhui) erreurs.date = 'La date du virement ne peut pas être dans le futur.'
  if (!s.motif.trim()) erreurs.motif = MOTIF_OBLIGATOIRE
  return erreurs
}

export function validerDelai(s: SaisieDelai, aujourdhui: string): Erreurs<SaisieDelai> {
  const erreurs: Erreurs<SaisieDelai> = {}
  if (!s.jusquau) erreurs.jusquau = 'Indiquez la nouvelle date limite.'
  else if (s.jusquau <= aujourdhui) erreurs.jusquau = 'La nouvelle date limite doit être après aujourd’hui.'
  if (!s.motif.trim()) erreurs.motif = MOTIF_OBLIGATOIRE
  return erreurs
}

/** Échéance que le délai repousse : la première non couverte. */
export function echeanceADecaler(f: Pick<FicheIntendance, 'echeances'>): EcheancePaiement | null {
  return f.echeances.find((e) => !e.couverte) ?? null
}

const ACTIONS: Record<string, string> = {
  virement_enregistre: 'Virement enregistré',
  delai_accorde: 'Délai accordé',
  paiement_confirme: 'Paiement en ligne confirmé',
  mode: 'Mode de paiement changé',
}

export function libelleAction(action: string): string {
  return ACTIONS[action] ?? action
}

// heures naïves du serveur, au fuseau du site (Abidjan = UTC) : lues en UTC et affichées à Abidjan, quel que soit le
// fuseau du navigateur
const FUSEAU = 'Africa/Abidjan'
const horodatage = new Intl.DateTimeFormat('fr-FR', {
  timeZone: FUSEAU,
  day: 'numeric',
  month: 'short',
  year: 'numeric',
  hour: '2-digit',
  minute: '2-digit',
})

function lireHorodatage(valeur: string | null): Date | null {
  if (!valeur) return null
  const d = new Date(`${valeur.slice(0, 19).replace(' ', 'T')}Z`)
  return Number.isNaN(d.getTime()) ? null : d
}

/** « 3 nov. 2026, 21:12 » pour un horodatage de Frappe ; vide s'il est absent ou illisible. */
export function formaterHorodatage(valeur: string | null): string {
  const d = lireHorodatage(valeur)
  return d ? horodatage.format(d) : ''
}

/** Valeur d'un attribut `datetime` : « 2026-11-03T21:12:00Z » ; absente si l'horodatage est illisible. */
export function isoHorodatage(valeur: string | null): string | undefined {
  const d = lireHorodatage(valeur)
  return d ? `${d.toISOString().slice(0, 19)}Z` : undefined
}
