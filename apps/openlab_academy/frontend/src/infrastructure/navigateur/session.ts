// Droits de la session, posés sur la page par le serveur (www/espace.py) : ils décident seulement des liens affichés,
// l'API refuse elle-même tout rôle non habilité. Absents ou malformés : aucun écran d'agent.
import * as z from 'zod/mini'
import type { Droits, Session } from '../../application/ports'

const AUCUN: Droits = { intendance: false, finances: false }
const schema = z.object({ intendance: z.boolean(), finances: z.boolean() })

export function sessionSur(lire: () => unknown): Session {
  return {
    droits() {
      const lu = schema.safeParse(lire())
      return lu.success ? { intendance: lu.data.intendance, finances: lu.data.finances } : AUCUN
    },
  }
}
