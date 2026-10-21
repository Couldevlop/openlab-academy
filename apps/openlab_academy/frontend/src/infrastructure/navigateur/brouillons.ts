// Brouillons de relecture dans le stockage du navigateur. Stockage indisponible (navigation privée) ou contenu
// altéré : le brouillon est simplement absent, l'écran ne tombe jamais.
import * as z from 'zod/mini'
import type { DepotBrouillons } from '../../application/ports'
import type { Brouillon } from '../../domaine/relecture'

const PREFIXE = 'openlab-relecture-'

const schemaBrouillon: z.ZodMiniType<Brouillon> = z.object({
  niveaux: z.record(z.string(), z.int()),
  conseils: z.record(z.string(), z.string()),
  enregistre: z.optional(z.string()),
})

export class DepotBrouillonsNavigateur implements DepotBrouillons {
  constructor(private readonly stockage: () => Storage) {}

  lire(relecture: string): Brouillon | null {
    try {
      const lu = schemaBrouillon.safeParse(JSON.parse(this.stockage().getItem(PREFIXE + relecture) ?? 'null'))
      return lu.success ? lu.data : null
    } catch {
      return null
    }
  }

  garder(relecture: string, brouillon: Brouillon): void {
    try {
      this.stockage().setItem(PREFIXE + relecture, JSON.stringify(brouillon))
    } catch {
      /* stockage indisponible : rien à garder */
    }
  }

  oublier(relecture: string): void {
    try {
      this.stockage().removeItem(PREFIXE + relecture)
    } catch {
      /* idem */
    }
  }
}
