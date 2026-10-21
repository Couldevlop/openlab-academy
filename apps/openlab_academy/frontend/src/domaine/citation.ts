// Citation de l'IA dans la copie : recherchée blancs normalisés, sur les seuls textes de la copie rendue (jamais sur
// du HTML). Le résultat dit quelles portions de quels textes surligner.

/** Portion `[de, a[` du texte n° `texte`, en unités UTF-16 comme les nœuds texte du navigateur. */
export interface Plage {
  texte: number
  de: number
  a: number
}

const blanc = (c: string): boolean => /\s/.test(c)

/** Texte sans blancs superflus. */
export function normaliser(texte: string | null | undefined): string {
  return (texte ?? '').replace(/\s+/g, ' ').trim()
}

/**
 * Plages de la citation dans la suite de textes, mis bout à bout et blancs réduits ; null si elle est vide ou
 * absente. Les morceaux faits seulement de blancs ne sont pas surlignés.
 */
export function localiserCitation(textes: readonly string[], citation: string): Plage[] | null {
  const aiguille = normaliser(citation)
  let plat = ''
  const carte: Array<{ texte: number; position: number }> = [] // position dans `plat` -> texte et position
  let precedentBlanc = true
  textes.forEach((t, texte) => {
    for (let position = 0; position < t.length; position++) {
      const c = t.charAt(position)
      const estBlanc = blanc(c)
      if (estBlanc && precedentBlanc) continue
      plat += estBlanc ? ' ' : c
      carte.push({ texte, position })
      precedentBlanc = estBlanc
    }
  })
  const debut = aiguille ? plat.indexOf(aiguille) : -1
  const premier = carte[debut]
  const dernier = carte[debut + aiguille.length - 1]
  if (debut < 0 || !premier || !dernier) return null
  const plages: Plage[] = []
  textes.slice(premier.texte, dernier.texte + 1).forEach((t, k) => {
    const texte = premier.texte + k
    const de = texte === premier.texte ? premier.position : 0
    const a = texte === dernier.texte ? dernier.position + 1 : t.length
    if (t.slice(de, a).trim()) plages.push({ texte, de, a })
  })
  return plages
}
