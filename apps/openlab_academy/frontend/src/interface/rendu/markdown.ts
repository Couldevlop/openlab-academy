// Rendu des copies et consignes : Markdown sans HTML brut (markdown-it html:false), puis assaini (DOMPurify).
// Seul ce résultat assaini est inséré dans la page ; tout autre texte est interpolé, donc échappé par Vue.
import DOMPurify from 'dompurify'
import MarkdownIt from 'markdown-it'
import { localiserCitation } from '../../domaine/citation'

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

export function rendreMarkdown(texte: string | null | undefined): string {
  return purificateur.sanitize(md.render(texte ?? ''), OPTIONS)
}

export interface Surlignage {
  html: string
  trouvee: boolean
}

/**
 * Surligne la citation dans un HTML déjà assaini, en n'agissant que sur ses nœuds texte :
 * le texte de la citation n'est jamais interprété comme du HTML.
 */
export function surligner(html: string, citation: string): Surlignage {
  const gabarit = document.createElement('template')
  gabarit.innerHTML = html
  const noeuds: Text[] = []
  const marcheur = document.createTreeWalker(gabarit.content, NodeFilter.SHOW_TEXT)
  while (marcheur.nextNode()) noeuds.push(marcheur.currentNode as Text)
  const plages = localiserCitation(
    noeuds.map((n) => n.data),
    citation,
  )
  if (!plages) return { html, trouvee: false }
  for (const { texte, de, a } of plages) {
    const milieu = (noeuds[texte] as Text).splitText(de)
    milieu.splitText(a - de)
    const marque = document.createElement('mark')
    marque.className = 'citation'
    milieu.replaceWith(marque)
    marque.appendChild(milieu)
  }
  return { html: gabarit.innerHTML, trouvee: true }
}
