// Données d'essai conformes aux réponses de l'API d'évaluation (entrypoints/evaluation_api.py).
import type { ElementFile, FileCorrection, VueCopie } from '../domaine/correction'
import type { Critere, Grille } from '../domaine/grille'
import type { ResumeRelecture, VueRelecture } from '../domaine/relecture'
import type { FicheIntendance, LigneIntendance, ResumeFinances, VueIntendance } from '../domaine/intendance'
import type { DossierPaiement, ParcoursGratuit } from '../domaine/paiement'
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

/** Parcours gratuit (MOOC) tel que `mon_dossier` le rend : aucun paiement. */
export const parcoursGratuit = (autres: Partial<ParcoursGratuit> = {}): ParcoursGratuit => ({
  cours: 'initiation-ia',
  titre: 'Initiation à l’IA',
  gratuit: true,
  ...autres,
})

/** Dossier conforme à `mon_dossier` (entrypoints/paiement_api.py) : deux tranches, frais réglés, à jour. */
export const dossierPaiement = (autres: Partial<DossierPaiement> = {}): DossierPaiement => ({
  cours: 'fondamentaux-data',
  titre: 'Fondamentaux de la data science',
  mode: 'deux_tranches',
  telephone: '+2250700000001',
  tarif: { frais_inscription: 10000, une_fois: 100000, deux_tranches: 110000, mensuel: 120000 },
  echeances: [
    { date_limite: '2026-10-22', montant: 10000, libelle: "Frais d'inscription", couverte: true },
    { date_limite: '2026-11-10', montant: 50000, libelle: 'Échéance', couverte: false },
    { date_limite: '2027-01-10', montant: 50000, libelle: 'Échéance', couverte: false },
  ],
  paye: 10000,
  reste: 100000,
  statut: 'a_jour',
  prochaine: { date_limite: '2026-11-10', montant: 50000 },
  paiement_en_ligne: true,
  bloque: false,
  instructions_virement: '',
  ...autres,
})

/** Ligne conforme à `intendance` (application/tableaux_paiement._ligne + rappel_envoye) : à jour. */
export const ligneIntendance = (autres: Partial<LigneIntendance> = {}): LigneIntendance => ({
  dossier: 'DP-0001',
  apprenant: 'awa.kone@example.ci',
  nom: 'Awa Koné',
  email: 'awa.kone@example.ci',
  parcours: 'fondamentaux-data',
  titre: 'Fondamentaux de la data science',
  cohorte: 'data-2026-10',
  cohorte_titre: 'Data, octobre 2026',
  mode: 'deux_tranches',
  paye: 10000,
  total: 110000,
  reste: 100000,
  prochaine: { date_limite: '2026-11-10', montant: 50000 },
  statut: 'a_jour',
  bloque: false,
  rappel_envoye: false,
  ...autres,
})

/** Vue conforme à `intendance` : indicateurs et deux lignes (à jour, bloqué). */
export const vueIntendance = (autres: Partial<VueIntendance> = {}): VueIntendance => ({
  indicateurs: {
    encaisse_mois: 155000,
    encours_30j: 90000,
    en_retard: { montant: 55000, apprenants: 1 },
    bloques: 1,
  },
  lignes: [
    ligneIntendance(),
    ligneIntendance({
      dossier: 'DP-0002',
      apprenant: 'yao.bamba@example.ci',
      nom: 'Yao Bamba',
      email: 'yao.bamba@example.ci',
      parcours: 'python-avance',
      titre: 'Python avancé',
      cohorte: 'python-2026-09',
      cohorte_titre: 'Python, septembre 2026',
      mode: 'mensuel',
      paye: 0,
      total: 120000,
      reste: 120000,
      prochaine: { date_limite: '2026-10-22', montant: 10000 },
      statut: 'en_retard',
      bloque: true,
    }),
  ],
  tronque: false,
  ...autres,
})

/** Fiche conforme à `fiche` : échéancier, paiements, rappels, journal. */
export const ficheIntendance = (autres: Partial<FicheIntendance> = {}): FicheIntendance => ({
  dossier: 'DP-0001',
  apprenant: 'awa.kone@example.ci',
  nom: 'Awa Koné',
  email: 'awa.kone@example.ci',
  parcours: 'fondamentaux-data',
  titre: 'Fondamentaux de la data science',
  cohorte: 'data-2026-10',
  cohorte_titre: 'Data, octobre 2026',
  mode: 'deux_tranches',
  paye: 10000,
  total: 110000,
  reste: 100000,
  prochaine: { date_limite: '2026-11-10', montant: 50000 },
  statut: 'a_jour',
  bloque: false,
  telephone: '+2250700000001',
  tarif: { frais_inscription: 10000, une_fois: 100000, deux_tranches: 110000, mensuel: 120000 },
  inscription: '2026-10-22',
  echeances: [
    { date_limite: '2026-10-22', montant: 10000, libelle: "Frais d'inscription", couverte: true },
    { date_limite: '2026-11-10', montant: 50000, libelle: 'Échéance', couverte: false },
    { date_limite: '2027-01-10', montant: 50000, libelle: 'Échéance', couverte: false },
  ],
  arriere: 0,
  dispense: false,
  delai_jusqu_au: null,
  paiements: [
    {
      montant: 10000,
      moyen: 'virement',
      reference: 'VIR-2026-001',
      statut: 'confirme',
      date_paiement: '2026-10-22 00:00:00',
      auteur: 'intendant@openlab.ci',
      cree: '2026-10-22 09:12:00',
    },
  ],
  rappels: [{ date_limite: '2026-11-10', jours_avant: 7, canal: 'sms', statut: 'envoye', cree: '2026-11-03 08:00:00' }],
  journal: [
    {
      dossier: 'DP-0001',
      apprenant: 'awa.kone@example.ci',
      nom: 'Awa Koné',
      parcours: 'fondamentaux-data',
      titre: 'Fondamentaux de la data science',
      acteur: 'intendant@openlab.ci',
      action: 'virement_enregistre',
      motif: 'Relevé du 22 octobre',
      horodatage: '2026-10-22 09:12:00',
      avant: { paye: 0, statut: 'en_retard' },
      apres: { paye: 10000, statut: 'a_jour', montant: 10000, reference: 'VIR-2210', date_paiement: '2026-10-22' },
    },
  ],
  ...autres,
})

/** Résumé conforme à `resume`. */
export const resumeFinances = (autres: Partial<ResumeFinances> = {}): ResumeFinances => ({
  encaisse_mois: 155000,
  evolution_pct: 12.5,
  taux_recouvrement: 73.8,
  retards: 3,
  bloques: 2,
  par_parcours: [
    {
      parcours: 'fondamentaux-data',
      titre: 'Fondamentaux de la data science',
      inscrits: 3,
      encaisse: 155000,
      reste: 145000,
    },
    { parcours: 'python-avance', titre: 'Python avancé', inscrits: 1, encaisse: 0, reste: 120000 },
  ],
  modes: { une_fois: 1, deux_tranches: 2, mensuel: 1 },
  dernieres_actions: [
    {
      dossier: 'DP-0002',
      apprenant: 'yao.bamba@example.ci',
      nom: 'Yao Bamba',
      parcours: 'python-avance',
      titre: 'Python avancé',
      acteur: 'intendant@openlab.ci',
      action: 'delai_accorde',
      motif: 'Accord avec la famille',
      horodatage: '2026-11-02 10:00:00',
      avant: {},
      apres: {},
    },
  ],
  ...autres,
})
