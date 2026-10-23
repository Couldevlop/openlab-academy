// Cas d'usage de l'apprenant sur le paiement d'un parcours : consulter son dossier, choisir son mode (téléphone
// vérifié avant l'envoi), payer en ligne en suivant seulement la page https rendue par le serveur.
import {
  jourIso,
  normaliserTelephone,
  TELEPHONE_INVALIDE,
  urlPaiementSure,
  type DossierPaiement,
  type Mode,
  type MonPaiement,
} from '../domaine/paiement'
import { ErreurDepot } from './erreurs'
import type { DepotPaiement, Horloge, Navigateur } from './ports'

export { TELEPHONE_INVALIDE }

export const LIEN_REFUSE =
  "Le lien de paiement reçu n'est pas sûr : il n'a pas été ouvert. Réessayez dans un instant ou réglez par virement."

export interface DossierDuJour {
  /** Le dossier, ou l'état gratuit d'un parcours gratuit (MOOC). */
  dossier: MonPaiement
  /** AAAA-MM-JJ, pour situer chaque échéance (réglée, en retard, à venir). */
  aujourdhui: string
}

export class ChargerDossier {
  constructor(
    private readonly depot: DepotPaiement,
    private readonly horloge: Horloge,
  ) {}

  async executer(cours: string): Promise<DossierDuJour> {
    const dossier = await this.depot.monDossier(cours)
    return { dossier, aujourdhui: jourIso(this.horloge.maintenant()) }
  }
}

export class ChoisirMode {
  constructor(private readonly depot: DepotPaiement) {}

  executer(cours: string, mode: Mode, telephone: string): Promise<DossierPaiement> {
    const numero = normaliserTelephone(telephone)
    if (!numero) return Promise.reject(new ErreurDepot('refus', [TELEPHONE_INVALIDE]))
    return this.depot.choisirMode(cours, mode, numero)
  }
}

export class Payer {
  constructor(
    private readonly depot: DepotPaiement,
    private readonly navigateur: Navigateur,
  ) {}

  async executer(cours: string): Promise<void> {
    const url = await this.depot.payer(cours)
    if (!urlPaiementSure(url)) throw new ErreurDepot('refus', [LIEN_REFUSE])
    this.navigateur.aller(url)
  }
}
