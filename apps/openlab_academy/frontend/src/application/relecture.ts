// Cas d'usage de la relecture par un pair. Le brouillon reste sur l'appareil en cas de coupure réseau ; il est
// oublié une fois la relecture envoyée, quand elle l'est déjà, ou passé sa durée de conservation.
import type { Grille } from '../domaine/grille'
import {
  aFaire,
  brouillonPerime,
  criteresIncomplets,
  prochaineAFaire,
  type ResumeRelecture,
  type SaisieRelecture,
  type VueRelecture,
} from '../domaine/relecture'
import type { DepotBrouillons, DepotRelecture, Horloge } from './ports'

export type ResultatEnvoi =
  { envoyee: false; incomplets: string[] } | { envoyee: true; liste: ResumeRelecture[]; suivante: string | null }

const vierge = (): SaisieRelecture => ({ niveaux: {}, conseils: {} })

export class ConsulterRelectures {
  constructor(private readonly depot: DepotRelecture) {}

  executer() {
    return this.depot.mesRelectures()
  }
}

export class OuvrirRelecture {
  constructor(
    private readonly depot: DepotRelecture,
    private readonly brouillons: DepotBrouillons,
    private readonly horloge: Horloge,
  ) {}

  async executer(relecture: string): Promise<{ vue: VueRelecture; saisie: SaisieRelecture }> {
    const vue = await this.depot.relecture(relecture)
    const brouillon = this.brouillons.lire(relecture)
    if (brouillon && aFaire(vue.statut) && !brouillonPerime(brouillon, this.horloge.maintenant())) {
      return { vue, saisie: { niveaux: { ...brouillon.niveaux }, conseils: { ...brouillon.conseils } } }
    }
    if (brouillon) this.brouillons.oublier(relecture)
    return { vue, saisie: vierge() }
  }
}

export class GarderBrouillon {
  constructor(
    private readonly brouillons: DepotBrouillons,
    private readonly horloge: Horloge,
  ) {}

  executer(relecture: string, saisie: SaisieRelecture): void {
    this.brouillons.garder(relecture, { ...saisie, enregistre: this.horloge.maintenant().toISOString() })
  }
}

export class EnvoyerRelecture {
  constructor(
    private readonly depot: DepotRelecture,
    private readonly brouillons: DepotBrouillons,
  ) {}

  /** Un niveau et un conseil par critère, sinon rien n'est envoyé ; rend la relecture suivante à faire. */
  async executer(relecture: string, grille: Grille, saisie: SaisieRelecture): Promise<ResultatEnvoi> {
    const incomplets = criteresIncomplets(grille, saisie)
    if (incomplets.length) return { envoyee: false, incomplets }
    await this.depot.enregistrer(relecture, saisie)
    this.brouillons.oublier(relecture)
    const liste = await this.depot.mesRelectures()
    return { envoyee: true, liste, suivante: prochaineAFaire(liste)?.relecture ?? null }
  }
}
