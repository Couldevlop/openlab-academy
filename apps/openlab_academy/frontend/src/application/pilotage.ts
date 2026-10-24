// Cas d'usage du pilotage (super administrateur, responsable pédagogique) : copies en souffrance et réglages
// appliqués à un exercice avec leur origine. Le serveur contrôle le rôle à chaque appel.
import { ErreurDepot } from './erreurs'
import type { DepotPilotage } from './ports'

export class ConsulterSouffrances {
  constructor(private readonly depot: DepotPilotage) {}

  executer() {
    return this.depot.souffrances()
  }
}

export class ConsulterReglagesEffectifs {
  constructor(private readonly depot: DepotPilotage) {}

  /** Exercice obligatoire ; cohorte facultative (sans elle, les surcharges de cohorte ne s'appliquent pas). */
  executer(exercice: string, cohorte = '') {
    const ex = exercice.trim()
    if (!ex) return Promise.reject(new ErreurDepot('refus', ["Indiquez l'exercice à examiner."]))
    return this.depot.reglagesEffectifs(ex, cohorte.trim() || undefined)
  }
}
