// Erreurs typées des dépôts et leur message pour l'utilisateur (texte brut, affiché échappé).

export type SorteErreur =
  | 'trop_de_demandes' // limitation de débit (429)
  | 'acces_refuse' // ressource d'autrui ou inexistante (403)
  | 'refus' // refus métier motivé par le serveur
  | 'hors_ligne' // serveur injoignable ou en panne
  | 'reponse_invalide' // réponse de forme inattendue

export class ErreurDepot extends Error {
  override readonly name = 'ErreurDepot'

  constructor(
    readonly sorte: SorteErreur,
    /** Motifs du serveur (refus) ou écarts de forme (réponse invalide). */
    readonly details: string[] = [],
  ) {
    super(`${sorte}${details.length ? ` : ${details.join(' ; ')}` : ''}`)
  }
}

export const TROP_DE_DEMANDES =
  'Trop de demandes en peu de temps. Patientez quelques minutes puis réessayez : votre saisie est conservée.'
export const ACCES_REFUSE = "Cet élément n'existe pas ou ne vous est pas ouvert."
export const HORS_LIGNE = 'Le serveur ne répond pas. Vérifiez votre connexion puis réessayez.'
export const REPONSE_INVALIDE =
  'Le serveur a répondu de façon inattendue. Rechargez la page ; si le problème persiste, prévenez votre formateur.'

const MESSAGES: Record<Exclude<SorteErreur, 'refus'>, string> = {
  trop_de_demandes: TROP_DE_DEMANDES,
  acces_refuse: ACCES_REFUSE,
  hors_ligne: HORS_LIGNE,
  reponse_invalide: REPONSE_INVALIDE,
}

/** Message lisible d'un échec ; toute erreur imprévue est présentée comme une panne. */
export function messageErreur(erreur: unknown): string {
  if (!(erreur instanceof ErreurDepot)) return HORS_LIGNE
  return erreur.sorte === 'refus' ? erreur.details.join(' ') : MESSAGES[erreur.sorte]
}
