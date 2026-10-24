// Cas d'usage des agents (intendant, administrateur) : consulter les dossiers filtrés et leur fiche, enregistrer un
// virement, accorder un délai (saisies relues avant l'envoi, motif obligatoire), exporter, lire le résumé.
// Le serveur contrôle le rôle à chaque appel et journalise l'utilisateur de la session comme acteur.
import {
  montantSaisi,
  parametresFiltres,
  validerDelai,
  validerVirement,
  type FicheIntendance,
  type Filtres,
  type ResumeFinances,
  type SaisieDelai,
  type SaisieVirement,
  type VueIntendance,
} from '../domaine/intendance'
import { jourIso } from '../domaine/paiement'
import { ErreurDepot } from './erreurs'
import type { DepotIntendance, Droits, Horloge, Session } from './ports'

export class ConsulterIntendance {
  constructor(private readonly depot: DepotIntendance) {}

  executer(filtres: Filtres): Promise<VueIntendance> {
    return this.depot.intendance(parametresFiltres(filtres))
  }
}

export class LienExport {
  constructor(private readonly depot: DepotIntendance) {}

  executer(filtres: Filtres): string {
    return this.depot.lienExport(parametresFiltres(filtres))
  }
}

export interface FicheDuJour {
  fiche: FicheIntendance
  /** AAAA-MM-JJ (Abidjan, UTC). */
  aujourdhui: string
}

export class OuvrirFiche {
  constructor(
    private readonly depot: DepotIntendance,
    private readonly horloge: Horloge,
  ) {}

  async executer(dossier: string): Promise<FicheDuJour> {
    const fiche = await this.depot.fiche(dossier)
    return { fiche, aujourdhui: jourIso(this.horloge.maintenant()) }
  }
}

function refuser(erreurs: Partial<Record<string, string>>): void {
  const motifs = Object.values(erreurs).filter((m): m is string => !!m)
  if (motifs.length) throw new ErreurDepot('refus', motifs)
}

export class EnregistrerVirement {
  constructor(
    private readonly depot: DepotIntendance,
    private readonly horloge: Horloge,
  ) {}

  async executer(dossier: string, s: SaisieVirement): Promise<void> {
    refuser(validerVirement(s, jourIso(this.horloge.maintenant())))
    await this.depot.enregistrerVirement(dossier, {
      montant: montantSaisi(s.montant),
      reference: s.reference.trim(),
      date_paiement: s.date,
      motif: s.motif.trim(),
    })
  }
}

export class AccorderDelai {
  constructor(
    private readonly depot: DepotIntendance,
    private readonly horloge: Horloge,
  ) {}

  async executer(dossier: string, s: SaisieDelai): Promise<void> {
    refuser(validerDelai(s, jourIso(this.horloge.maintenant())))
    await this.depot.accorderDelai(dossier, s.jusquau, s.motif.trim())
  }
}

export class ConsulterResume {
  constructor(private readonly depot: DepotIntendance) {}

  executer(): Promise<ResumeFinances> {
    return this.depot.resume()
  }
}

export class ConsulterDroits {
  constructor(private readonly session: Session) {}

  executer(): Droits {
    return this.session.droits()
  }
}
