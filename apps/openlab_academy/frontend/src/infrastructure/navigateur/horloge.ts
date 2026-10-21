import type { Horloge } from '../../application/ports'

export const horlogeSysteme: Horloge = { maintenant: () => new Date() }
