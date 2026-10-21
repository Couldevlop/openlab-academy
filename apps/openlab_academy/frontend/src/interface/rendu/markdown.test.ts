import { describe, expect, it } from 'vitest'
import { rendreMarkdown, surligner } from './markdown'

describe('rendreMarkdown', () => {
  it('rend le Markdown de la copie', () => {
    expect(rendreMarkdown('# Titre\n\nUn **point** clé')).toContain('<strong>point</strong>')
  })

  it("n'interprète jamais le HTML écrit dans la copie (XSS)", () => {
    const html = rendreMarkdown('<script>alert(1)</script>\n\n<img src=x onerror=alert(2)> <b onclick="x()">b</b>')
    const zone = document.createElement('div')
    zone.innerHTML = html
    expect(zone.querySelector('script, img, b')).toBeNull()
    expect(zone.textContent).toContain('<script>alert(1)</script>')
  })

  it('neutralise les liens javascript et isole les liens externes', () => {
    const zone = document.createElement('div')
    zone.innerHTML = rendreMarkdown('[piège](javascript:alert(1)) et [dépôt](https://exemple.ci/depot)')
    const liens = [...zone.querySelectorAll('a')]
    expect(liens.map((a) => a.getAttribute('href'))).toEqual(['https://exemple.ci/depot'])
    expect(liens[0]?.getAttribute('rel')).toBe('noopener noreferrer nofollow')
  })

  it("n'affiche aucune image distante", () => {
    expect(rendreMarkdown('![pixel](https://traceur.example/p.png)')).not.toContain('<img')
  })

  it('accepte une copie vide', () => {
    expect(rendreMarkdown(null)).toBe('')
  })
})

describe('surligner la citation de l’IA', () => {
  const html = rendreMarkdown(
    'Je reformulerais : pourquoi les ventes ont-elles\nbaissé de 18 % à Bouaké ?\n\nDonnées : ventes.',
  )

  it('entoure la citation trouvée d’un <mark>', () => {
    const { html: rendu, trouvee } = surligner(html, 'pourquoi les ventes ont-elles baissé de 18 %')
    expect(trouvee).toBe(true)
    const zone = document.createElement('div')
    zone.innerHTML = rendu
    expect([...zone.querySelectorAll('mark.citation')].map((m) => m.textContent).join('')).toBe(
      'pourquoi les ventes ont-elles\nbaissé de 18 %',
    )
  })

  it('surligne une citation qui traverse une mise en forme', () => {
    const { html: rendu } = surligner(rendreMarkdown('un **point clé** ici'), 'point clé ici')
    const zone = document.createElement('div')
    zone.innerHTML = rendu
    expect([...zone.querySelectorAll('mark')].map((m) => m.textContent)).toEqual(['point clé', ' ici'])
  })

  it('laisse la copie intacte quand la citation est absente ou vide', () => {
    expect(surligner(html, 'introuvable')).toEqual({ html, trouvee: false })
    expect(surligner(html, '  ')).toEqual({ html, trouvee: false })
  })

  it('échappe une citation contenant du HTML (texte, jamais balise)', () => {
    const copie = rendreMarkdown('Voici <img src=x onerror=alert(1)> dans le texte')
    const { html: rendu, trouvee } = surligner(copie, '<img src=x onerror=alert(1)>')
    expect(trouvee).toBe(true)
    const zone = document.createElement('div')
    zone.innerHTML = rendu
    expect(zone.querySelector('img')).toBeNull()
    expect(zone.querySelector('mark')?.textContent).toBe('<img src=x onerror=alert(1)>')
  })

  it('une citation à cheval sur un paragraphe ne surligne pas le blanc qui les sépare', () => {
    const { html: rendu } = surligner(rendreMarkdown('fin du premier\n\ndébut du second'), 'premier début')
    const zone = document.createElement('div')
    zone.innerHTML = rendu
    expect([...zone.querySelectorAll('mark')].map((m) => m.textContent)).toEqual(['premier', 'début'])
  })
})
