// Paiement d'un parcours vu par l'apprenant : son dossier (mode, échéancier, statut calculé par le serveur), les
// montants en francs CFA et les règles de saisie (téléphone ivoirien, lien de paiement https seulement).

export type Mode = 'une_fois' | 'deux_tranches' | 'mensuel'
export const MODES: readonly Mode[] = ['une_fois', 'deux_tranches', 'mensuel']

export type StatutPaiement = 'a_jour' | 'en_retard' | 'solde' | 'dispense'

/** Prix figés à l'inscription ; le prix d'un mode comprend les frais d'inscription. */
export interface Tarif {
  frais_inscription: number
  une_fois: number
  deux_tranches: number
  mensuel: number
}

export interface EcheancePaiement {
  /** AAAA-MM-JJ ; due au plus tard ce jour-là. */
  date_limite: string
  montant: number
  libelle: string
  /** Couverte par les paiements confirmés, imputés dans l'ordre des dates. */
  couverte: boolean
}

export interface Prochaine {
  date_limite: string | null
  /** Montant que « Payer » demandera. */
  montant: number
}

export interface DossierPaiement {
  cours: string
  titre: string
  mode: Mode
  telephone: string
  tarif: Tarif
  echeances: EcheancePaiement[]
  paye: number
  reste: number
  statut: StatutPaiement
  prochaine: Prochaine | null
  paiement_en_ligne: boolean
  /** Accès au parcours suspendu jusqu'au paiement. */
  bloque: boolean
  /** Texte brut des réglages, affiché tel quel. */
  instructions_virement: string
}

/** Parcours gratuit (MOOC) : ni tarif, ni échéancier, ni rappel, ni blocage ; aucun dossier de paiement. */
export interface ParcoursGratuit {
  cours: string
  titre: string
  gratuit: true
}

/** Ce que « Mes paiements » montre pour un parcours : son dossier, ou l'état gratuit. */
export type MonPaiement = DossierPaiement | ParcoursGratuit

export function estGratuit(p: MonPaiement): p is ParcoursGratuit {
  return 'gratuit' in p && p.gratuit
}

const FINE = ' ' // espace fine insécable

/** « 187 500 FCFA » : groupes de trois chiffres et unité séparés par des espaces fines insécables. */
export function formaterXof(montant: number): string {
  const entier = Math.round(Math.abs(montant)).toString()
  const groupes = entier.replace(/\B(?=(\d{3})+(?!\d))/g, FINE)
  return `${montant < 0 ? '-' : ''}${groupes}${FINE}FCFA`
}

const STATUTS: Record<StatutPaiement, string> = {
  a_jour: 'À jour',
  en_retard: 'En retard',
  solde: 'Soldé',
  dispense: 'Dispensé',
}

export function libelleStatut(statut: StatutPaiement): string {
  return STATUTS[statut]
}

const LIBELLES_MODE: Record<Mode, string> = {
  une_fois: 'En une fois',
  deux_tranches: 'En deux tranches',
  mensuel: 'Chaque mois',
}

const CALENDRIERS: Record<Mode, string> = {
  une_fois: 'Un seul versement, à la prochaine échéance du mois',
  deux_tranches: 'Deux versements, l’un au début, l’autre au milieu du parcours',
  mensuel: 'Un versement par mois jusqu’à la fin du parcours',
}

export function libelleMode(mode: Mode): string {
  return LIBELLES_MODE[mode]
}

export function calendrierMode(mode: Mode): string {
  return CALENDRIERS[mode]
}

const jour = new Intl.DateTimeFormat('fr-FR', { day: 'numeric', month: 'long', year: 'numeric', timeZone: 'UTC' })

/** « 10 novembre 2026 » ; vide si la date est absente ou illisible. */
export function formaterJour(iso: string | null): string {
  if (!iso) return ''
  const d = new Date(`${iso}T00:00:00Z`)
  return Number.isNaN(d.getTime()) ? '' : jour.format(d)
}

/** Jour courant AAAA-MM-JJ à Abidjan (UTC), comme les échéances du serveur. */
export function jourIso(maintenant: Date): string {
  return maintenant.toISOString().slice(0, 10)
}

export type EtatEcheance = 'reglee' | 'en_retard' | 'aujourdhui' | 'a_venir'

/** Réglée si couverte ; due le jour même ; en retard à partir du lendemain de sa date ; sinon à venir. */
export function etatEcheance(e: EcheancePaiement, aujourdhui: string): EtatEcheance {
  if (e.couverte) return 'reglee'
  if (e.date_limite === aujourdhui) return 'aujourdhui'
  return e.date_limite < aujourdhui ? 'en_retard' : 'a_venir'
}

export interface LigneEcheancier extends EcheancePaiement {
  etat: EtatEcheance
  /** Première échéance non réglée : celle que le prochain paiement couvrira. */
  prochaine: boolean
}

export function lignesEcheancier(d: DossierPaiement, aujourdhui: string): LigneEcheancier[] {
  const premiere = d.echeances.findIndex((e) => !e.couverte)
  return d.echeances.map((e, i) => ({ ...e, etat: etatEcheance(e, aujourdhui), prochaine: i === premiere }))
}

/** Une échéance passée (strictement) reste impayée : le mode ne peut plus changer (le serveur refuserait). */
export function enSouffrance(d: DossierPaiement, aujourdhui: string): boolean {
  return d.echeances.some((e) => etatEcheance(e, aujourdhui) === 'en_retard')
}

/** Part réglée du parcours, en pourcentage entier (100 quand il ne reste rien). */
export function progression(d: DossierPaiement): number {
  const total = d.paye + d.reste
  return total > 0 ? Math.min(100, Math.floor((d.paye * 100) / total)) : 100
}

export interface Changement {
  total: number
  dejaVerse: number
  reste: number
}

/** Ce que devient le dossier dans un autre mode : nouveau prix global, le déjà versé est conservé. */
export function changement(d: DossierPaiement, mode: Mode): Changement {
  const total = d.tarif[mode]
  return { total, dejaVerse: d.paye, reste: Math.max(total - d.paye, 0) }
}

export const TELEPHONE_INVALIDE =
  'Numéro de téléphone invalide : 10 chiffres, précédés ou non de +225 (par exemple 07 00 00 00 00).'

/** Numéro ivoirien : 10 chiffres, indicatif +225 (ou 00225) facultatif ; rendu en +225XXXXXXXXXX, sinon null. */
export function normaliserTelephone(brut: string): string | null {
  const compact = brut.replace(/[\s.\-()]/g, '')
  const local = compact.replace(/^(\+|00)225/, '')
  return /^\d{10}$/.test(local) ? `+225${local}` : null
}

/** Page de paiement suivie seulement en https (jamais javascript:, data:, http: ni chemin relatif). */
export function urlPaiementSure(url: string): boolean {
  try {
    const u = new URL(url)
    return u.protocol === 'https:' && u.hostname !== ''
  } catch {
    return false
  }
}

/** « +225 07 00 00 00 01 » pour un numéro ivoirien normalisé ; tout autre texte rendu tel quel. */
export function formaterTelephone(numero: string): string {
  const n = /^\+225(\d{2})(\d{2})(\d{2})(\d{2})(\d{2})$/.exec(numero)
  return n ? `+225 ${n.slice(1).join(' ')}` : numero
}
