// Cas d'usage de l'apprenant : consulter le retour de sa copie (le serveur masque la note tant qu'il doit des
// relectures et ne l'envoie qu'à son auteur) et l'accusé de dépôt de ce qu'il a rendu.
import type { DepotRetour } from './ports'

export class ConsulterRetour {
  constructor(private readonly depot: DepotRetour) {}

  executer(copie: string) {
    return this.depot.monRetour(copie)
  }
}

export class ConsulterAccuse {
  constructor(private readonly depot: DepotRetour) {}

  executer(copie: string) {
    return this.depot.accuse(copie)
  }
}
