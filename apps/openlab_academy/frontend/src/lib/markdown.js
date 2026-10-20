// Rendu des copies et consignes : Markdown sans HTML brut (markdown-it html:false), puis assaini (DOMPurify).
// Seul ce résultat assaini est inséré dans la page ; tout autre texte est interpolé, donc échappé par Vue.
import DOMPurify from 'dompurify'
import MarkdownIt from 'markdown-it'

const md = new MarkdownIt({ html: false, linkify: true })

const purificateur = DOMPurify()
purificateur.addHook('afterSanitizeAttributes', (noeud) => {
  if (noeud.tagName === 'A') {
    noeud.setAttribute('target', '_blank')
    noeud.setAttribute('rel', 'noopener noreferrer nofollow')
  }
})

// pas d'image distante : une image ouvrirait une requête vers un serveur choisi par l'auteur de la copie
const OPTIONS = { USE_PROFILES: { html: true }, FORBID_TAGS: ['img', 'svg', 'math', 'style', 'form', 'input'] }

export function rendreMarkdown(texte) {
  return purificateur.sanitize(md.render(String(texte ?? '')), OPTIONS)
}

const blanc = (c) => /\s/.test(c)

/** Texte sans blancs superflus : la citation de l'IA est recherchée blancs normalisés. */
export function normaliser(texte) {
  return String(texte ?? '').replace(/\s+/g, ' ').trim()
}

/**
 * Surligne la citation dans un HTML déjà assaini, en n'agissant que sur ses nœuds texte :
 * le texte de la citation n'est jamais interprété comme du HTML.
 */
export function surligner(html, citation) {
  const aiguille = normaliser(citation)
  if (!aiguille) return { html, trouvee: false }
  const gabarit = document.createElement('template')
  gabarit.innerHTML = html
  const noeuds = []
  const marcheur = document.createTreeWalker(gabarit.content, NodeFilter.SHOW_TEXT)
  while (marcheur.nextNode()) noeuds.push(marcheur.currentNode)
  let plat = ''
  const carte = [] // position dans `plat` -> [indice du nœud, position dans le nœud]
  let precedentBlanc = true
  noeuds.forEach((noeud, i) => {
    for (let j = 0; j < noeud.data.length; j++) {
      const estBlanc = blanc(noeud.data[j])
      if (estBlanc && precedentBlanc) continue
      plat += estBlanc ? ' ' : noeud.data[j]
      carte.push([i, j])
      precedentBlanc = estBlanc
    }
  })
  const debut = plat.indexOf(aiguille)
  if (debut < 0) return { html, trouvee: false }
  const [nDebut, oDebut] = carte[debut]
  const [nFin, oFin] = carte[debut + aiguille.length - 1]
  for (let i = nDebut; i <= nFin; i++) {
    const noeud = noeuds[i]
    const de = i === nDebut ? oDebut : 0
    const a = i === nFin ? oFin + 1 : noeud.data.length
    if (!noeud.data.slice(de, a).trim()) continue
    const milieu = noeud.splitText(de)
    milieu.splitText(a - de)
    const marque = document.createElement('mark')
    marque.className = 'citation'
    milieu.replaceWith(marque)
    marque.appendChild(milieu)
  }
  return { html: gabarit.innerHTML, trouvee: true }
}
