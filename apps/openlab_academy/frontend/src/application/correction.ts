// Cas d'usage du correcteur (formateur, juré) : file, copie, enregistrement, publication, validation par lots.
// La publication enregistre d'abord la saisie : la note publiée est toujours celle qui est affichée.
import { chargeCorrection, type Saisie, type VersionTexte, type VueCopie } from '../domaine/correction'
import { comparerTextes, resumerDiff, type LigneDiff, type ResumeDiff } from '../domaine/versions'
import type { DepotCorrection } from './ports'

export class ConsulterFile {
  constructor(private readonly depot: DepotCorrection) {}

  executer(exercice?: string) {
    return this.depot.file(exercice)
  }
}

export class OuvrirCopie {
  constructor(private readonly depot: DepotCorrection) {}

  executer(copie: string) {
    return this.depot.copie(copie)
  }
}

export class EnregistrerCorrection {
  constructor(private readonly depot: DepotCorrection) {}

  executer(copie: string, saisie: Saisie): Promise<void> {
    return this.depot.corriger(chargeCorrection(copie, saisie))
  }
}

export class PublierNote {
  constructor(private readonly depot: DepotCorrection) {}

  /** Rend la note publiée. */
  async executer(copie: string, saisie: Saisie): Promise<number> {
    await this.depot.corriger(chargeCorrection(copie, saisie))
    return this.depot.publier(copie)
  }
}

export class ValiderLot {
  constructor(private readonly depot: DepotCorrection) {}

  executer(copies: string[], etPublier: boolean) {
    return this.depot.validerLot(copies, etPublier)
  }
}

export interface Comparaison {
  precedente: VersionTexte
  diff: LigneDiff[]
  resume: ResumeDiff
}

/** Compare une version antérieure à la version ouverte : ce qui a été retiré, ce qui a été ajouté. */
export class ComparerVersions {
  constructor(private readonly depot: DepotCorrection) {}

  async executer(vue: VueCopie, precedente: string): Promise<Comparaison> {
    const version = await this.depot.versionPrecedente(vue.copie, precedente)
    const diff = comparerTextes(version.contenu, vue.contenu)
    return { precedente: version, diff, resume: resumerDiff(diff) }
  }
}
