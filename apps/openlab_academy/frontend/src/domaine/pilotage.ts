// Pilotage de l'évaluation (super administrateur, responsable pédagogique) : copies en souffrance (escalade
// épuisée) et réglages réellement appliqués à un exercice, avec l'origine de chaque valeur (défauts, type, YAML de
// l'exercice, surcharge de cohorte ou d'exercice). Réponses de evaluation_api.copies_en_souffrance et
// evaluation_api.reglages_effectifs.

export interface CopieEnSouffrance {
  copie: string
  apprenant: string
  exercice: string
  cohorte: string
  /** « 2026-11-03 21:12:00 », heure du site (Abidjan = UTC). */
  depuis: string | null
  escalade_a: string
  action: string
  /** Heures avant l'action réglée ; absent quand rien ne se fera seul (la copie attend une décision). */
  reste_heures: number | null
}

export interface ValeurReglee {
  valeur: unknown
  source: string
}

export interface EquipeEffective {
  titulaires: string[]
  suppleants: string[]
  responsable: string
  provenance: Record<string, string>
}

export interface ReglagesEffectifs {
  type_exercice: string
  chaine: Record<string, ValeurReglee>
  equipe: EquipeEffective
}

export interface LigneReglage {
  champ: string
  libelle: string
  valeur: string
  source: string
}

const TYPES: Record<string, string> = {
  mise_en_situation: 'Mise en situation',
  livrable: 'Livrable',
  projet: 'Projet',
  capstone: 'Capstone',
}

const OPTIONS: Record<string, string> = {
  nb_pairs: 'Relectures par les pairs',
  anonymat: 'Relectures anonymes',
  note_masquee_avant_relectures: 'Note masquée avant les relectures dues',
  note_sur: 'Note sur',
  seuil_reussite: 'Seuil de réussite',
  pairs_attente_max_jours: 'Attente maximale des relectures',
  pairs_minimum_releves: 'Relectures minimales pour la médiane',
  pairs_reattributions_max: 'Réattributions maximales d’une copie',
}

const ETAPES: Record<string, string> = {
  auto_evaluation: 'Auto-évaluation',
  controles: 'Contrôles automatiques',
  ia: 'Pré-correction par l’IA',
  pairs: 'Relecture par les pairs',
  jury: 'Jury',
  formateur: 'Formateur',
}

const EXPIRATIONS: Record<string, string> = {
  passer: 'passer à l’étape suivante',
  reattribuer: 'réattribuer',
  escalader: 'escalader',
  dispenser: 'dispenser',
  publier_provisoire: 'publier une note provisoire',
}

const ACTIONS: Record<string, string> = {
  rien: 'Attend une décision (rappel quotidien)',
  publier_provisoire: 'Publication d’une note provisoire',
}

const PROVENANCES: Record<string, string> = {
  titulaires: 'Titulaires',
  suppleants: 'Suppléants',
  responsable: 'Responsable',
}

const nombre = new Intl.NumberFormat('fr-FR', { maximumFractionDigits: 2 })

export const libelleTypeExercice = (t: string) => TYPES[t] ?? t
export const libelleActionSouffrance = (a: string) => ACTIONS[a] ?? a
export const libelleProvenance = (champ: string) => PROVENANCES[champ] ?? champ

export function libelleChamp(champ: string): string {
  if (champ.startsWith('etape.')) {
    const etape = champ.slice('etape.'.length)
    return `Étape : ${ETAPES[etape] ?? etape}`
  }
  return OPTIONS[champ] ?? champ
}

function estEtape(v: unknown): v is { active: boolean; delai_heures: number; expiration: string } {
  return typeof v === 'object' && v !== null && 'active' in v && 'delai_heures' in v && 'expiration' in v
}

/** Valeur affichable d'un champ de la chaîne ; une forme inattendue est montrée telle quelle, jamais masquée. */
export function valeurLisible(champ: string, valeur: unknown): string {
  if (estEtape(valeur)) {
    if (!valeur.active) return 'Inactive'
    const expiration = EXPIRATIONS[valeur.expiration] ?? valeur.expiration
    return `Active · délai ${nombre.format(valeur.delai_heures)} h · à l’expiration : ${expiration}`
  }
  if (typeof valeur === 'boolean') return valeur ? 'Oui' : 'Non'
  if (typeof valeur === 'number') {
    const n = nombre.format(valeur)
    return champ === 'pairs_attente_max_jours' ? `${n} jour${valeur > 1 ? 's' : ''}` : n
  }
  if (typeof valeur === 'string') return valeur
  return JSON.stringify(valeur) ?? ''
}

const RANG = [...Object.keys(OPTIONS), ...Object.keys(ETAPES).map((e) => `etape.${e}`)]
const rang = (champ: string) => {
  const i = RANG.indexOf(champ)
  return i < 0 ? RANG.length : i
}

/** Champs de la chaîne dans un ordre stable (options, puis étapes dans l'ordre de la chaîne, puis le reste). */
export function lignesReglages(r: ReglagesEffectifs): LigneReglage[] {
  return Object.entries(r.chaine)
    .sort(([a], [b]) => rang(a) - rang(b) || a.localeCompare(b))
    .map(([champ, { valeur, source }]) => ({
      champ,
      libelle: libelleChamp(champ),
      valeur: valeurLisible(champ, valeur),
      source,
    }))
}

/** Équipe de correction en lignes : titulaires, suppléants, responsable, chacun avec le niveau qui l'a fourni. */
export function lignesEquipe(e: EquipeEffective): LigneReglage[] {
  return [
    { champ: 'titulaires', valeur: e.titulaires.join(', ') },
    { champ: 'suppleants', valeur: e.suppleants.join(', ') },
    { champ: 'responsable', valeur: e.responsable },
  ].map((l) => ({ ...l, libelle: libelleProvenance(l.champ), source: e.provenance[l.champ] ?? '' }))
}

/** « dans 5 h », « dans 2 j 3 h », « imminente » ; vide quand aucune action ne se fera seule. */
export function formaterReste(heures: number | null): string {
  if (heures === null) return ''
  if (heures <= 0) return 'imminente'
  const total = Math.ceil(heures)
  const jours = Math.floor(total / 24)
  const reste = total % 24
  if (!jours) return `dans ${reste} h`
  return reste ? `dans ${jours} j ${reste} h` : `dans ${jours} j`
}
