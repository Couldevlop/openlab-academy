// @vitest-environment node
// Règles d'architecture du lint, vérifiées sur du code soumis à ESLint comme s'il était dans un écran.
import { ESLint } from 'eslint'
import { describe, expect, it } from 'vitest'

const ECRAN = 'src/interface/composants/Puce.vue'
const eslint = new ESLint()

async function regles(script: string, fichier = ECRAN): Promise<string[]> {
  const code = fichier.endsWith('.vue') ? `<script setup lang="ts">\n${script}\n</script>\n` : script
  const [resultat] = await eslint.lintText(code, { filePath: fichier })
  return (resultat?.messages ?? []).map((m) => m.ruleId ?? m.message)
}

describe('architecture du front', { timeout: 60_000 }, () => {
  it('aucun appel réseau direct depuis un écran, même par window ou globalThis', async () => {
    expect(await regles("void window.fetch('/api')")).toContain('no-restricted-properties')
    expect(await regles("void globalThis.fetch('/api')")).toContain('no-restricted-properties')
    expect(await regles("void window.fetch('/api')", 'src/domaine/grille.ts')).toContain('no-restricted-properties')
  })

  it('les écrans reçoivent les cas d’usage par injection : import de type seul', async () => {
    const valeur = "import { creerCasUsages } from '../../application/cas-usages'\nconsole.log(creerCasUsages)"
    expect(await regles(valeur)).toContain('@typescript-eslint/no-restricted-imports')
    const type =
      "import type { CasUsages } from '../../application/cas-usages'\nlet c: CasUsages | null = null\nconsole.log(c)"
    expect(await regles(type)).not.toContain('@typescript-eslint/no-restricted-imports')
    const cas = "import { ConsulterFile } from '../../application/correction'\nconsole.log(ConsulterFile)"
    expect(await regles(cas)).toContain('@typescript-eslint/no-restricted-imports')
  })

  it('les sous-modules de frappe-ui restent aux adaptateurs', async () => {
    expect(await regles("import { call } from 'frappe-ui/src/utils'\nconsole.log(call)")).toContain(
      'no-restricted-imports',
    )
  })
})
