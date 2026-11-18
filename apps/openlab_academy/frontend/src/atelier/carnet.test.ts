/* Lecture du carnet Jupyter de l'atelier. Le module vit à côté de l'atelier, servi tel quel au
 * navigateur (aucun paquet à construire pour une page qui doit rester lisible) : il est donc chargé
 * ici dans une portée à nous, et ses fonctions pures sont vérifiées sans navigateur. */
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { runInNewContext } from 'node:vm'
import { describe, expect, it } from 'vitest'

type Cellule = { rang: number; type: string; source: string }
type Module = {
  lire: (contenu: string) => Cellule[]
  ecrire: (contenu: string, cellules: Cellule[]) => string
  html: (markdown: string) => string
  echapper: (valeur: unknown) => string
}

// vitest a pour racine le dossier du front ; l'atelier est servi depuis l'application, à côté
const SOURCE = resolve(process.cwd(), '../openlab_academy/public/atelier/carnet.js')

function charger(): Module {
  // le module s'accroche à `globalThis` : on lui en donne un à lui, sans toucher à celui des tests
  const portee: { Carnet?: Module } = {}
  runInNewContext(readFileSync(SOURCE, 'utf8'), portee)
  if (!portee.Carnet) throw new Error("carnet.js n'a rien exposé")
  return portee.Carnet
}

const Carnet = charger()

function carnet(cells: unknown[], nbformat = 4) {
  return JSON.stringify({ nbformat, nbformat_minor: 5, metadata: { openlab: { seance: '02' } }, cells })
}

describe('lire un carnet', () => {
  it('rend les cellules dans l’ordre, code et présentation distingués', () => {
    const cellules = Carnet.lire(
      carnet([
        { cell_type: 'markdown', source: ['# Séance 2\n', '\n', 'Trois mesures.'] },
        { cell_type: 'code', source: 'x = 1\n' },
      ]),
    )
    expect(cellules).toEqual([
      { rang: 0, type: 'presentation', source: '# Séance 2\n\nTrois mesures.' },
      { rang: 1, type: 'code', source: 'x = 1\n' },
    ])
  })

  it('traite toute cellule qui n’est pas du code comme de la présentation', () => {
    const [cellule] = Carnet.lire(carnet([{ cell_type: 'raw', source: 'brut' }]))
    expect(cellule?.type).toBe('presentation')
  })

  it('accepte une cellule sans source', () => {
    const [cellule] = Carnet.lire(carnet([{ cell_type: 'code' }]))
    expect(cellule?.source).toBe('')
  })

  it('refuse un fichier sans cellules', () => {
    expect(() => Carnet.lire('{"nbformat": 4}')).toThrow(/aucune cellule/)
  })

  it('refuse un format que l’atelier ne lit pas', () => {
    expect(() => Carnet.lire(carnet([], 3))).toThrow(/format 3/)
  })

  it('refuse un fichier qui n’est pas du JSON', () => {
    expect(() => Carnet.lire('pas du json')).toThrow()
  })
})

describe('réécrire un carnet', () => {
  const origine = carnet([
    { cell_type: 'code', source: 'x = 1\n', outputs: [{ text: 'gardé' }], metadata: { tags: ['a'] } },
    { cell_type: 'markdown', source: 'texte' },
  ])

  it('reporte les sources modifiées et garde tout le reste', () => {
    const cellules = Carnet.lire(origine).map((cellule) =>
      cellule.rang === 0 ? { ...cellule, source: 'x = 2\n' } : cellule,
    )
    const relu = JSON.parse(Carnet.ecrire(origine, cellules))
    expect(relu.cells[0].source).toBe('x = 2\n')
    expect(relu.cells[0].outputs).toEqual([{ text: 'gardé' }])
    expect(relu.cells[0].metadata).toEqual({ tags: ['a'] })
    expect(relu.metadata).toEqual({ openlab: { seance: '02' } })
    expect(relu.nbformat).toBe(4)
  })

  it('ignore une cellule qui n’existe plus dans le fichier', () => {
    const relu = JSON.parse(Carnet.ecrire(origine, [{ rang: 9, type: 'code', source: 'perdu' }]))
    expect(relu.cells).toHaveLength(2)
    expect(relu.cells[0].source).toBe('x = 1\n')
  })

  it('reste relisible par lire', () => {
    expect(Carnet.lire(Carnet.ecrire(origine, Carnet.lire(origine)))).toEqual(Carnet.lire(origine))
  })
})

describe('rendu du texte d’une cellule de présentation', () => {
  it('échappe le HTML avant toute mise en forme', () => {
    expect(Carnet.html('<script>alert(1)</script>')).toBe('<p>&lt;script&gt;alert(1)&lt;/script&gt;</p>')
  })

  it('rend les titres de un à six dièses', () => {
    expect(Carnet.html('# Un')).toBe('<h1>Un</h1>')
    expect(Carnet.html('###### Six')).toBe('<h6>Six</h6>')
  })

  it('rend les listes à puces et les listes numérotées', () => {
    expect(Carnet.html('- a\n- b')).toBe('<ul>\n<li>a</li>\n<li>b</li>\n</ul>')
    expect(Carnet.html('1. a\n2. b')).toBe('<ol>\n<li>a</li>\n<li>b</li>\n</ol>')
  })

  it('ferme une liste avant d’en ouvrir une autre', () => {
    expect(Carnet.html('- a\n1. b')).toBe('<ul>\n<li>a</li>\n</ul>\n<ol>\n<li>b</li>\n</ol>')
  })

  it('rend le code en ligne, le gras et l’italique', () => {
    expect(Carnet.html('un `x = 1`, du **gras** et de l’*italique*')).toBe(
      '<p>un <code>x = 1</code>, du <strong>gras</strong> et de l’<em>italique</em></p>',
    )
  })

  it('rend un bloc de code sans y chercher de mise en forme', () => {
    expect(Carnet.html('```python\nx = **1**\n```')).toBe('<pre><code>x = **1**</code></pre>')
  })

  it('ferme un bloc de code resté ouvert', () => {
    expect(Carnet.html('```\nx = 1')).toBe('<pre><code>x = 1</code></pre>')
  })

  it('regroupe les lignes d’un paragraphe et sépare sur une ligne vide', () => {
    expect(Carnet.html('une ligne\net la suite\n\nautre')).toBe('<p>une ligne et la suite</p>\n<p>autre</p>')
  })

  it('rend un lien http ou interne au site', () => {
    expect(Carnet.html('[doc](https://exemple.test/a)')).toBe(
      '<p><a href="https://exemple.test/a" rel="noopener noreferrer">doc</a></p>',
    )
    expect(Carnet.html('[leçon](/lms/courses)')).toContain('href="/lms/courses"')
  })

  it('laisse en texte un lien dont l’adresse exécuterait du code', () => {
    expect(Carnet.html('[piège](javascript:alert(1))')).toBe('<p>[piège](javascript:alert(1))</p>')
  })

  it('rend une chaîne vide pour un texte vide', () => {
    expect(Carnet.html('')).toBe('')
    expect(Carnet.echapper(null)).toBe('')
    expect(Carnet.echapper(undefined)).toBe('')
  })
})
