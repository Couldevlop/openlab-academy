// Cas d'usage du correcteur (formateur, juré) : file, copie, enregistrement, publication, validation par lots.
// La publication enregistre d'abord la saisie : la note publiée est toujours celle qui est affichée.
import { chargeCorrection, type Saisie } from '../domaine/correction'
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
