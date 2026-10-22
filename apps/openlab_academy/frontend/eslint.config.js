// Qualité du front : Vue et TypeScript typés, sens des dépendances de l'architecture hexagonale, mise en forme laissée
// à Prettier.
//   domaine         <- application <- infrastructure (adaptateurs)
//                                  <- interface (écrans, composants, routeur)
// Le domaine ne connaît que lui-même ; l'application, le domaine ; l'interface n'atteint jamais l'infrastructure :
// elle reçoit les cas d'usage par provide/inject. Seul src/main.ts branche le tout.
import { defineConfigWithVueTs, vueTsConfigs } from '@vue/eslint-config-typescript'
import prettier from 'eslint-config-prettier'
import pluginVue from 'eslint-plugin-vue'

const couche = (nom) => [`**/${nom}`, `**/${nom}/**`]
const RESEAU = [
  { name: 'fetch', message: "Le réseau passe par un adaptateur de l'infrastructure." },
  { name: 'XMLHttpRequest', message: "Le réseau passe par un adaptateur de l'infrastructure." },
]
// fetch atteint aussi par l'objet global : window.fetch, globalThis.fetch, self.fetch
const RESEAU_GLOBAL = ['window', 'globalThis', 'self'].flatMap((object) =>
  ['fetch', 'XMLHttpRequest'].map((property) => ({
    object,
    property,
    message: "Le réseau passe par un adaptateur de l'infrastructure.",
  })),
)
// cas d'usage : les écrans les reçoivent par provide/inject, ils n'en importent que les types
const CAS_USAGES = ['cas-usages', 'correction', 'relecture', 'retour', 'paiement', 'intendance'].map(
  (m) => `**/application/${m}`,
)
const NAVIGATEUR = [
  ...RESEAU,
  { name: 'window', message: 'Règle pure : aucun accès au navigateur.' },
  { name: 'document', message: 'Règle pure : aucun accès au navigateur.' },
  { name: 'localStorage', message: "Le stockage passe par un adaptateur de l'infrastructure." },
  { name: 'sessionStorage', message: "Le stockage passe par un adaptateur de l'infrastructure." },
]
const CADRES = [
  'vue',
  'vue-router',
  'frappe-ui',
  'frappe-ui-requete',
  'frappe-ui/*',
  'zod',
  'dompurify',
  'markdown-it',
  'zod/mini',
]

// un paquet à motif (frappe-ui/*) va dans patterns : paths ne compare que des noms exacts
const interdire = (
  couches,
  paquets = [],
  pourquoi = 'Cadre ou bibliothèque réservé aux adaptateurs et aux écrans.',
) => {
  const motifs = paquets.filter((p) => p.includes('*'))
  return {
    'no-restricted-imports': [
      'error',
      {
        paths: paquets.filter((p) => !p.includes('*')).map((name) => ({ name, message: pourquoi })),
        patterns: [
          { group: couches.flatMap(couche), message: 'Import contraire au sens des dépendances.' },
          ...(motifs.length ? [{ group: motifs, message: pourquoi }] : []),
        ],
      },
    ],
    'no-restricted-properties': ['error', ...RESEAU_GLOBAL],
  }
}

export default defineConfigWithVueTs(
  { ignores: ['coverage/**', 'dist/**', 'eslint.config.js', 'vite.config.ts'] },
  pluginVue.configs['flat/recommended'],
  vueTsConfigs.recommendedTypeChecked,
  {
    rules: {
      // HTML brut interdit : seul CopieRendue insère le Markdown assaini (html:false puis DOMPurify)
      'vue/no-v-html': 'error',
      'vue/multi-word-component-names': 'off', // noms français d'un mot : Accueil, Correcteur, Retour…
      'vue/block-lang': ['error', { script: { lang: 'ts' } }],
      '@typescript-eslint/consistent-type-imports': ['error', { fixStyle: 'inline-type-imports' }],
      '@typescript-eslint/no-unused-vars': ['error', { argsIgnorePattern: '^_', varsIgnorePattern: '^_' }],
      eqeqeq: ['error', 'always', { null: 'ignore' }],
    },
  },
  {
    files: ['src/domaine/**/*.ts'],
    ignores: ['**/*.test.ts'],
    rules: {
      ...interdire(['application', 'infrastructure', 'interface'], CADRES),
      'no-restricted-globals': ['error', ...NAVIGATEUR],
    },
  },
  {
    files: ['src/application/**/*.ts'],
    ignores: ['**/*.test.ts'],
    rules: { ...interdire(['infrastructure', 'interface'], CADRES), 'no-restricted-globals': ['error', ...NAVIGATEUR] },
  },
  {
    files: ['src/infrastructure/**/*.ts'],
    ignores: ['**/*.test.ts'],
    rules: { ...interdire(['interface']), 'no-restricted-properties': 'off' }, // l'adaptateur réseau
  },
  {
    files: ['src/interface/**/*.{ts,vue}'],
    ignores: ['**/*.test.ts'],
    rules: {
      ...interdire(
        ['infrastructure'],
        ['frappe-ui', 'frappe-ui-requete', 'frappe-ui/*', 'zod', 'zod/mini'],
        "Réservé aux adaptateurs de l'infrastructure.",
      ),
      'no-restricted-globals': ['error', ...RESEAU],
      '@typescript-eslint/no-restricted-imports': [
        'error',
        {
          patterns: [
            {
              group: CAS_USAGES,
              allowTypeImports: true,
              message: "Cas d'usage reçus par injection : import de type seulement.",
            },
          ],
        },
      ],
    },
  },
  {
    files: ['src/**/*.test.ts', 'src/test/**/*.ts'],
    rules: {
      // tests : accès indexés sûrs par construction des données d'essai
      '@typescript-eslint/no-non-null-assertion': 'off',
      '@typescript-eslint/unbound-method': 'off',
      '@typescript-eslint/require-await': 'off', // faux ports : réponses asynchrones immédiates
    },
  },
  prettier,
)
