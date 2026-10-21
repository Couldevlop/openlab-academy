// Données d'essai conformes aux réponses de l'API d'évaluation (entrypoints/evaluation_api.py).
import type { ElementFile, FileCorrection, VueCopie } from '../domaine/correction'
import type { Critere, Grille } from '../domaine/grille'
import type { ResumeRelecture, VueRelecture } from '../domaine/relecture'
import type { CritereRetour, Retour } from '../domaine/retour'

export const LIBELLES = ['Insuffisant', 'À consolider', 'Satisfaisant', 'Excellent']

export const critere = (code: string, poids: number, libelle = code): Critere => ({
  code,
  libelle,
  description: libelle,
  poids,
  controles: [],
  niveaux: LIBELLES.map((l, i) => ({ libelle: l, descripteur: `${l} (${code})`, points: i })),
})

export const grille = (...criteres: Critere[]): Grille => ({ criteres })

export const elementFile = (copie: string, autres: Partial<ElementFile> = {}): ElementFile => ({
  copie,
  apprenant: `${copie.toLowerCase()}@exemple.ci`,
  exercice: 'ASG-1',
  cohorte: 'COH',
  version: 1,
  statut: 'a_corriger',
  etape: 'formateur',
  echeance: null,
  role: 'formateur',
  confiance: null,
  ecarts: [],
  signalee: false,
  corrigee: false,
  ...autres,
})

export const fileCorrection = (ids: string[], lots: string[][] = []): FileCorrection => ({
  copies: ids.map((id) => elementFile(id)),
  lots,
})

export const vueCopie = (autres: Partial<VueCopie> = {}): VueCopie => ({
  copie: 'C2',
  apprenant: 'a@exemple.ci',
  exercice: 'ASG-1',
  cohorte: 'COH',
  titre: 'La baisse des ventes',
  note_sur: 20,
  seuil_reussite: 10,
  version: 1,
  statut: 'a_corriger',
  etape: 'formateur',
  echeance: null,
  role: 'formateur',
  au_nom_de: null,
  contenu: 'Je chercherais pourquoi les ventes baissent à Bouaké.',
  source_url: '',
  commit: '',
  consigne: 'Rédigez la question.',
  grille: grille(critere('pertinence', 50), critere('rigueur', 50)),
  auto_evaluation: null,
  controles: [],
  ia: {
    niveaux: { pertinence: 2, rigueur: 2 },
    justifications: {},
    citations: { pertinence: 'pourquoi les ventes', rigueur: 'Bouaké' },
    confiance: 0.9,
  },
  pairs: { mediane: {}, nombre: 0, commentaires: [] },
  jury: { mediane: {}, nombre: 0, attendus: 0 },
  formateur: null,
  ecarts: [],
  signalement: '',
  ...autres,
})

export const resumeRelecture = (relecture: string, autres: Partial<ResumeRelecture> = {}): ResumeRelecture => ({
  relecture,
  exercice: 'ASG-1',
  statut: 'à_faire',
  echeance: '2026-11-03 21:12:00',
  rang: 1,
  total: 3,
  ...autres,
})

export const vueRelecture = (autres: Partial<VueRelecture> = {}): VueRelecture => ({
  relecture: 'R1',
  exercice: 'ASG-1',
  titre: 'La baisse des ventes à Bouaké',
  consigne: 'Rédigez la question.',
  contenu: 'Je chercherais pourquoi les ventes baissent.',
  grille: grille(critere('pertinence', 50, 'Pertinence'), critere('rigueur', 50, 'Rigueur')),
  statut: 'à_faire',
  echeance: '2026-11-03 21:12:00',
  rang: 1,
  total: 3,
  anonymat_garanti: true,
  ...autres,
})

export const critereRetour = (
  code: string,
  niveau: number | null,
  autres: Partial<CritereRetour> = {},
): CritereRetour => ({
  code,
  libelle: code,
  poids: 50,
  niveau,
  niveau_libelle: niveau === null ? '' : (LIBELLES[niveau] ?? ''),
  niveaux: LIBELLES,
  auto_evaluation: null,
  commentaire: '',
  pairs: [],
  ...autres,
})

export const retour = (autres: Partial<Retour> = {}): Retour => ({
  copie: 'C1',
  exercice: 'ASG-1',
  titre: 'La baisse des ventes à Bouaké',
  statut: 'publiee',
  provisoire: false,
  masquee: false,
  note: null,
  note_sur: null,
  reussite: null,
  criteres: [],
  commentaire_general: '',
  message: '',
  ...autres,
})
